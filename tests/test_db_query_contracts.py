import unittest
from datetime import date, datetime

import db
from config import secret_manager
from model import Club, Ecp
from utils import create_check_hash


class RecordingDatabaseManager(db.DatabaseManager):
    def __init__(self, fetch_all_rows=None, fetch_one_row=None, fetch_one_rows=None):
        self.fetch_all_rows = fetch_all_rows or []
        self.fetch_one_row = fetch_one_row
        self.fetch_one_rows = list(fetch_one_rows) if fetch_one_rows is not None else None
        self.last_fetch_all_query = None
        self.last_fetch_all_params = None
        self.last_fetch_one_query = None
        self.last_execute_query = None
        self.last_execute_params = None
        self.execute_queries = []
        self.execute_params = []

    def _fetch_all(self, query, params=None):
        self.last_fetch_all_query = query
        self.last_fetch_all_params = params
        return self.fetch_all_rows

    def _fetch_one(self, query, params=None):
        self.last_fetch_one_query = query
        if self.fetch_one_rows is not None:
            return self.fetch_one_rows.pop(0) if self.fetch_one_rows else None
        return self.fetch_one_row

    def _execute(self, query, params=None):
        self.last_execute_query = query
        self.last_execute_params = params
        self.execute_queries.append(query)
        self.execute_params.append(params)

    def _log_action(self, action, table_name, details, user=None):
        return None


