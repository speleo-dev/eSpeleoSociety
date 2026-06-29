def club_to_api(club) -> dict:
    return {
        "id": getattr(club, "club_id", None),
        "name": getattr(club, "name", "") or "",
        "street": getattr(club, "street", "") or "",
        "city": getattr(club, "city", "") or "",
        "zipCode": getattr(club, "zip_code", "") or "",
        "country": getattr(club, "country", "") or "",
        "email": getattr(club, "email", "") or "",
        "phone": getattr(club, "phone", "") or "",
        "webpage": getattr(club, "webpage", "") or "",
        "presidentName": getattr(club, "president_name", "") or "",
        "memberCount": int(getattr(club, "member_count", 0) or 0),
    }


def member_to_api(member) -> dict:
    return {
        "id": getattr(member, "member_id", None),
        "status": getattr(member, "status", "") or "",
        "titlePrefix": getattr(member, "title_prefix", "") or "",
        "firstName": getattr(member, "first_name", "") or "",
        "lastName": getattr(member, "last_name", "") or "",
        "titleSuffix": getattr(member, "title_suffix", "") or "",
        "email": getattr(member, "email", "") or "",
        "phone": getattr(member, "phone", "") or "",
        "primaryClubId": getattr(member, "primary_club_id", None),
        "isPresident": bool(getattr(member, "is_president", False)),
        "hasEcp": bool(getattr(member, "ecp_hash", None)),
    }


def ecp_verification_to_api(record: dict) -> dict:
    return {
        "memberId": record.get("member_id"),
        "displayName": record.get("display_name", ""),
        "clubName": record.get("club_name", ""),
        "status": record.get("status", ""),
        "validUntil": record.get("valid_until"),
        "portraitUrl": record.get("portrait_url"),
        "cardImageUrl": record.get("card_image_url"),
        "cardPdfUrl": record.get("card_pdf_url"),
        "legalDocumentUrl": record.get("legal_document_url"),
        "payloadHash": record.get("qr_payload_hash"),
    }
