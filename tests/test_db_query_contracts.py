import unittest
from datetime import date, datetime

import db
from config import secret_manager
from model import Ecp
from utils import create_check_hash


class RecordingDatabaseManager(db.DatabaseManager):
    def __init__(self, fetch_all_rows=None, fetch_one_row=None):
        self.fetch_all_rows = fetch_all_rows or []
        self.fetch_one_row = fetch_one_row
        self.last_fetch_all_query = None
        self.last_fetch_one_query = None
        self.last_execute_query = None
        self.last_execute_params = None

    def _fetch_all(self, query, params=None):
        self.last_fetch_all_query = query
        return self.fetch_all_rows

    def _fetch_one(self, query, params=None):
        self.last_fetch_one_query = query
        return self.fetch_one_row

    def _execute(self, query, params=None):
        self.last_execute_query = query
        self.last_execute_params = params

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
        })

        ecp_record = manager.fetch_ecp_record_by_id(33)

        self.assertEqual(ecp_record.ecp_id, 33)
        self.assertEqual(ecp_record.photo_hash, "photo-ref")
        self.assertEqual(ecp_record.qr_url, "https://storage.example/ecp_qr/a.png")
        self.assertEqual(ecp_record.qr_key_id, "key-2026")
        self.assertEqual(ecp_record.qr_payload_hash, "c" * 64)
        self.assertEqual(ecp_record.valid_until, date(2027, 6, 23))
        self.assertEqual(ecp_record.wallet_status, "not_issued")
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
        )

        for column_name in (
            "qr_url",
            "qr_key_id",
            "qr_payload",
            "qr_payload_hash",
            "issued_at",
            "valid_until",
            "wallet_status",
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
        self.assertEqual(manager.last_execute_params[-1], 33)

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


if __name__ == "__main__":
    unittest.main()
