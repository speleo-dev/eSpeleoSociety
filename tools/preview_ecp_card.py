"""Offline preview renderer for the eCP card, PDF and verification page.

Renders the real production artifacts (``ecp_card.build_ecp_card_assets`` and
``ecp_card.build_verification_page_html``) from synthetic data so the visual
design can be iterated without a database, Google Cloud bucket, FTP server or
configured signing key. A throwaway Ed25519 key pair is generated per run.

Usage::

    python tools/preview_ecp_card.py
    python tools/preview_ecp_card.py --out /tmp/ecp-preview --portrait path/to/face.jpg
    python tools/preview_ecp_card.py --name "Jan Novak" --club "Speleoklub Tribec" --status inactive
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ecp_card import build_ecp_card_assets, build_verification_page_html  # noqa: E402
from ecp_documents import DEFAULT_LEGAL_DOCUMENT_URL, default_legal_documents  # noqa: E402
from ecp_issuance import issue_signed_ecp_qr  # noqa: E402
from ecp_qr import generate_ecp_signing_key_pair  # noqa: E402

PREVIEW_KEY_ID = "preview-key"
PREVIEW_VERIFICATION_URL = "https://ecp.sss.sk/ecp_verify/preview.html"


def _split_name(full_name: str) -> tuple[str, str]:
    parts = [part for part in full_name.split() if part]
    if not parts:
        return "Jan", "Jaskyniar"
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def _build_member(name: str, member_id: int, status: str) -> SimpleNamespace:
    first_name, last_name = _split_name(name)
    return SimpleNamespace(
        member_id=member_id,
        first_name=first_name,
        last_name=last_name,
        title_prefix="",
        title_suffix="",
        status=status,
        ecp_hash="preview-ecp-hash",
    )


def _build_club(club_name: str) -> SimpleNamespace:
    return SimpleNamespace(club_id=1, name=club_name, webpage="https://sss.sk")


def _read_portrait(portrait_path: str | None) -> bytes | None:
    if not portrait_path:
        return None
    path = Path(portrait_path).expanduser()
    if not path.is_file():
        raise SystemExit(f"Portrait file not found: {path}")
    return path.read_bytes()


def render_preview(
    out_dir: Path,
    name: str,
    club_name: str,
    member_id: int,
    status: str,
    portrait_path: str | None = None,
    valid_until: date | None = None,
) -> dict[str, Path]:
    member = _build_member(name, member_id, status)
    club = _build_club(club_name)
    portrait_image = _read_portrait(portrait_path)

    private_key_pem, _public_key_pem = generate_ecp_signing_key_pair()
    issued_at = datetime.now().astimezone()
    if valid_until is None:
        valid_until = (issued_at + timedelta(days=365)).date()

    issued_qr = issue_signed_ecp_qr(
        member=member,
        club=club,
        valid_until=valid_until,
        private_key_pem=private_key_pem,
        key_id=PREVIEW_KEY_ID,
        paid_year=issued_at.year,
        issued_at=issued_at,
        ecp_hash=member.ecp_hash,
        verification_url=PREVIEW_VERIFICATION_URL,
        legal_documents=default_legal_documents(),
    )

    card_image, card_pdf = build_ecp_card_assets(member, club, issued_qr, portrait_image)

    out_dir.mkdir(parents=True, exist_ok=True)
    card_image_path = out_dir / "ecp_card.jpg"
    card_pdf_path = out_dir / "ecp_card.pdf"
    qr_path = out_dir / "ecp_qr.png"
    verification_path = out_dir / "verification.html"

    card_image_path.write_bytes(card_image)
    card_pdf_path.write_bytes(card_pdf)
    qr_path.write_bytes(issued_qr.qr_png)

    verification_html = build_verification_page_html(
        member=member,
        club=club,
        issued_qr=issued_qr,
        qr_url=qr_path.as_uri(),
        card_image_url=card_image_path.as_uri(),
        card_pdf_url=card_pdf_path.as_uri(),
        portrait_url=None,
        legal_document_url=DEFAULT_LEGAL_DOCUMENT_URL,
    )
    verification_path.write_bytes(verification_html)

    return {
        "card_image": card_image_path,
        "card_pdf": card_pdf_path,
        "qr": qr_path,
        "verification": verification_path,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="build/ecp-preview", help="Output directory (default: build/ecp-preview)")
    parser.add_argument("--name", default="Jan Jaskyniar", help="Member display name used on the card")
    parser.add_argument("--club", default="Speleoklub Preview", help="Club name used on the card")
    parser.add_argument("--member-id", type=int, default=4242, help="Member id printed on the card")
    parser.add_argument("--status", default="active", help="Membership status printed on the card")
    parser.add_argument("--portrait", default=None, help="Optional portrait image file to embed")
    args = parser.parse_args(argv)

    artifacts = render_preview(
        out_dir=Path(args.out).expanduser(),
        name=args.name,
        club_name=args.club,
        member_id=args.member_id,
        status=args.status,
        portrait_path=args.portrait,
    )

    print("eCP preview artifacts:")
    for label, path in artifacts.items():
        print(f"  {label:<12} {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
