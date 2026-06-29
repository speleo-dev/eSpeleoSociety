from datetime import date
import unittest

from backend.audit import AuditEvent
from backend.repository import DatabaseApiRepository


class FakeDbManager:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []
        self.last_query = None
        self.last_params = None
        self.fetch_one_calls = []
        self.execute_calls = []

    def _fetch_all(self, query, params=None):
        self.last_query = query
        self.last_params = params
        return self.rows

    def _fetch_one(self, query, params=None):
        self.last_query = query
        self.last_params = params
        self.fetch_one_calls.append((query, params))
        return self.row

    def _log_action(self, action, table_name, details, user=None):
        self.last_log_action = action
        self.last_log_table_name = table_name
        self.last_log_details = details
        self.last_log_user = user

    def _execute(self, query, params=None):
        self.last_query = query
        self.last_params = params
        self.execute_calls.append((query, params))


class BackendRepositoryTest(unittest.TestCase):
    def test_ecp_verification_lookup_rejects_invalid_tokens_before_db_query(self):
        fake_db = FakeDbManager(row=None)
        repository = DatabaseApiRepository(fake_db)

        self.assertIsNone(repository.fetch_ecp_verification_by_token("../bad"))
        self.assertIsNone(fake_db.last_query)

    def test_ecp_verification_lookup_maps_db_row_to_public_record(self):
        fake_db = FakeDbManager(row={
            "member_id": 101,
            "display_name": "Ada Lovelace",
            "club_name": "Alpha",
            "status": "active",
            "valid_until": date(2027, 6, 29),
            "portrait_url": "https://storage.example/portrait.jpg",
            "card_image_url": "https://storage.example/card.jpg",
            "card_pdf_url": "https://storage.example/card.pdf",
            "legal_document_url": "https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf",
            "qr_payload_hash": "a" * 64,
        })
        repository = DatabaseApiRepository(fake_db)

        record = repository.fetch_ecp_verification_by_token("token-123456789")

        self.assertEqual(record["display_name"], "Ada Lovelace")
        self.assertEqual(record["valid_until"], "2027-06-29")
        self.assertEqual(fake_db.last_params, ("%/ecp_verify/token-123456789.html",))
        self.assertIn("er.ecp_active = TRUE", fake_db.last_query)

    def test_list_clubs_uses_sql_filter_and_keyset_cursor(self):
        fake_db = FakeDbManager(rows=[
            {
                "club_id": 7,
                "club_name": "Speleo Nitra",
                "street": "Street 7",
                "city": "Nitra",
                "zip_code": "94901",
                "country": "SK",
                "email": "nitra@example.sk",
                "phone": "0901",
                "webpage": "https://nitra.example.sk",
                "president_id": 70,
                "president_name_text": "Ada",
                "foundation_date": date(1980, 1, 1),
                "logo_url": "",
                "member_count": 4,
                "president_name": "Ada",
            },
            {
                "club_id": 8,
                "club_name": "Speleo Nitra B",
                "street": "Street 8",
                "city": "Nitra",
                "zip_code": "94902",
                "country": "SK",
                "email": "nitrab@example.sk",
                "phone": "0902",
                "webpage": "",
                "president_id": 80,
                "president_name_text": "Grace",
                "foundation_date": date(1981, 1, 1),
                "logo_url": "",
                "member_count": 3,
                "president_name": "Grace",
            },
        ])
        repository = DatabaseApiRepository(fake_db)

        clubs, next_cursor = repository.list_clubs(limit=1, cursor=None, filter_text="nit")

        self.assertEqual(len(clubs), 1)
        self.assertEqual(clubs[0].name, "Speleo Nitra")
        self.assertIsNotNone(next_cursor)
        self.assertIn("ILIKE", fake_db.last_query)
        self.assertIn("c.club_id > %s", fake_db.last_query)
        self.assertIn("LIMIT %s", fake_db.last_query)
        self.assertEqual(fake_db.last_params[0], 0)
        self.assertEqual(fake_db.last_params[-1], 2)
        self.assertIn("%nit%", fake_db.last_params)

    def test_fetch_member_portal_profile_maps_self_service_fields(self):
        fake_db = FakeDbManager(row={
            "member_id": 101,
            "status": "active",
            "title_prefix": "",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "title_suffix": "",
            "display_name": "Ada Lovelace",
            "email": "ada@example.sk",
            "phone": "0901",
            "portrait_url": "https://storage.example/portrait.jpg",
            "primary_club_id": 1,
            "primary_club_name": "Alpha",
            "ecp_active": True,
            "ecp_valid_until": date(2027, 6, 29),
            "ecp_verification_url": "https://storage.example/ecp_verify/token.html",
            "ecp_card_image_url": "https://storage.example/card.jpg",
            "ecp_card_pdf_url": "https://storage.example/card.pdf",
            "ecp_wallet_status": "issued",
            "pending_ecp_request_id": 55,
            "pending_ecp_request_status": "pending",
            "pending_ecp_request_date": date(2026, 6, 29),
        })
        repository = DatabaseApiRepository(fake_db)

        profile = repository.fetch_member_portal_profile(101)

        self.assertEqual(profile["display_name"], "Ada Lovelace")
        self.assertEqual(profile["ecp_valid_until"], "2027-06-29")
        self.assertEqual(profile["pending_ecp_request_date"], "2026-06-29")
        self.assertEqual(fake_db.last_params, (101,))
        self.assertIn("WHERE m.member_id = %s", fake_db.last_query)
        self.assertNotIn("birth_date_encrypted", fake_db.last_query)

    def test_create_member_ecp_request_uploads_photo_and_links_record(self):
        uploads = []

        def upload_blob(blob_name, data, content_type):
            uploads.append((blob_name, data, content_type))
            return f"https://storage.example/{blob_name}"

        fake_db = FakeDbManager(row={"ecp_record_id": 88, "request_id": 77, "request_date": date(2026, 6, 29)})
        repository = DatabaseApiRepository(fake_db, upload_blob=upload_blob, check_hash_factory=lambda: "check-1")

        request = repository.create_member_ecp_request(
            member_id=101,
            photo_bytes=b"portrait",
            content_type="image/jpeg",
            gdpr_consent=True,
            notifications_enabled=False,
        )

        self.assertEqual(request["request_id"], 77)
        self.assertEqual(request["ecp_record_id"], 88)
        self.assertEqual(request["status"], "pending")
        self.assertEqual(request["request_date"], "2026-06-29")
        self.assertEqual(uploads[0][1:], (b"portrait", "image/jpeg"))
        self.assertTrue(uploads[0][0].startswith("ecp_request_photos/"))
        self.assertTrue(uploads[0][0].endswith(".jpg"))
        self.assertIn("INSERT INTO ecp_records", fake_db.fetch_one_calls[0][0])
        self.assertIn("INSERT INTO ecp_requests", fake_db.fetch_one_calls[1][0])
        self.assertNotIn("photo_hash", fake_db.fetch_one_calls[1][0])

    def test_record_api_audit_event_uses_db_log_without_raw_tokens(self):
        fake_db = FakeDbManager()
        repository = DatabaseApiRepository(fake_db)

        repository.record_api_audit_event(AuditEvent(
            request_id="req_123",
            method="GET",
            route="/api/v1/ecp/verify/{token}",
            status_code=200,
            subject="anonymous",
            roles=(),
            outcome="success",
        ))

        self.assertEqual(fake_db.last_log_action, "API_REQUEST")
        self.assertEqual(fake_db.last_log_table_name, "api_requests")
        self.assertEqual(fake_db.last_log_user, "anonymous")
        self.assertIn("/api/v1/ecp/verify/{token}", fake_db.last_log_details)
        self.assertNotIn("token-123456789", fake_db.last_log_details)


if __name__ == "__main__":
    unittest.main()
