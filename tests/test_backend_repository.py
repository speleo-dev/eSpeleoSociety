from datetime import date
import unittest

from backend.repository import DatabaseApiRepository


class FakeDbManager:
    def __init__(self, row):
        self.row = row
        self.last_query = None
        self.last_params = None

    def _fetch_one(self, query, params=None):
        self.last_query = query
        self.last_params = params
        return self.row


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


if __name__ == "__main__":
    unittest.main()
