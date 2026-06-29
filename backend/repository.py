import re


TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{12,256}(?:\.html)?$")


class DatabaseApiRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def fetch_clubs(self):
        return self.db_manager.fetch_clubs()

    def fetch_members(self, club_id: int):
        return self.db_manager.fetch_members(club_id)

    def fetch_ecp_verification_by_token(self, token: str):
        if not TOKEN_RE.match(token or ""):
            return None
        normalized_token = token if token.endswith(".html") else f"{token}.html"
        row = self.db_manager._fetch_one(
            """
            SELECT
                m.member_id,
                trim(concat_ws(' ', NULLIF(m.title_prefix, ''), m.first_name, m.last_name, NULLIF(m.title_suffix, ''))) AS display_name,
                COALESCE(c.club_name, '') AS club_name,
                m.member_status AS status,
                er.valid_until,
                m.portrait_url,
                er.card_image_url,
                er.card_pdf_url,
                er.legal_document_url,
                er.qr_payload_hash
            FROM ecp_records er
            JOIN members m ON m.ecp_hash = er.ecp_hash
            LEFT JOIN club_affiliations ca ON ca.member_id = m.member_id AND ca.is_primary_club = TRUE
            LEFT JOIN clubs c ON c.club_id = ca.club_id
            WHERE er.ecp_active = TRUE
              AND er.verification_url LIKE %s
            LIMIT 1;
            """,
            (f"%/ecp_verify/{normalized_token}",),
        )
        if not row:
            return None
        valid_until = row["valid_until"]
        return {
            "member_id": row["member_id"],
            "display_name": row["display_name"],
            "club_name": row["club_name"],
            "status": row["status"],
            "valid_until": valid_until.isoformat() if hasattr(valid_until, "isoformat") else valid_until,
            "portrait_url": row["portrait_url"],
            "card_image_url": row["card_image_url"],
            "card_pdf_url": row["card_pdf_url"],
            "legal_document_url": row["legal_document_url"],
            "qr_payload_hash": row["qr_payload_hash"],
        }
