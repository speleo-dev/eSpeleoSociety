import base64
from datetime import date, datetime, timezone
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import unittest

from ecp_qr import generate_ecp_signing_key_pair, verify_ecp_payload
from ecp_issuance import (
    EcpSigningConfigError,
    calculate_ecp_valid_until,
    issue_and_upload_ecp_delivery_bundle,
    issue_signed_ecp_qr,
    issue_and_upload_signed_ecp_qr,
    load_ecp_signing_config,
)


class EcpIssuanceTest(unittest.TestCase):
    def test_calculate_ecp_valid_until_defaults_to_one_year(self):
        self.assertEqual(calculate_ecp_valid_until(date(2026, 6, 22)), date(2027, 6, 22))
        self.assertEqual(calculate_ecp_valid_until(date(2024, 2, 29)), date(2025, 2, 28))

    def test_issue_signed_ecp_qr_generates_verifiable_payload_and_png(self):
        private_key_pem, public_key_pem = generate_ecp_signing_key_pair()
        member = SimpleNamespace(
            member_id=123,
            title_prefix="Ing.",
            first_name="Ada",
            last_name="Lovelace",
            title_suffix="PhD.",
            status="active",
        )
        club = SimpleNamespace(club_id=9, name="Speleo Club")

        issued = issue_signed_ecp_qr(
            member=member,
            club=club,
            valid_until=date(2027, 6, 22),
            private_key_pem=private_key_pem,
            key_id="test-key",
            paid_year=2027,
            issued_at=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
            ecp_hash="abc123",
        )

        self.assertEqual(issued.payload["claim"]["display_name"], "Ing. Ada Lovelace PhD.")
        self.assertEqual(issued.payload["claim"]["club_name"], "Speleo Club")
        self.assertEqual(issued.payload["claim"]["status"], "active")
        self.assertEqual(issued.payload["claim"]["paid_year"], 2027)
        self.assertTrue(verify_ecp_payload(issued.payload, public_key_pem, now=date(2026, 6, 22)))
        self.assertTrue(issued.qr_png.startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(issued.blob_name, "ecp_qr/abc123.png")
        self.assertEqual(issued.key_id, "test-key")
        self.assertEqual(issued.valid_until, date(2027, 6, 22))
        self.assertEqual(issued.issued_at, datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc))
        self.assertEqual(len(issued.payload_hash), 64)

    def test_load_ecp_signing_config_accepts_escaped_pem_from_secrets(self):
        private_key_pem, _ = generate_ecp_signing_key_pair()
        escaped_pem = private_key_pem.decode("utf-8").replace("\n", "\\n")

        config = load_ecp_signing_config({
            "ecp_signing_private_key_pem": escaped_pem,
            "ecp_signing_key_id": "key-2026",
        }.get)

        self.assertIn("BEGIN PRIVATE KEY", config.private_key_pem)
        self.assertIn("\n", config.private_key_pem)
        self.assertEqual(config.key_id, "key-2026")

    def test_load_ecp_signing_config_requires_key_and_key_id(self):
        with self.assertRaises(EcpSigningConfigError):
            load_ecp_signing_config({}.get)

        with self.assertRaises(EcpSigningConfigError):
            load_ecp_signing_config({"ecp_signing_private_key_pem": "x"}.get)

    def test_issue_and_upload_signed_ecp_qr_uploads_png_and_returns_url(self):
        private_key_pem, public_key_pem = generate_ecp_signing_key_pair()
        member = SimpleNamespace(
            member_id=123,
            title_prefix="",
            first_name="Ada",
            last_name="Lovelace",
            title_suffix="",
            status="active",
        )
        club = SimpleNamespace(club_id=9, name="Speleo Club")
        uploads = []

        def upload(blob_name, data, content_type):
            uploads.append((blob_name, data, content_type))
            return f"https://example.test/{blob_name}"

        issued, qr_url = issue_and_upload_signed_ecp_qr(
            member=member,
            club=club,
            ecp_hash="abc123",
            get_secret={
                "ecp_signing_private_key_pem": private_key_pem.decode("utf-8"),
                "ecp_signing_key_id": "key-2026",
            }.get,
            upload_blob=upload,
            valid_until=date(2027, 6, 22),
            issued_at=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
        )

        self.assertIsNone(qr_url)
        self.assertEqual(uploads, [])
        self.assertTrue(verify_ecp_payload(issued.payload, public_key_pem, now=date(2026, 6, 22)))
        self.assertEqual(issued.key_id, "key-2026")
        self.assertEqual(len(issued.payload_hash), 64)

    def test_issue_and_upload_ecp_delivery_bundle_skips_qr_png_upload_and_uses_public_verify_domain(self):
        private_key_pem, public_key_pem = generate_ecp_signing_key_pair()
        member = SimpleNamespace(
            member_id=123,
            title_prefix="",
            first_name="Ada",
            last_name="Lovelace",
            title_suffix="",
            status="active",
            portrait_url="https://storage.example/portraits/123.jpg",
        )
        club = SimpleNamespace(club_id=9, name="Speleo Club")
        uploads = []

        def upload(blob_name, data, content_type):
            uploads.append((blob_name, data, content_type))
            return f"https://storage.example/{blob_name}"

        bundle = issue_and_upload_ecp_delivery_bundle(
            member=member,
            club=club,
            ecp_hash="abc123",
            get_secret={
                "ecp_signing_private_key_pem": private_key_pem.decode("utf-8"),
                "ecp_signing_key_id": "key-2026",
                "bucket_name": "ecp-test-bucket",
                "ecp_verification_base_url": "https://ecp.sss.sk/v",
            }.get,
            upload_blob=upload,
            valid_until=date(2027, 6, 22),
            issued_at=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
        )

        self.assertTrue(verify_ecp_payload(bundle.issued_qr.payload, public_key_pem, now=date(2026, 6, 22)))
        self.assertEqual(bundle.issued_qr.payload["claim"]["verification_url"], bundle.verification_url)
        self.assertIn("vynimka.pdf", bundle.issued_qr.payload["claim"]["legal_documents"][0]["url"])
        self.assertTrue(bundle.card_image.startswith(b"\xff\xd8"))
        self.assertTrue(bundle.card_pdf.startswith(b"%PDF"))
        self.assertIsNone(bundle.qr_url)
        self.assertTrue(bundle.verification_url.startswith("https://ecp.sss.sk/v/"))
        uploaded_names = [name for name, _, _ in uploads]
        self.assertFalse(any(name.startswith("ecp_qr/") for name in uploaded_names))
        self.assertIn("ecp_cards/abc123.jpg", uploaded_names)
        self.assertIn("ecp_cards/abc123.pdf", uploaded_names)
        self.assertTrue(any(name.startswith("v/") and name.endswith(".html") for name in uploaded_names))
        self.assertTrue(any(content_type == "text/html; charset=utf-8" for _, _, content_type in uploads))
        verification_upload = next(data for name, data, _ in uploads if name.startswith("v/"))
        self.assertNotIn(b"QR PNG", verification_upload)

    def test_issue_and_upload_ecp_delivery_bundle_can_publish_verification_html_to_webroot(self):
        private_key_pem, public_key_pem = generate_ecp_signing_key_pair()
        member = SimpleNamespace(
            member_id=123,
            first_name="Jana",
            last_name="Novakova",
            title_prefix="",
            title_suffix="",
            status="active",
        )
        club = SimpleNamespace(name="Speleo Klub")
        uploads = []

        def upload(name, data, content_type):
            uploads.append((name, data, content_type))
            return f"https://storage.example/{name}"

        with TemporaryDirectory() as webroot:
            bundle = issue_and_upload_ecp_delivery_bundle(
                member=member,
                club=club,
                ecp_hash="abc123",
                get_secret={
                    "bucket_name": "ecp-test-bucket",
                    "ecp_signing_key_id": "key-2026",
                    "ecp_signing_private_key_b64": base64.b64encode(private_key_pem).decode("ascii"),
                    "ecp_verification_base_url": "https://ecp.sss.sk/v",
                    "ecp_verification_webroot": webroot,
                }.get,
                upload_blob=upload,
                valid_until=date(2027, 6, 22),
                issued_at=datetime(2026, 6, 22, 12, 0, tzinfo=timezone.utc),
            )

            verification_path = f"{webroot}/{bundle.verification_blob_name}"
            with open(verification_path, "rb") as handle:
                verification_html = handle.read()

        uploaded_names = [name for name, _, _ in uploads]
        self.assertIn("ecp_cards/abc123.jpg", uploaded_names)
        self.assertIn("ecp_cards/abc123.pdf", uploaded_names)
        self.assertFalse(any(name.startswith("v/") for name in uploaded_names))
        self.assertTrue(bundle.verification_url.startswith("https://ecp.sss.sk/v/"))
        self.assertIn(b"Jana Novakova", verification_html)
        self.assertTrue(verify_ecp_payload(bundle.issued_qr.payload, public_key_pem, now=date(2026, 6, 22)))


if __name__ == "__main__":
    unittest.main()
