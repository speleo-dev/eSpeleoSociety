import os
import tempfile
import unittest

from config import SecretManager


class SecretManagerEncryptionTest(unittest.TestCase):
    def test_encrypt_and_save_file_populates_secrets_so_caller_can_detect_success(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                manager = SecretManager(properties_file="secrets.properties")
                ok = manager.encrypt_and_save_file({"db_password": "s3cr3t"}, pin="1234")

                self.assertTrue(ok)
                self.assertEqual(manager.secrets, {"db_password": "s3cr3t"})
            finally:
                os.chdir(original_cwd)

    def test_encrypt_and_save_file_round_trips_through_decrypt_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                manager = SecretManager(properties_file="secrets.properties")
                manager.encrypt_and_save_file({"db_password": "s3cr3t"}, pin="1234")

                reader = SecretManager(properties_file="secrets.properties")
                ok = reader.decrypt_file("1234")

                self.assertTrue(ok)
                self.assertEqual(reader.get_secret("db_password"), "s3cr3t")
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
