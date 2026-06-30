from datetime import date, datetime, timezone
from types import SimpleNamespace
import unittest

from ecp_qr import generate_ecp_signing_key_pair
from ecp_issuance import issue_signed_ecp_qr
from wallet_pass import build_wallet_barcode


class WalletPassTest(unittest.TestCase):
    def test_wallet_barcode_uses_native_qr_code_value_from_signed_payload(self):
        private_key_pem, _ = generate_ecp_signing_key_pair()
        member = SimpleNamespace(
            member_id=123,
            title_prefix="",
            first_name="Ada",
            last_name="Lovelace",
            title_suffix="",
            status="active",
        )
        club = SimpleNamespace(club_id=9, name="Speleo Club")
        issued_qr = issue_signed_ecp_qr(
            member=member,
            club=club,
            valid_until=date(2027, 6, 22),
            private_key_pem=private_key_pem,
            key_id="key-2026",
            paid_year=2027,
            issued_at=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
            verification_url="https://ecp.sss.sk/v/token-1",
        )

        barcode = build_wallet_barcode(issued_qr)

        self.assertEqual(barcode["type"], "QR_CODE")
        self.assertEqual(barcode["value"], issued_qr.qr_data)
        self.assertEqual(barcode["alternateText"], "eCP 123")
        self.assertNotIn("image", barcode)
        self.assertNotIn("url", barcode)


if __name__ == "__main__":
    unittest.main()
