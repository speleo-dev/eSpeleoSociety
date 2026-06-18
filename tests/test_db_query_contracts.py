from pathlib import Path
import unittest


class DbQueryContractsTest(unittest.TestCase):
    def test_fetch_ecp_requests_joins_by_photo_hash_written_by_insert_path(self):
        source = Path("db.py").read_text(encoding="utf-8")
        start = source.index("    def fetch_ecp_requests")
        end = source.index("    def fetch_notifications", start)
        method_source = source[start:end]

        self.assertIn("r.photo_hash = er.photo_hash", method_source)
        self.assertNotIn("r.ecp_record_id = er.ecp_record_id", method_source)

    def test_fetch_ecp_record_by_photo_hash_selects_check_hash_it_reads(self):
        source = Path("db.py").read_text(encoding="utf-8")
        start = source.index("    def fetch_ecp_record_by_photo_hash")
        end = source.index("    def fetch_ecp_requests", start)
        method_source = source[start:end]

        self.assertIn("er.check_hash", method_source)
        self.assertIn("check_hash=row['check_hash']", method_source)


if __name__ == "__main__":
    unittest.main()
