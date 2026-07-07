import base64
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
from io import BytesIO
import json
from pathlib import Path
import secrets
from typing import Callable

import qrcode

from ecp_card import build_ecp_card_assets, build_verification_page_html, public_gcs_url
from ecp_documents import DEFAULT_LEGAL_DOCUMENT_URL, default_legal_documents
from ecp_qr import create_ecp_claim, sign_ecp_claim


class EcpSigningConfigError(RuntimeError):
    pass


class EcpQrUploadError(RuntimeError):
    pass


@dataclass(frozen=True)
class EcpSigningConfig:
    private_key_pem: str
    key_id: str


@dataclass(frozen=True)
class IssuedSignedEcpQr:
    payload: dict
    qr_data: str
    qr_png: bytes
    blob_name: str
    payload_hash: str
    key_id: str
    issued_at: datetime
    valid_until: date
    verification_url: str | None = None
    legal_documents: list[dict] | None = None


@dataclass(frozen=True)
class IssuedEcpDeliveryBundle:
    issued_qr: IssuedSignedEcpQr
    qr_url: str | None
    verification_url: str
    verification_blob_name: str
    card_image: bytes
    card_pdf: bytes
    card_image_url: str
    card_pdf_url: str
    card_image_blob_name: str
    card_pdf_blob_name: str
    legal_document_url: str


def _normalise_pem(value: str) -> str:
    return value.strip().replace("\\n", "\n")


def load_ecp_signing_config(get_secret: Callable[[str], str | None]) -> EcpSigningConfig:
    private_key_pem = get_secret("ecp_signing_private_key_pem")
    private_key_b64 = get_secret("ecp_signing_private_key_b64")
    key_id = get_secret("ecp_signing_key_id")

    if not private_key_pem and private_key_b64:
        private_key_pem = base64.b64decode(private_key_b64).decode("utf-8")

    if not private_key_pem:
        raise EcpSigningConfigError("Missing eCP signing private key secret.")
    if not key_id:
        raise EcpSigningConfigError("Missing eCP signing key id secret.")

    return EcpSigningConfig(private_key_pem=_normalise_pem(private_key_pem), key_id=key_id.strip())


def member_display_name(member) -> str:
    parts = [
        getattr(member, "title_prefix", None),
        getattr(member, "first_name", None),
        getattr(member, "last_name", None),
        getattr(member, "title_suffix", None),
    ]
    return " ".join(str(part).strip() for part in parts if part and str(part).strip())


def calculate_ecp_valid_until(issued_on=None) -> date:
    if issued_on is None:
        issued_on = date.today()
    if isinstance(issued_on, datetime):
        issued_on = issued_on.date()
    try:
        return issued_on.replace(year=issued_on.year + 1)
    except ValueError:
        return issued_on.replace(year=issued_on.year + 1, day=28)


def _qr_png_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def issue_signed_ecp_qr(
    member,
    club,
    valid_until: date,
    private_key_pem: bytes | str,
    key_id: str,
    paid_year: int | None = None,
    issued_at: datetime | None = None,
    ecp_hash: str | None = None,
    verification_url: str | None = None,
    legal_documents: list[dict] | None = None,
) -> IssuedSignedEcpQr:
    if issued_at is None:
        issued_at = datetime.now().astimezone()
    claim = create_ecp_claim(
        member_id=getattr(member, "member_id"),
        display_name=member_display_name(member),
        club_name=getattr(club, "name", "") or "",
        status=getattr(member, "status", "active") or "active",
        valid_until=valid_until,
        paid_year=paid_year,
        issued_at=issued_at,
        verification_url=verification_url,
        legal_documents=legal_documents,
    )
    payload = sign_ecp_claim(claim, private_key_pem, key_id=key_id)
    qr_data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    blob_hash = ecp_hash or f"member-{getattr(member, 'member_id')}"
    return IssuedSignedEcpQr(
        payload=payload,
        qr_data=qr_data,
        qr_png=_qr_png_bytes(qr_data),
        blob_name=f"ecp_qr/{blob_hash}.png",
        payload_hash=hashlib.sha256(qr_data.encode("utf-8")).hexdigest(),
        key_id=key_id,
        issued_at=issued_at,
        valid_until=valid_until,
        verification_url=verification_url,
        legal_documents=legal_documents,
    )


def issue_and_upload_signed_ecp_qr(
    member,
    club,
    ecp_hash: str,
    get_secret: Callable[[str], str | None],
    upload_blob: Callable[[str, bytes, str], str | None],
    valid_until: date | None = None,
    paid_year: int | None = None,
    issued_at: datetime | None = None,
) -> tuple[IssuedSignedEcpQr, str | None]:
    """Issue a signed payload without uploading a standalone QR PNG.

    Google Wallet renders the QR natively from barcode.value. The generated PNG
    remains available on IssuedSignedEcpQr for JPG/PDF card rendering only.
    """
    signing_config = load_ecp_signing_config(get_secret)
    if valid_until is None:
        valid_until = calculate_ecp_valid_until(issued_at)
    if paid_year is None:
        paid_year = valid_until.year

    issued_qr = issue_signed_ecp_qr(
        member=member,
        club=club,
        valid_until=valid_until,
        private_key_pem=signing_config.private_key_pem,
        key_id=signing_config.key_id,
        paid_year=paid_year,
        issued_at=issued_at,
        ecp_hash=ecp_hash,
    )
    return issued_qr, None


