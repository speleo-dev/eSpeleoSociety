from dataclasses import dataclass
import json
import re

from backend.audit import AuditEvent
from backend.pagination import decode_id_cursor, encode_id_cursor


TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{12,256}(?:\.html)?$")


@dataclass(frozen=True)
class ClubRecord:
    club_id: int
    name: str
    street: str
    city: str
    zip_code: str
    country: str
    email: str
    phone: str
    president_id: int
    president_name: str
    foundation_date: object
    member_count: int
    logo_url: str | None = None
    webpage: str = ""
    president_name_text: str = ""


class DatabaseApiRepository:
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def fetch_clubs(self):
        return self.db_manager.fetch_clubs()

    def list_clubs(self, limit: int, cursor=None, filter_text: str = ""):
        last_id = decode_id_cursor(cursor)
        filter_value = self._like_filter(filter_text)
        filter_clause = ""
        params = [last_id]
        if filter_value:
            filter_clause = """
              AND (
                    COALESCE(c.club_name, '') ILIKE %s ESCAPE '\\'
                 OR COALESCE(c.city, '') ILIKE %s ESCAPE '\\'
                 OR COALESCE(c.email, '') ILIKE %s ESCAPE '\\'
                 OR COALESCE(c.phone, '') ILIKE %s ESCAPE '\\'
                 OR COALESCE(c.webpage, '') ILIKE %s ESCAPE '\\'
                 OR COALESCE(c.president_name_text, '') ILIKE %s ESCAPE '\\'
              )
            """
            params.extend([filter_value] * 6)
        params.append(limit + 1)
        rows = self.db_manager._fetch_all(
            f"""
            SELECT c.club_id, c.club_name, c.street, c.city, c.zip_code, c.country,
                   c.email, c.phone, c.webpage, c.president_id, c.president_name_text,
                   c.foundation_date, c.logo_url,
                   COUNT(ca.member_id) AS member_count,
                   COALESCE(NULLIF(c.president_name_text, ''), NULLIF(m.first_name || ' ' || m.last_name, ''), '') AS president_name
            FROM clubs c
            LEFT JOIN club_affiliations ca ON c.club_id = ca.club_id
            LEFT JOIN members m ON c.president_id = m.member_id
            WHERE c.club_id > %s
            {filter_clause}
            GROUP BY c.club_id, c.club_name, m.first_name, m.last_name
            ORDER BY c.club_id
            LIMIT %s;
            """,
            tuple(params),
        )
        page_rows = rows[:limit]
        clubs = [self._club_from_row(row) for row in page_rows]
        next_cursor = encode_id_cursor(clubs[-1].club_id) if len(rows) > limit and clubs else None
        return clubs, next_cursor

    def fetch_members(self, club_id: int):
        return self.db_manager.fetch_members(club_id)

    def record_api_audit_event(self, event: AuditEvent):
        details = json.dumps(
            {
                "request_id": event.request_id,
                "method": event.method,
                "route": event.route,
                "status_code": event.status_code,
                "roles": list(event.roles),
                "outcome": event.outcome,
                "error_code": event.error_code,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        self.db_manager._log_action(
            "API_REQUEST",
            "api_requests",
            details,
            user=event.subject,
        )

    def _like_filter(self, value: str) -> str:
        normalized = str(value or "").strip()[:100]
        if not normalized:
            return ""
        escaped = (
            normalized
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        return f"%{escaped}%"

    def _club_from_row(self, row):
        return ClubRecord(
            club_id=row["club_id"],
            name=row["club_name"],
            street=row["street"],
            city=row["city"],
            zip_code=row["zip_code"],
            country=row["country"],
            email=row["email"],
            phone=row["phone"],
            president_id=row["president_id"],
            president_name=row["president_name"],
            foundation_date=row["foundation_date"],
            member_count=row["member_count"],
            logo_url=row["logo_url"],
            webpage=row["webpage"],
            president_name_text=row["president_name_text"],
        )

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
