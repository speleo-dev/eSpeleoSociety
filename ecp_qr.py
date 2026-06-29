import base64
from copy import deepcopy
from datetime import date, datetime, timezone
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


PAYLOAD_ALGORITHM = "EdDSA-Ed25519"


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _canonical_json(data) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _date_to_iso(value) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def generate_ecp_signing_key_pair() -> tuple[bytes, bytes]:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def create_ecp_claim(
    member_id: int,
    display_name: str,
    club_name: str,
    status: str,
    valid_until,
    paid_year: int | None = None,
    issued_at=None,
    verification_url: str | None = None,
    legal_documents: list[dict] | None = None,
) -> dict:
    if issued_at is None:
        issued_at = datetime.now(timezone.utc)

    claim = {
        "schema": "eSpeleoSociety.eCP.v1",
        "member_id": int(member_id),
        "display_name": display_name,
        "club_name": club_name,
        "status": status,
        "valid_until": _date_to_iso(valid_until),
        "issued_at": _date_to_iso(issued_at),
    }
    if paid_year is not None:
        claim["paid_year"] = int(paid_year)
    if verification_url:
        claim["verification_url"] = verification_url
    if legal_documents:
        claim["legal_documents"] = deepcopy(legal_documents)
    return claim


def sign_ecp_claim(claim: dict, private_key_pem: bytes | str, key_id: str) -> dict:
    if isinstance(private_key_pem, str):
        private_key_pem = private_key_pem.encode("utf-8")
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)

    payload = {
        "alg": PAYLOAD_ALGORITHM,
        "kid": key_id,
        "claim": deepcopy(claim),
    }
    signature = private_key.sign(_canonical_json(payload))
    payload["sig"] = _base64url_encode(signature)
    return payload


def verify_ecp_payload(payload: dict, public_key_pem: bytes | str, now=None) -> bool:
    if isinstance(public_key_pem, str):
        public_key_pem = public_key_pem.encode("utf-8")
    if now is None:
        now = date.today()
    if isinstance(now, datetime):
        now = now.date()

    try:
        signature = _base64url_decode(payload["sig"])
        signed_payload = deepcopy(payload)
        signed_payload.pop("sig")
        public_key = serialization.load_pem_public_key(public_key_pem)
        public_key.verify(signature, _canonical_json(signed_payload))

        valid_until = date.fromisoformat(payload["claim"]["valid_until"])
        return now <= valid_until
    except (KeyError, ValueError, InvalidSignature):
        return False
