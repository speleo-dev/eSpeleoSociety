from pathlib import Path
import unittest


class SetupSecretsTest(unittest.TestCase):
    def test_setup_dialog_collects_ecp_signing_secrets(self):
        source = Path("setup.py").read_text(encoding="utf-8")

        self.assertIn("ecp_signing_key_id", source)
        self.assertIn("ecp_signing_private_key_b64", source)

    def test_setup_dialog_collects_project_runtime_secrets(self):
        source = Path("setup.py").read_text(encoding="utf-8")

        expected_fields = [
            "google_wallet_issuer_id",
            "smtp_server",
            "smtp_port",
            "smtp_user",
            "smtp_password",
            "log_level",
        ]
        for field in expected_fields:
            with self.subTest(field=field):
                self.assertIn(field, source)

        self.assertIn('"db_password"', source)
        self.assertIn('"smtp_password"', source)
        self.assertIn("SENSITIVE_SECRET_FIELDS", source)


if __name__ == "__main__":
    unittest.main()
