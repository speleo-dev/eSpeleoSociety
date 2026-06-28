import base64
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
from io import BytesIO
import json
from typing import Callable

import qrcode

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
) -> tuple[IssuedSignedEcpQr, str]:
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
    qr_url = upload_blob(issued_qr.blob_name, issued_qr.qr_png, "image/png")
    if not qr_url:
        raise EcpQrUploadError("Signed eCP QR upload failed.")
    return issued_qr, qr_url
