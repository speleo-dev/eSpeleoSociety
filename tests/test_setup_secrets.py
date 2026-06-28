from pathlib import Path
import unittest


class SetupSecretsTest(unittest.TestCase):
    def test_setup_dialog_collects_ecp_signing_secrets(self):
        source = Path("setup.py").read_text(encoding="utf-8")

        self.assertIn("ecp_signing_key_id", source)
        self.assertIn("ecp_signing_private_key_b64", source)


if __name__ == "__main__":
    unittest.main()
