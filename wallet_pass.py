import json


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