def _verification_blob_name(ecp_hash: str, token: str | None = None, path_prefix: str = "ecp_verify") -> str:
    token = token or secrets.token_urlsafe(24)
    return f"{path_prefix.strip('/')}/{token}.html"


def _verification_url(bucket_name: str, blob_name: str, public_base_url: str | None = None) -> str:
    if public_base_url:
        token_name = blob_name.rsplit("/", 1)[-1].removesuffix(".html")
        return f"{public_base_url.rstrip('/')}/{token_name}"
    return public_gcs_url(bucket_name, blob_name)


def _write_verification_html_to_webroot(webroot: str, blob_name: str, content: bytes) -> str:
    root = Path(webroot).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve()
    target = (root / blob_name).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise EcpQrUploadError("eCP verification page path escapes configured webroot.") from exc

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return str(target)


def issue_and_upload_ecp_delivery_bundle(
    member,
    club,
    ecp_hash: str,
    get_secret: Callable[[str], str | None],
    upload_blob: Callable[[str, bytes, str], str | None],
    valid_until: date | None = None,
    paid_year: int | None = None,
    issued_at: datetime | None = None,
    portrait_image: bytes | None = None,
    portrait_url: str | None = None,
    legal_document_url: str = DEFAULT_LEGAL_DOCUMENT_URL,
) -> IssuedEcpDeliveryBundle:
    bucket_name = get_secret("bucket_name")
    if not bucket_name:
        raise EcpSigningConfigError("Missing bucket_name secret for eCP verification page URL.")

    public_verification_base_url = (get_secret("ecp_verification_base_url") or "").strip()
    verification_path_prefix = "v" if public_verification_base_url else "ecp_verify"
    verification_blob_name = _verification_blob_name(ecp_hash, path_prefix=verification_path_prefix)
    verification_url = _verification_url(bucket_name, verification_blob_name, public_verification_base_url)
    legal_documents = default_legal_documents()
    if legal_document_url != DEFAULT_LEGAL_DOCUMENT_URL:
        legal_documents = [{
            "name": "Vseobecna vynimka pre pohyb mimo vyznacenych chodnikov",
            "url": legal_document_url,
        }]

    signing_config = load_ecp_signing_config(get_secret)
    if valid_until is None:
        valid_until = calculate_ecp_valid_until(issued_at)
    if paid_year is None:
        paid_year = valid_until.year

    issued_qr = issue_signed_ecp_qr(
        member=member,
        club=club,
        valid_until=valid_until,
        private_key_pem=signing_config.private_key_pem,
        key_id=signing_config.key_id,
        paid_year=paid_year,
        issued_at=issued_at,
        ecp_hash=ecp_hash,
        verification_url=verification_url,
        legal_documents=legal_documents,
    )

    qr_url = None

    card_image, card_pdf = build_ecp_card_assets(
        member=member,
        club=club,
        issued_qr=issued_qr,
        portrait_image=portrait_image,
    )
    card_image_blob_name = f"ecp_cards/{ecp_hash}.jpg"
    card_pdf_blob_name = f"ecp_cards/{ecp_hash}.pdf"
    card_image_url = upload_blob(card_image_blob_name, card_image, "image/jpeg")
    if not card_image_url:
        raise EcpQrUploadError("eCP card JPG upload failed.")
    card_pdf_url = upload_blob(card_pdf_blob_name, card_pdf, "application/pdf")
    if not card_pdf_url:
        raise EcpQrUploadError("eCP card PDF upload failed.")

    verification_html = build_verification_page_html(
        member=member,
        club=club,
        issued_qr=issued_qr,
        qr_url=qr_url,
        card_image_url=card_image_url,
        card_pdf_url=card_pdf_url,
        portrait_url=portrait_url,
        legal_document_url=legal_document_url,
    )
    verification_webroot = (get_secret("ecp_verification_webroot") or "").strip()
    if verification_webroot:
        uploaded_verification_url = _write_verification_html_to_webroot(
            verification_webroot,
            verification_blob_name,
            verification_html,
        )
    else:
        uploaded_verification_url = upload_blob(
            verification_blob_name,
            verification_html,
            "text/html; charset=utf-8",
        )
    if not uploaded_verification_url:
        raise EcpQrUploadError("eCP verification page upload failed.")

    return IssuedEcpDeliveryBundle(
        issued_qr=issued_qr,
        qr_url=qr_url,
        verification_url=verification_url,
        verification_blob_name=verification_blob_name,
        card_image=card_image,
        card_pdf=card_pdf,
        card_image_url=card_image_url,
        card_pdf_url=card_pdf_url,
        card_image_blob_name=card_image_blob_name,
        card_pdf_blob_name=card_pdf_blob_name,
        legal_document_url=legal_document_url,
    )
