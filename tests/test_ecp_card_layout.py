"""Regression tests for the eCP card layout.

The card is rendered with absolute pixel coordinates and the member text column
sits directly left of the QR box. Before these tests, a long member name was
painted across the QR modules, which produced a card that looked fine to the
issuer but could not be scanned.
"""

import unittest
from datetime import date, datetime, timedelta
from io import BytesIO
from types import SimpleNamespace

from PIL import Image

from ecp_card import (
    QR_BOX,
    TEXT_COLUMN_MAX_WIDTH,
    build_ecp_card_assets,
    _format_date,
    _format_status,
)
from ecp_issuance import issue_signed_ecp_qr
from ecp_qr import generate_ecp_signing_key_pair

LONG_NAME = "Ing. Bohuslava Podhradska PhD."
LONG_CLUB = "Speleoklub Slovensky kras Roznava"


def _member(first_name="Jan", last_name="Jaskyniar", title_prefix="", title_suffix=""):
    return SimpleNamespace(
        member_id=4242,
        first_name=first_name,
        last_name=last_name,
        title_prefix=title_prefix,
        title_suffix=title_suffix,
        status="active",
        ecp_hash="test-ecp-hash",
    )


def _club(name="Speleoklub Test"):
    return SimpleNamespace(club_id=1, name=name)


def _issued_qr(member, club):
    private_key_pem, _public_key_pem = generate_ecp_signing_key_pair()
    issued_at = datetime.now().astimezone()
    return issue_signed_ecp_qr(
        member=member,
        club=club,
        valid_until=(issued_at + timedelta(days=365)).date(),
        private_key_pem=private_key_pem,
        key_id="test-key",
        issued_at=issued_at,
        ecp_hash=member.ecp_hash,
        verification_url="https://ecp.sss.sk/ecp_verify/test.html",
    )


class EcpCardQrIntegrityTests(unittest.TestCase):
    def _render(self, member, club):
        issued_qr = _issued_qr(member, club)
        image_bytes, _pdf_bytes = build_ecp_card_assets(member, club, issued_qr)
        return issued_qr, Image.open(BytesIO(image_bytes)).convert("RGB")

    def test_long_name_does_not_overwrite_qr_region(self):
        long_member = _member(first_name="Bohuslava", last_name="Podhradska", title_prefix="Ing.", title_suffix="PhD.")
        long_club = _club(LONG_CLUB)
        issued_qr, long_card = self._render(long_member, long_club)

        short_member = _member()
        short_card = build_ecp_card_assets(short_member, _club(), issued_qr)[0]
        short_card = Image.open(BytesIO(short_card)).convert("RGB")

        box = (QR_BOX[0], QR_BOX[1], QR_BOX[2], QR_BOX[3])
        self.assertEqual(
            long_card.crop(box).tobytes(),
            short_card.crop(box).tobytes(),
            "member text bled into the QR region - the card would be unscannable",
        )

    def test_qr_on_card_is_still_decodable(self):
        try:
            import cv2
            import numpy as np
        except ImportError:  # pragma: no cover - optional dependency
            self.skipTest("opencv is not installed")

        member = _member(first_name="Bohuslava", last_name="Podhradska", title_prefix="Ing.", title_suffix="PhD.")
        issued_qr, card = self._render(member, _club(LONG_CLUB))

        detector = cv2.QRCodeDetector()
        decoded, _points, _straight = detector.detectAndDecode(np.array(card)[:, :, ::-1])
        self.assertEqual(decoded, issued_qr.qr_data)

    def test_text_column_never_reaches_the_qr_box(self):
        self.assertLess(TEXT_COLUMN_MAX_WIDTH, QR_BOX[0])
        member = _member(first_name="Bohuslava", last_name="Podhradska", title_prefix="Ing.", title_suffix="PhD.")
        _issued, card = self._render(member, _club(LONG_CLUB))

        # The gutter left of the QR box must stay card background (#f7faf9);
        # JPEG compression shifts channels slightly, so compare with tolerance.
        background = card.getpixel((QR_BOX[0] - 6, 180))
        for channel, expected in zip(background, (247, 250, 249)):
            self.assertAlmostEqual(channel, expected, delta=8)


class EcpCardFormattingTests(unittest.TestCase):
    def test_format_date_accepts_iso_strings(self):
        self.assertEqual(_format_date("2026-08-26T20:41:30+00:00"), "2026-08-26")
        self.assertEqual(_format_date("2026-08-26T20:41:30Z"), "2026-08-26")
        self.assertEqual(_format_date("2026-08-26"), "2026-08-26")

    def test_format_date_accepts_date_objects(self):
        self.assertEqual(_format_date(date(2026, 8, 26)), "2026-08-26")
        self.assertEqual(_format_date(datetime(2026, 8, 26, 20, 41)), "2026-08-26")

    def test_format_date_is_tolerant(self):
        self.assertEqual(_format_date(None), "")
        self.assertEqual(_format_date(""), "")
        self.assertEqual(_format_date("neznamy"), "neznamy")

    def test_format_status_maps_internal_values(self):
        self.assertEqual(_format_status("active"), "Aktívny")
        self.assertEqual(_format_status("SUSPENDED"), "Pozastavený")

    def test_format_status_passes_through_unknown_values(self):
        self.assertEqual(_format_status("nieco_ine"), "nieco_ine")
        self.assertEqual(_format_status(None), "")


if __name__ == "__main__":
    unittest.main()
