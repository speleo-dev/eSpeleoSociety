from types import SimpleNamespace
import unittest

from utils import get_request_field


class WalletRequestTest(unittest.TestCase):
    def test_get_request_field_supports_object_attributes(self):
        request = SimpleNamespace(photo_hash="photo-1")

        self.assertEqual(get_request_field(request, "photo_hash"), "photo-1")

    def test_get_request_field_supports_dict_values(self):
        request = {"photo_hash": "photo-2"}

        self.assertEqual(get_request_field(request, "photo_hash"), "photo-2")


if __name__ == "__main__":
    unittest.main()
