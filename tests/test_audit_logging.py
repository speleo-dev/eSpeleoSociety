import unittest

from db import sanitize_log_details


class AuditLoggingTest(unittest.TestCase):
    def test_sanitize_log_details_redacts_member_pii_and_ecp_tokens(self):
        raw_details = (
            "Updated member ID 12 with data: "
            "{'email': 'ada@example.org', 'phone': '+421900111222', "
            "'ecp_hash': 'abcdef123456', 'photo_hash': 'photo-secret', "
            "'birth_date': '1980-01-01', 'street': 'Hidden 42'}"
        )

        sanitized = sanitize_log_details(raw_details)

        self.assertNotIn("ada@example.org", sanitized)
        self.assertNotIn("+421900111222", sanitized)
        self.assertNotIn("abcdef123456", sanitized)
        self.assertNotIn("photo-secret", sanitized)
        self.assertNotIn("1980-01-01", sanitized)
        self.assertNotIn("Hidden 42", sanitized)
        self.assertIn("[REDACTED]", sanitized)


if __name__ == "__main__":
    unittest.main()
