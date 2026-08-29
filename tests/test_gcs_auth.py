import json
import unittest
from unittest import mock

from gcs_auth import resolve_gcs_credentials

SAMPLE_KEY = {
    "type": "service_account",
    "project_id": "sss-membershipcard-test-451913",
    "private_key_id": "abc123",
    "private_key": "-----BEGIN-PLACEHOLDER-PRIVATE-KEY-----\nsample-not-a-real-key\n-----END-PLACEHOLDER-PRIVATE-KEY-----\n",
    "client_email": "uploader@sss-membershipcard-test-451913.iam.gserviceaccount.com",
    "client_id": "123456789",
    "token_uri": "https://oauth2.googleapis.com/token",
}


class ResolveGcsCredentialsTest(unittest.TestCase):
    def test_empty_value_reports_not_configured(self):
        credentials, error = resolve_gcs_credentials("")
        self.assertIsNone(credentials)
        self.assertIn("not configured", error)

    def test_missing_legacy_path_reports_clear_message(self):
        credentials, error = resolve_gcs_credentials("sss-membershipcard-test-451913-2fa710bfeb4e.json")
        self.assertIsNone(credentials)
        self.assertIn("was not found", error)
        self.assertIn("Secrets Setup", error)

    def test_invalid_json_content_reports_error(self):
        credentials, error = resolve_gcs_credentials("{not valid json")
        self.assertIsNone(credentials)
        self.assertIn("not valid JSON", error)

    def test_embedded_json_content_is_parsed_into_credentials(self):
        with mock.patch(
            "google.oauth2.service_account.Credentials.from_service_account_info"
        ) as from_info:
            from_info.return_value = mock.sentinel.credentials
            credentials, error = resolve_gcs_credentials(json.dumps(SAMPLE_KEY))

        self.assertIsNone(error)
        self.assertIs(credentials, mock.sentinel.credentials)
        from_info.assert_called_once_with(SAMPLE_KEY)


if __name__ == "__main__":
    unittest.main()
