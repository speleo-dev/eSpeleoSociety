import os
import tempfile
import unittest

from config import SecretManager


class SecretManagerEncryptionTest(unittest.TestCase):
    def test_encrypt_and_save_file_does_not_leave_plaintext_temp_file_on_disk(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                manager = SecretManager(properties_file="secrets.properties")
                ok = manager.encrypt_and_save_file({"db_password": "s3cr3t"}, pin="1234")

                self.assertTrue(ok)
                self.assertTrue(os.path.exists("secrets.properties"))
                self.assertFalse(os.path.exists("temp.properties"))
                self.assertEqual(sorted(os.listdir(tmp_dir)), ["secrets.properties"])
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

    def test_encrypt_and_save_file_handles_percent_signs_and_json_correctly(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            original_cwd = os.getcwd()
            os.chdir(tmp_dir)
            try:
                manager = SecretManager(properties_file="secrets.properties")
                secrets_data = {
                    "credentials_json": '{"type": "service_account", "cert_url": "https://example.com/certs%2Fkey%40domain"}',
                    "db_password": "pass%word%100",
                }
                ok = manager.encrypt_and_save_file(secrets_data, pin="98765432")
                self.assertTrue(ok)

                reader = SecretManager(properties_file="secrets.properties")
                ok = reader.decrypt_file("98765432")
                self.assertTrue(ok)
                self.assertEqual(reader.get_secret("credentials_json"), secrets_data["credentials_json"])
                self.assertEqual(reader.get_secret("db_password"), "pass%word%100")
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
