from dataclasses import dataclass
from datetime import date
import json
import re

from backend.audit import AuditEvent
from backend.pagination import decode_id_cursor, decode_keyset_cursor, encode_id_cursor, encode_keyset_cursor


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


@dataclass(frozen=True)
class MemberRecord:
    member_id: int
    status: str
    title_prefix: str
    first_name: str
    last_name: str
    title_suffix: str
    phone: str
    email: str
    ecp_hash: str | None
    primary_club_id: int | None
    is_president: bool
    has_paid_current_year_fee: bool = False
    is_directory_stub: bool = False


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

    def list_club_members(self, club_id: int, limit: int, cursor=None, filter_text: str = ""):
        cursor_values = self._member_cursor_values(cursor)
        filter_value = self._like_filter(filter_text)
        filter_clause = ""
        params = [
            date.today().year,
            club_id,
            cursor_values["role_rank"],
            cursor_values["last_name_sort"],
            cursor_values["first_name_sort"],
            cursor_values["member_id"],
        ]
        if filter_value:
            filter_clause = """
              AND (
                    concat_ws(' ', NULLIF(m.title_prefix, ''), m.first_name, m.last_name, NULLIF(m.title_suffix, '')) ILIKE %s ESCAPE '\\'
                 OR COALESCE(m.email, '') ILIKE %s ESCAPE '\\'
                 OR COALESCE(m.phone, '') ILIKE %s ESCAPE '\\'
                 OR COALESCE(m.member_status, '') ILIKE %s ESCAPE '\\'
                 OR COALESCE(ca_assoc.role, '') ILIKE %s ESCAPE '\\'
              )
            """
            params.extend([filter_value] * 5)
        params.append(limit + 1)
        rows = self.db_manager._fetch_all(
            f"""
            SELECT
                m.member_id,
                m.member_status,
                m.title_prefix,
                m.first_name,
                m.last_name,
                m.title_suffix,
                m.phone,
                m.email,
                m.ecp_hash,
                m.is_directory_stub,
                ca_assoc.role AS club_role,
                CASE WHEN ca_assoc.role = 'president' THEN 0 ELSE 1 END AS role_rank,
                lower(COALESCE(m.last_name, '')) AS last_name_sort,
                lower(COALESCE(m.first_name, '')) AS first_name_sort,
                (SELECT sub_ca.club_id
                 FROM club_affiliations sub_ca
                 WHERE sub_ca.member_id = m.member_id AND sub_ca.is_primary_club = TRUE
                 LIMIT 1) AS primary_club_id,
                EXISTS (
                    SELECT 1
                    FROM membership_fees mf
                    WHERE mf.member_id = m.member_id AND mf.year = %s
                ) AS has_paid_current_year_fee
            FROM members m
            JOIN club_affiliations ca_assoc ON m.member_id = ca_assoc.member_id
            WHERE ca_assoc.club_id = %s
              AND (
                    CASE WHEN ca_assoc.role = 'president' THEN 0 ELSE 1 END,
                    lower(COALESCE(m.last_name, '')),
                    lower(COALESCE(m.first_name, '')),
                    m.member_id
                  ) > (%s, %s, %s, %s)
            {filter_clause}
            ORDER BY role_rank, last_name_sort, first_name_sort, m.member_id
            LIMIT %s;
            """,
            tuple(params),
        )
        page_rows = rows[:limit]
        members = [self._member_from_row(row) for row in page_rows]
        next_cursor = self._member_cursor_from_row(page_rows[-1]) if len(rows) > limit and page_rows else None
        return members, next_cursor

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

    def _member_cursor_values(self, cursor: str | None) -> dict:
        values = decode_keyset_cursor(cursor)
        return {
            "role_rank": self._int_value(values.get("role_rank"), -1),
            "last_name_sort": str(values.get("last_name_sort") or ""),
            "first_name_sort": str(values.get("first_name_sort") or ""),
            "member_id": self._int_value(values.get("member_id"), 0),
        }

    def _member_cursor_from_row(self, row) -> str:
        return encode_keyset_cursor({
            "role_rank": self._int_value(row["role_rank"], 1),
            "last_name_sort": str(row["last_name_sort"] or ""),
            "first_name_sort": str(row["first_name_sort"] or ""),
            "member_id": self._int_value(row["member_id"], 0),
        })

    def _member_from_row(self, row):
        return MemberRecord(
            member_id=row["member_id"],
            status=row["member_status"],
            title_prefix=row["title_prefix"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            title_suffix=row["title_suffix"],
            phone=row["phone"],
            email=row["email"],
            ecp_hash=row["ecp_hash"],
            primary_club_id=row["primary_club_id"],
            is_president=row["club_role"] == "president",
            has_paid_current_year_fee=bool(row["has_paid_current_year_fee"]),
            is_directory_stub=bool(row["is_directory_stub"]),
        )

    def _int_value(self, value, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

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
