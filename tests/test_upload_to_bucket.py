import unittest
from unittest import mock

import utils


class UploadToBucketTest(unittest.TestCase):
    """upload_to_bucket must never crash the caller (e.g. save_changes) even
    when GCS configuration or credentials are broken/missing."""

    def _patch_secrets(self, credentials_json='{"type": "service_account"}', project_id="proj", bucket_name="bucket"):
        return mock.patch.object(
            utils.secret_manager,
            "get_secret",
            side_effect=lambda name: {
                "credentials_json": credentials_json,
                "project_id": project_id,
                "bucket_name": bucket_name,
            }.get(name),
        )

    def test_missing_credentials_reports_and_returns_none(self):
        with self._patch_secrets(credentials_json="sss-membershipcard-test-451913-2fa710bfeb4e.json"):
            result = utils.upload_to_bucket("blob.jpg", b"data", "image/jpeg")
        self.assertIsNone(result)

    def test_missing_config_returns_none_without_raising(self):
        with self._patch_secrets(project_id=None):
            result = utils.upload_to_bucket("blob.jpg", b"data", "image/jpeg")
        self.assertIsNone(result)

    def test_client_construction_failure_is_caught(self):
        with self._patch_secrets():
            with mock.patch.object(utils, "resolve_gcs_credentials", return_value=(mock.sentinel.creds, None)):
                with mock.patch.object(utils, "_get_storage_module") as get_storage:
                    get_storage.return_value.Client.side_effect = RuntimeError("boom")
                    result = utils.upload_to_bucket("blob.jpg", b"data", "image/jpeg")
        self.assertIsNone(result)

    def test_successful_upload_returns_public_url(self):
        with self._patch_secrets():
            with mock.patch.object(utils, "resolve_gcs_credentials", return_value=(mock.sentinel.creds, None)):
                with mock.patch.object(utils, "_get_storage_module") as get_storage:
                    fake_blob = mock.Mock()
                    fake_bucket = mock.Mock()
                    fake_bucket.blob.return_value = fake_blob
                    get_storage.return_value.Client.return_value.bucket.return_value = fake_bucket

                    result = utils.upload_to_bucket("member_portraits/1.jpg", b"data", "image/jpeg")

        self.assertEqual(result, "https://storage.googleapis.com/bucket/member_portraits/1.jpg")
        fake_blob.upload_from_string.assert_called_once()
        fake_blob.make_public.assert_called_once()
        get_storage.return_value.Client.assert_called_once_with(project="proj", credentials=mock.sentinel.creds)


if __name__ == "__main__":
    unittest.main()