class DbQueryContractsTest(unittest.TestCase):
    def setUp(self):
        secret_manager.secrets["crypt_key"] = "unit-test-crypt-key"

    def test_fetch_ecp_requests_joins_record_by_ecp_record_id_and_exposes_photo_hash(self):
        manager = RecordingDatabaseManager(fetch_all_rows=[{
            "request_id": 11,
            "member_id": 22,
            "status": "pending",
            "request_date": "2026-06-20",
            "ecp_record_id": 33,
            "photo_hash": "photo-ref",
        }])

        requests = manager.fetch_ecp_requests()

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].ecp_record_id, 33)
        self.assertEqual(requests[0].photo_hash, "photo-ref")
        self.assertIn("r.ecp_record_id = er.ecp_record_id", manager.last_fetch_all_query)
        self.assertNotIn("r.photo_hash = er.photo_hash", manager.last_fetch_all_query)

    def test_insert_ecp_request_writes_ecp_record_id_not_photo_hash(self):
        manager = RecordingDatabaseManager()

        manager.insert_ecp_request(member_id=22, ecp_record_id=33)

        self.assertIn("ecp_record_id", manager.last_execute_query)
        self.assertNotIn("photo_hash", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params, (22, 33))

    def test_fetch_ecp_record_by_photo_hash_does_not_join_on_missing_member_id(self):
        manager = RecordingDatabaseManager(fetch_one_row={
            "ecp_record_id": 33,
            "ecp_hash": "a" * 64,
            "gdpr_consent": True,
            "notifications_enabled": False,
            "photo_hash": "photo-ref",
            "ecp_active": False,
            "check_hash": create_check_hash(),
        })

        ecp_record = manager.fetch_ecp_record_by_photo_hash("photo-ref")

        self.assertEqual(ecp_record.ecp_id, 33)
        self.assertIsNone(ecp_record.member_id)
        self.assertIn("er.ecp_record_id", manager.last_fetch_one_query)
        self.assertNotIn("er.member_id", manager.last_fetch_one_query)

    def test_fetch_ecp_record_by_id_uses_author_schema_primary_key(self):
        manager = RecordingDatabaseManager(fetch_one_row={
            "ecp_record_id": 33,
            "ecp_hash": "a" * 64,
            "gdpr_consent": True,
            "notifications_enabled": False,
            "photo_hash": "photo-ref",
            "ecp_active": False,
            "check_hash": create_check_hash(),
            "qr_url": "https://storage.example/ecp_qr/a.png",
            "qr_key_id": "key-2026",
            "qr_payload_hash": "c" * 64,
            "issued_at": datetime(2026, 6, 23, 12, 0),
            "valid_until": date(2027, 6, 23),
            "wallet_status": "not_issued",
            "verification_url": "https://storage.example/ecp_verify/token.html",
            "card_image_url": "https://storage.example/ecp_cards/a.jpg",
            "card_pdf_url": "https://storage.example/ecp_cards/a.pdf",
            "legal_document_url": "https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf",
        })

        ecp_record = manager.fetch_ecp_record_by_id(33)

        self.assertEqual(ecp_record.ecp_id, 33)
        self.assertEqual(ecp_record.photo_hash, "photo-ref")
        self.assertEqual(ecp_record.qr_url, "https://storage.example/ecp_qr/a.png")
        self.assertEqual(ecp_record.qr_key_id, "key-2026")
        self.assertEqual(ecp_record.qr_payload_hash, "c" * 64)
        self.assertEqual(ecp_record.valid_until, date(2027, 6, 23))
        self.assertEqual(ecp_record.wallet_status, "not_issued")
        self.assertEqual(ecp_record.verification_url, "https://storage.example/ecp_verify/token.html")
        self.assertEqual(ecp_record.card_image_url, "https://storage.example/ecp_cards/a.jpg")
        self.assertEqual(ecp_record.card_pdf_url, "https://storage.example/ecp_cards/a.pdf")
        self.assertIn("WHERE er.ecp_record_id = %s", manager.last_fetch_one_query)
        self.assertNotIn("er.member_id", manager.last_fetch_one_query)

    def test_update_ecp_record_on_approval_targets_ecp_record_id(self):
        manager = RecordingDatabaseManager()

        manager.update_ecp_record_on_approval(ecp_record_id=33, new_generated_ecp_hash="b" * 64)

        self.assertIn("WHERE ecp_record_id = %s", manager.last_execute_query)
        self.assertNotIn("WHERE photo_hash = %s", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params, ("b" * 64, 33))

    def test_update_ecp_record_issuance_persists_qr_metadata(self):
        manager = RecordingDatabaseManager()
        payload = {"kid": "key-2026", "claim": {"member_id": 22}}
        issued_at = datetime(2026, 6, 23, 12, 0)
        valid_until = date(2027, 6, 23)

        manager.update_ecp_record_issuance(
            ecp_record_id=33,
            ecp_hash="b" * 64,
            qr_url="https://storage.example/ecp_qr/b.png",
            qr_key_id="key-2026",
            qr_payload=payload,
            qr_payload_hash="c" * 64,
            issued_at=issued_at,
            valid_until=valid_until,
            verification_url="https://storage.example/ecp_verify/token.html",
            card_image_url="https://storage.example/ecp_cards/b.jpg",
            card_pdf_url="https://storage.example/ecp_cards/b.pdf",
            legal_document_url="https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf",
        )

        for column_name in (
            "qr_url",
            "qr_key_id",
            "qr_payload",
            "qr_payload_hash",
            "issued_at",
            "valid_until",
            "wallet_status",
            "verification_url",
            "card_image_url",
            "card_pdf_url",
            "legal_document_url",
        ):
            self.assertIn(column_name, manager.last_execute_query)
        self.assertIn("WHERE ecp_record_id = %s", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params[0], "b" * 64)
        self.assertEqual(manager.last_execute_params[1], "https://storage.example/ecp_qr/b.png")
        self.assertEqual(manager.last_execute_params[2], "key-2026")
        self.assertEqual(manager.last_execute_params[4], "c" * 64)
        self.assertEqual(manager.last_execute_params[5], issued_at)
        self.assertEqual(manager.last_execute_params[6], valid_until)
        self.assertEqual(manager.last_execute_params[7], "not_issued")
        self.assertEqual(manager.last_execute_params[8], "https://storage.example/ecp_verify/token.html")
        self.assertEqual(manager.last_execute_params[9], "https://storage.example/ecp_cards/b.jpg")
        self.assertEqual(manager.last_execute_params[10], "https://storage.example/ecp_cards/b.pdf")
        self.assertEqual(manager.last_execute_params[11], "https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf")
        self.assertEqual(manager.last_execute_params[-1], 33)

    def test_update_member_portrait_persists_portrait_metadata(self):
        manager = RecordingDatabaseManager()

        manager.update_member_portrait(
            member_id=22,
            portrait_url="https://storage.example/member_portraits/22.jpg",
            portrait_hash="d" * 64,
            face_detected=True,
        )

        self.assertIn("portrait_url = %s", manager.last_execute_query)
        self.assertIn("portrait_hash = %s", manager.last_execute_query)
        self.assertIn("portrait_face_detected = %s", manager.last_execute_query)
        self.assertIn("portrait_updated_at = CURRENT_TIMESTAMP", manager.last_execute_query)
        self.assertEqual(
            manager.last_execute_params,
            ("https://storage.example/member_portraits/22.jpg", "d" * 64, True, 22),
        )

    def test_fetch_member_search_directory_uses_lightweight_joined_query(self):
        manager = RecordingDatabaseManager(fetch_all_rows=[{
            "member_id": 11,
            "member_status": "active",
            "title_prefix": "",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "title_suffix": "",
            "phone": "0901",
            "email": "ada@example.sk",
            "ecp_hash": "ecp-1",
            "discounted_membership": False,
            "is_directory_stub": False,
            "portrait_url": "https://storage.example/portrait.jpg",
            "portrait_hash": "portrait-hash",
            "portrait_face_detected": True,
            "portrait_updated_at": datetime(2026, 6, 30, 12, 0),
            "primary_club_id": 7,
            "primary_club_name": "Speleo Nitra",
            "primary_club_president_id": 11,
            "has_paid_current_year_fee": True,
        }])

        members = manager.fetch_member_search_directory()

        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].first_name, "Ada")
        self.assertEqual(members[0].primary_club_name, "Speleo Nitra")
        self.assertTrue(members[0].is_president)
        self.assertTrue(members[0].has_paid_current_year_fee)
        self.assertIn("LEFT JOIN LATERAL", manager.last_fetch_all_query)
        self.assertIn("LEFT JOIN clubs c ON c.club_id = ca_primary.club_id", manager.last_fetch_all_query)
        self.assertIn("ORDER BY lower(COALESCE(m.last_name, ''))", manager.last_fetch_all_query)
        self.assertNotIn("birth_date_encrypted", manager.last_fetch_all_query)
        self.assertNotIn("m.street", manager.last_fetch_all_query)
        self.assertEqual(len(manager.last_fetch_all_params), 1)

    def test_delete_ecp_record_by_id_targets_author_schema_primary_key(self):
        manager = RecordingDatabaseManager()

        manager.delete_ecp_record_by_id(33)

        self.assertIn("WHERE ecp_record_id = %s", manager.last_execute_query)
        self.assertNotIn("WHERE photo_hash = %s", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params, (33,))

    def test_insert_ecp_returns_created_ecp_record_id_for_request_linking(self):
        manager = RecordingDatabaseManager(fetch_one_row=(33,))
        ecp = Ecp(
            ecp_hash="a" * 64,
            gdpr_consent=True,
            notifications_enabled=True,
            photo_hash="photo-ref",
            is_ecp_active=False,
            member_id=22,
            check_hash=create_check_hash(),
        )

        created_id = manager.insert_ecp(ecp)

        self.assertEqual(created_id, 33)
        self.assertIn("RETURNING ecp_record_id", manager.last_fetch_one_query)
        self.assertEqual(ecp.ecp_id, 33)

    def test_set_primary_membership_clears_other_primary_clubs_for_member(self):
        manager = RecordingDatabaseManager()

        manager.set_primary_memberships(member_id=22, club_id=33)

        self.assertIn("CASE WHEN club_id = %s THEN TRUE ELSE FALSE END", manager.last_execute_query)
        self.assertIn("WHERE member_id = %s", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params, (33, 22))

    def test_insert_membership_is_idempotent_for_existing_member_club_pair(self):
        manager = RecordingDatabaseManager()

        manager.insert_memberships(member_id=22, club_id=33, primary_club=False)

        self.assertIn("ON CONFLICT (member_id, club_id)", manager.last_execute_query)
        self.assertIn("role", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params, (22, 33, False, "member"))

    def test_insert_fee_record_is_idempotent_per_member_year_and_type(self):
        manager = RecordingDatabaseManager()

        manager.insert_fee_record(member_id=22, year=2026, hash_ecp="a" * 64)

        self.assertIn("fee_type", manager.last_execute_query)
        self.assertIn("ON CONFLICT (member_id, year, fee_type) DO NOTHING", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params, (22, "a" * 64, 2026, "standard"))

    def test_fetch_clubs_exposes_webpage_and_public_president_name(self):
        manager = RecordingDatabaseManager(fetch_all_rows=[{
            "club_id": 11,
            "club_name": "Speleo Club",
            "street": "",
            "city": "",
            "zip_code": "",
            "country": "SK",
            "email": "one@example.sk, two@example.sk",
            "phone": "0903 111 222, 02/123 45 67",
            "webpage": "https://speleo.example.sk",
            "president_id": None,
            "president_name_text": "Public President",
            "foundation_date": None,
            "logo_url": None,
            "member_count": 0,
            "president_name": "Public President",
        }])

        clubs = manager.fetch_clubs()

        self.assertEqual(clubs[0].webpage, "https://speleo.example.sk")
        self.assertEqual(clubs[0].president_name_text, "Public President")
        self.assertEqual(clubs[0].email, "one@example.sk, two@example.sk")
        self.assertEqual(clubs[0].phone, "0903 111 222, 02/123 45 67")
        self.assertIn("c.webpage", manager.last_fetch_all_query)
        self.assertIn("c.president_name_text", manager.last_fetch_all_query)

    def test_update_club_persists_directory_contact_fields(self):
        manager = RecordingDatabaseManager()
        club = Club(
            club_id=11,
            name="Speleo Club",
            street="",
            city="",
            zip_code="",
            country="SK",
            email="one@example.sk, two@example.sk",
            phone="0903 111 222, 02/123 45 67",
            president_id=None,
            president_name="",
            foundation_date=None,
            member_count=0,
            webpage="https://speleo.example.sk",
            president_name_text="Public President",
        )

        manager.update_club(club)

        self.assertIn("webpage = %s", manager.last_execute_query)
        self.assertIn("president_name_text = %s", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params[8], "https://speleo.example.sk")
        self.assertEqual(manager.last_execute_params[10], "Public President")

    def test_upsert_club_directory_entry_links_president_member_to_club(self):
        manager = RecordingDatabaseManager(fetch_one_rows=[
            (11,),
            None,
            None,
            (22,),
        ])

        club_id = manager.upsert_club_directory_entry(
            club_name="Speleo Club",
            president_name_text="Public President",
            president_title_prefix="",
            president_first_name="Public",
            president_last_name="President",
            president_title_suffix="",
            phone="0903 111 222, 02/123 45 67",
            email="one@example.sk, two@example.sk",
            webpage="https://speleo.example.sk",
        )

        self.assertEqual(club_id, 11)
        self.assertTrue(any("INSERT INTO club_affiliations" in query for query in manager.execute_queries))
        self.assertIn((22, 11, True, "president"), manager.execute_params)
        self.assertIn((22, 11), manager.execute_params)

    def test_upsert_directory_president_member_reuses_existing_president(self):
        manager = RecordingDatabaseManager(fetch_one_rows=[{
            "member_id": 22,
            "is_directory_stub": False,
        }])

        member_id = manager.upsert_directory_president_member(
            club_id=11,
            title_prefix="Mgr.",
            first_name="Public",
            last_name="President",
            title_suffix="",
            phone="0903 111 222",
            email="one@example.sk",
        )

        self.assertEqual(member_id, 22)
        self.assertEqual(manager.execute_queries, [])

    def test_update_member_birth_date_encrypts_or_clears_value(self):
        manager = RecordingDatabaseManager()

        manager.update_member_birth_date(member_id=22, birth_date=date(1980, 1, 2))

        self.assertIn("birth_date_encrypted", manager.last_execute_query)
        self.assertIn("encode(encrypt", manager.last_execute_query)
        self.assertEqual(manager.last_execute_params[0], b"1980-01-02")
        self.assertEqual(manager.last_execute_params[1], b"1980-01-02")
        self.assertEqual(manager.last_execute_params[-1], 22)

    def test_set_club_member_role_president_updates_single_president_link(self):
        manager = RecordingDatabaseManager()

        manager.set_club_member_role(club_id=11, member_id=22, role="president")

        joined_queries = "\n".join(manager.execute_queries)
        self.assertIn("UPDATE club_affiliations", joined_queries)
        self.assertIn("SET role = 'member'", joined_queries)
        self.assertIn("SET role = %s", joined_queries)
        self.assertIn("UPDATE clubs", joined_queries)
        self.assertIn((11,), manager.execute_params)
        self.assertIn(("president", 11, 22), manager.execute_params)
        self.assertIn((22, 11), manager.execute_params)

    def test_set_club_member_role_member_clears_matching_president_link(self):
        manager = RecordingDatabaseManager()

        manager.set_club_member_role(club_id=11, member_id=22, role="member")

        joined_queries = "\n".join(manager.execute_queries)
        self.assertIn("SET role = %s", joined_queries)
        self.assertIn("president_id = NULL", joined_queries)
        self.assertIn(("member", 11, 22), manager.execute_params)
        self.assertIn((11, 22), manager.execute_params)


if __name__ == "__main__":
    unittest.main()
