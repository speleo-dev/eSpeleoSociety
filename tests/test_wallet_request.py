from types import SimpleNamespace
import unittest

from utils import get_request_field
from wallet_pass import build_wallet_barcode_from_request


class WalletRequestTest(unittest.TestCase):
    def test_get_request_field_supports_object_attributes(self):
        request = SimpleNamespace(photo_hash="photo-1")

        self.assertEqual(get_request_field(request, "photo_hash"), "photo-1")

    def test_get_request_field_supports_dict_values(self):
        request = {"photo_hash": "photo-2"}

        self.assertEqual(get_request_field(request, "photo_hash"), "photo-2")

    def test_wallet_barcode_from_request_uses_signed_qr_data_without_qr_image_url(self):
        request = SimpleNamespace(member_id=123, signed_qr_data='{"signed":"payload"}')

        barcode = build_wallet_barcode_from_request(request, get_request_field)

        self.assertEqual(
            barcode,
            {
                "type": "QR_CODE",
                "value": '{"signed":"payload"}',
                "alternateText": "eCP 123",
            },
        )


if __name__ == "__main__":
    unittest.main()
