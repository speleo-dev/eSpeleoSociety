import unittest
from unittest.mock import patch

import utils


class FakeBlob:
    def __init__(self, should_fail):
        self.should_fail = should_fail

    def delete(self):
        if self.should_fail:
            raise RuntimeError("bucket unavailable")


class FakeBucket:
    def __init__(self, should_fail):
        self.should_fail = should_fail

    def blob(self, name):
        return FakeBlob(self.should_fail)


class FakeClient:
    def __init__(self, should_fail, project=None):
        self.should_fail = should_fail

    def bucket(self, name):
        return FakeBucket(self.should_fail)


def fake_storage_module(should_fail):
    class FakeStorageModule:
        @staticmethod
        def Client(project=None):
            return FakeClient(should_fail, project=project)

    return FakeStorageModule


class DeletePhotoFromBucketTest(unittest.TestCase):
    def _run(self, should_fail):
        with patch.object(utils, "_get_storage_module", return_value=fake_storage_module(should_fail)), \
             patch.object(utils.secret_manager, "get_secret", return_value="fake-secret"):
            return utils.delete_photo_from_bucket("some-photo-hash")

    def test_returns_true_when_blob_deletion_succeeds(self):
        self.assertTrue(self._run(should_fail=False))

    def test_returns_false_instead_of_silently_swallowing_deletion_failure(self):
        self.assertFalse(self._run(should_fail=True))


if __name__ == "__main__":
    unittest.main()
