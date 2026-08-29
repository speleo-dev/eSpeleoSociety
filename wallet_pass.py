import json
import time
from typing import Callable


def build_wallet_barcode(issued_qr, alternate_text: str | None = None) -> dict:
    claim = issued_qr.payload.get("claim", {}) if getattr(issued_qr, "payload", None) else {}
    member_id = claim.get("member_id")
    if alternate_text is None:
        alternate_text = f"eCP {member_id}" if member_id is not None else "eCP"
    return {
        "type": "QR_CODE",
        "value": issued_qr.qr_data,
        "alternateText": alternate_text,
    }


def build_wallet_barcode_from_request(req_details, get_field) -> dict:
    qr_data = get_field(req_details, "signed_qr_data")
    if not qr_data:
        signed_payload = get_field(req_details, "signed_qr_payload")
        if signed_payload:
            qr_data = json.dumps(signed_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    if not qr_data:
        raise ValueError("Missing signed QR data for Google Wallet barcode.")

    member_id = get_field(req_details, "member_id")
    alternate_text = f"eCP {member_id}" if member_id is not None else "eCP"
    return {
        "type": "QR_CODE",
        "value": qr_data,
        "alternateText": alternate_text,
    }


def _member_name(member) -> str:
    parts = [
        getattr(member, "title_prefix", None),
        getattr(member, "first_name", None),
        getattr(member, "last_name", None),
        getattr(member, "title_suffix", None),
    ]
    return " ".join(str(p).strip() for p in parts if p and str(p).strip()) or "Člen SSS"


def build_google_wallet_generic_object(
    member,
    club,
    issued_qr,
    issuer_id: str,
    class_id: str | None = None,
    object_id: str | None = None,
    verification_url: str | None = None,
) -> dict:
    """Builds a Google Wallet GenericObject definition with embedded barcode and member details."""
    member_id = getattr(member, "member_id", "0")
    ecp_hash = getattr(issued_qr, "payload_hash", "0")[:16]
    actual_class_id = class_id or f"{issuer_id}.espeleo_member_card"
    actual_object_id = object_id or f"{issuer_id}.member_{member_id}_{ecp_hash}"

    claim = getattr(issued_qr, "payload", {}).get("claim", {})
    valid_until = claim.get("valid_until") or str(getattr(issued_qr, "valid_until", ""))
    club_name = getattr(club, "name", "") or claim.get("club_name", "") or "Slovenská speleologická spoločnosť"
    display_name = _member_name(member)

    obj = {
        "id": actual_object_id,
        "classId": actual_class_id,
        "genericType": "GENERIC_OTHER",
        "hexBackgroundColor": "#0b4a46",
        "logo": {
            "sourceUri": {
                "uri": "https://sss.sk/wp-content/uploads/2020/05/logo_sss.png"
            }
        },
        "cardTitle": {
            "defaultValue": {
                "language": "sk",
                "value": "Slovenská speleologická spoločnosť"
            }
        },
        "header": {
            "defaultValue": {
                "language": "sk",
                "value": display_name
            }
        },
        "subheader": {
            "defaultValue": {
                "language": "sk",
                "value": club_name
            }
        },
        "barcode": {
            "type": "QR_CODE",
            "value": issued_qr.qr_data,
            "alternateText": f"eCP {member_id}"
        },
        "textModulesData": [
            {
                "id": "member_id",
                "header": "Členské číslo",
                "body": str(member_id)
            },
            {
                "id": "valid_until",
                "header": "Platnosť do",
                "body": str(valid_until)
            },
            {
                "id": "status",
                "header": "Stav",
                "body": "Aktívny"
            }
        ]
    }

    if verification_url:
        obj["linksModuleData"] = {
            "uris": [
                {
                    "uri": verification_url,
                    "description": "Online overenie preukazu eCP",
                    "id": "verification_link"
                },
                {
                    "uri": "https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf",
                    "description": "Všeobecná výnimka MŽP SR",
                    "id": "legal_doc"
                }
            ]
        }

    return obj


def create_google_wallet_jwt_save_url(
    generic_object: dict,
    service_account_email: str,
    private_key_pem: str,
) -> str:
    """Signs Google Wallet GenericObject into a JWT save link."""
    import jwt

    claims = {
        "iss": service_account_email,
        "aud": "google",
        "origins": ["https://sss.sk", "https://ecp.sss.sk"],
        "typ": "savetowallet",
        "iat": int(time.time()),
        "payload": {
            "genericObjects": [generic_object]
        }
    }

    token = jwt.encode(claims, private_key_pem, algorithm="RS256")
    return f"https://pay.google.com/gp/v/save/{token}"


def build_apple_wallet_pass_dict(
    member,
    club,
    issued_qr,
    verification_url: str | None = None,
) -> dict:
    """Builds an Apple Wallet pass.json structure for a Generic Membership Card."""
    member_id = getattr(member, "member_id", "0")
    claim = getattr(issued_qr, "payload", {}).get("claim", {})
    valid_until = claim.get("valid_until") or str(getattr(issued_qr, "valid_until", ""))
    club_name = getattr(club, "name", "") or claim.get("club_name", "") or "Slovenská speleologická spoločnosť"
    display_name = _member_name(member)

    pass_dict = {
        "formatVersion": 1,
        "passTypeIdentifier": "pass.sk.sss.ecp",
        "organizationName": "Slovenská speleologická spoločnosť",
        "description": "Elektronický členský preukaz SSS",
        "logoText": "SSS",
        "foregroundColor": "rgb(255, 255, 255)",
        "backgroundColor": "rgb(11, 74, 70)",
        "labelColor": "rgb(190, 220, 215)",
        "barcodes": [
            {
                "format": "PKBarcodeFormatQR",
                "message": issued_qr.qr_data,
                "messageEncoding": "iso-8859-1",
                "altText": f"eCP {member_id}"
            }
        ],
        "generic": {
            "primaryFields": [
                {
                    "key": "member_name",
                    "label": "Člen",
                    "value": display_name
                }
            ],
            "secondaryFields": [
                {
                    "key": "club",
                    "label": "Klub / Skupina",
                    "value": club_name
                }
            ],
            "auxiliaryFields": [
                {
                    "key": "member_id",
                    "label": "Číslo člena",
                    "value": str(member_id)
                },
                {
                    "key": "valid_until",
                    "label": "Platnosť",
                    "value": str(valid_until)
                }
            ],
            "backFields": [
                {
                    "key": "issuer",
                    "label": "Vystavovateľ",
                    "value": "Slovenská speleologická spoločnosť (SSS)"
                },
                {
                    "key": "web",
                    "label": "Webstránka",
                    "value": "https://sss.sk"
                }
            ]
        }
    }

    if verification_url:
        pass_dict["generic"]["backFields"].append({
            "key": "verification_url",
            "label": "Online overenie",
            "value": verification_url
        })

    return pass_dict

