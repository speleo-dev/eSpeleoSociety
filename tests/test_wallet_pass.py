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

    def test_build_google_wallet_generic_object(self):
        private_key_pem, _ = generate_ecp_signing_key_pair()
        member = SimpleNamespace(
            member_id=42,
            title_prefix="Ing.",
            first_name="Janko",
            last_name="Hrasko",
            title_suffix="",
            status="active",
        )
        club = SimpleNamespace(club_id=1, name="Speleoklub Nitra")
        issued_qr = issue_signed_ecp_qr(
            member=member,
            club=club,
            valid_until=date(2027, 12, 31),
            private_key_pem=private_key_pem,
            key_id="key-2026",
            ecp_hash="abcdef1234567890",
            verification_url="https://ecp.sss.sk/v/token42",
        )

        from wallet_pass import build_google_wallet_generic_object
        obj = build_google_wallet_generic_object(
            member=member,
            club=club,
            issued_qr=issued_qr,
            issuer_id="3388000000022877308",
            verification_url="https://ecp.sss.sk/v/token42",
        )

        self.assertEqual(obj["cardTitle"]["defaultValue"]["value"], "Slovenská speleologická spoločnosť")
        self.assertEqual(obj["header"]["defaultValue"]["value"], "Ing. Janko Hrasko")
        self.assertEqual(obj["subheader"]["defaultValue"]["value"], "Speleoklub Nitra")
        self.assertEqual(obj["barcode"]["value"], issued_qr.qr_data)
        self.assertEqual(obj["barcode"]["alternateText"], "eCP 42")
        self.assertIn("linksModuleData", obj)
        self.assertEqual(obj["linksModuleData"]["uris"][0]["uri"], "https://ecp.sss.sk/v/token42")

    def test_build_apple_wallet_pass_dict(self):
        private_key_pem, _ = generate_ecp_signing_key_pair()
        member = SimpleNamespace(
            member_id=42,
            title_prefix="",
            first_name="Janko",
            last_name="Hrasko",
            title_suffix="",
            status="active",
        )
        club = SimpleNamespace(club_id=1, name="Speleoklub Nitra")
        issued_qr = issue_signed_ecp_qr(
            member=member,
            club=club,
            valid_until=date(2027, 12, 31),
            private_key_pem=private_key_pem,
            key_id="key-2026",
            verification_url="https://ecp.sss.sk/v/token42",
        )

        from wallet_pass import build_apple_wallet_pass_dict
        pass_dict = build_apple_wallet_pass_dict(
            member=member,
            club=club,
            issued_qr=issued_qr,
            verification_url="https://ecp.sss.sk/v/token42",
        )

        self.assertEqual(pass_dict["passTypeIdentifier"], "pass.sk.sss.ecp")
        self.assertEqual(pass_dict["organizationName"], "Slovenská speleologická spoločnosť")
        self.assertEqual(pass_dict["barcodes"][0]["message"], issued_qr.qr_data)
        self.assertEqual(pass_dict["barcodes"][0]["altText"], "eCP 42")
        self.assertEqual(pass_dict["generic"]["primaryFields"][0]["value"], "Janko Hrasko")
        self.assertEqual(pass_dict["generic"]["secondaryFields"][0]["value"], "Speleoklub Nitra")


if __name__ == "__main__":
    unittest.main()
