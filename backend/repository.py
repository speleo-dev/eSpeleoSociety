from dataclasses import dataclass
import json
import re
import secrets

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
    def __init__(self, db_manager, upload_blob=None, check_hash_factory=None):
        self.db_manager = db_manager
        self.upload_blob = upload_blob
        self.check_hash_factory = check_hash_factory or (lambda: secrets.token_urlsafe(32))

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

    def fetch_member_portal_profile(self, member_id: int):
        row = self.db_manager._fetch_one(
            """
            SELECT
                m.member_id,
                m.member_status AS status,
                m.title_prefix,
                m.first_name,
                m.last_name,
                m.title_suffix,
                trim(concat_ws(' ', NULLIF(m.title_prefix, ''), m.first_name, m.last_name, NULLIF(m.title_suffix, ''))) AS display_name,
                m.email,
                m.phone,
                m.portrait_url,
                ca.club_id AS primary_club_id,
                c.club_name AS primary_club_name,
                er.ecp_active,
                er.valid_until AS ecp_valid_until,
                er.verification_url AS ecp_verification_url,
                er.card_image_url AS ecp_card_image_url,
                er.card_pdf_url AS ecp_card_pdf_url,
                er.wallet_status AS ecp_wallet_status,
                pending.request_id AS pending_ecp_request_id,
                pending.status AS pending_ecp_request_status,
                pending.request_date AS pending_ecp_request_date
            FROM members m
            LEFT JOIN club_affiliations ca ON ca.member_id = m.member_id AND ca.is_primary_club = TRUE
            LEFT JOIN clubs c ON c.club_id = ca.club_id
            LEFT JOIN ecp_records er ON er.ecp_hash = m.ecp_hash
            LEFT JOIN LATERAL (
                SELECT r.request_id, r.status, r.request_date
                FROM ecp_requests r
                WHERE r.member_id = m.member_id AND r.status = 'pending'
                ORDER BY r.request_date DESC, r.request_id DESC
                LIMIT 1
            ) pending ON TRUE
            WHERE m.member_id = %s
            LIMIT 1;
            """,
            (member_id,),
        )
        if not row:
            return None
        return {
            "member_id": row["member_id"],
            "status": row["status"],
            "title_prefix": row["title_prefix"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "title_suffix": row["title_suffix"],
            "display_name": row["display_name"],
            "email": row["email"],
            "phone": row["phone"],
            "portrait_url": row["portrait_url"],
            "primary_club_id": row["primary_club_id"],
            "primary_club_name": row["primary_club_name"],
            "ecp_active": row["ecp_active"],
            "ecp_valid_until": self._date_to_iso(row["ecp_valid_until"]),
            "ecp_verification_url": row["ecp_verification_url"],
            "ecp_card_image_url": row["ecp_card_image_url"],
            "ecp_card_pdf_url": row["ecp_card_pdf_url"],
            "ecp_wallet_status": row["ecp_wallet_status"],
            "pending_ecp_request_id": row["pending_ecp_request_id"],
            "pending_ecp_request_status": row["pending_ecp_request_status"],
            "pending_ecp_request_date": self._date_to_iso(row["pending_ecp_request_date"]),
        }

    def create_member_ecp_request(
        self,
        member_id: int,
        photo_bytes: bytes,
        content_type: str,
        gdpr_consent=True,
        notifications_enabled=True,
    ):
        if not self.upload_blob:
            raise RuntimeError("Photo upload backend is not configured.")
        extension = ".png" if content_type == "image/png" else ".jpg"
        photo_hash = secrets.token_hex(32)
        blob_name = f"ecp_request_photos/{photo_hash}{extension}"
        photo_url = self.upload_blob(blob_name, photo_bytes, content_type)
        ecp_hash = secrets.token_hex(32)
        ecp_row = self.db_manager._fetch_one(
            """
            INSERT INTO ecp_records (
                ecp_hash,
                gdpr_consent,
                notifications_enabled,
                photo_hash,
                ecp_active,
                check_hash
            )
            VALUES (%s, %s, %s, %s, FALSE, %s)
            RETURNING ecp_record_id;
            """,
            (
                ecp_hash,
                bool(gdpr_consent),
                bool(notifications_enabled),
                photo_hash,
                self.check_hash_factory(),
            ),
        )
        ecp_record_id = ecp_row["ecp_record_id"] if isinstance(ecp_row, dict) else ecp_row[0]
        request_row = self.db_manager._fetch_one(
            """
            INSERT INTO ecp_requests (member_id, ecp_record_id, status, request_date)
            VALUES (%s, %s, 'pending', CURRENT_DATE)
            RETURNING request_id, request_date;
            """,
            (member_id, ecp_record_id),
        )
        request_id = request_row["request_id"] if isinstance(request_row, dict) else request_row[0]
        request_date = request_row["request_date"] if isinstance(request_row, dict) else request_row[1]
        self.db_manager._log_action("INSERT", "ecp_requests", f"Inserted portal eCP request for member ID {member_id}")
        return {
            "request_id": request_id,
            "member_id": member_id,
            "ecp_record_id": ecp_record_id,
            "photo_hash": photo_hash,
            "photo_url": photo_url,
            "status": "pending",
            "request_date": self._date_to_iso(request_date),
        }

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

    def _date_to_iso(self, value):
        return value.isoformat() if hasattr(value, "isoformat") else value

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
