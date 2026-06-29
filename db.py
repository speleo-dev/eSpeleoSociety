import psycopg2
import psycopg2.extras
import re
from config import secret_manager
from typing import List
from model import Club, Membership, Ecp, EcpRequest, Member # EcpRequest model might need photo_hash
import datetime # Added import

SENSITIVE_LOG_KEYS = (
    "birth_date",
    "birth_date_encrypted",
    "check_hash",
    "city",
    "credentials_json",
    "crypt_key",
    "db_password",
    "ecp_hash",
    "email",
    "phone",
    "photo_hash",
    "smtp_password",
    "smtp_user",
    "street",
    "zip_code",
)


def sanitize_log_details(details: str) -> str:
    """Redact personal data and credential-like values before DB audit logging."""
    if details is None:
        return ""

    sanitized = str(details)
    for key in SENSITIVE_LOG_KEYS:
        quoted_pattern = re.compile(
            rf"(['\"]?{re.escape(key)}['\"]?\s*[:=]\s*)(['\"])(.*?)(\2)",
            re.IGNORECASE,
        )
        sanitized = quoted_pattern.sub(r"\1\2[REDACTED]\4", sanitized)

        unquoted_pattern = re.compile(
            rf"(['\"]?{re.escape(key)}['\"]?\s*[:=]\s*)([^,}}\]\n]+)",
            re.IGNORECASE,
        )
        sanitized = unquoted_pattern.sub(r"\1[REDACTED]", sanitized)

        prose_pattern = re.compile(
            rf"({re.escape(key)}\s+)([^\s,;]+)",
            re.IGNORECASE,
        )
        sanitized = prose_pattern.sub(r"\1[REDACTED]", sanitized)

    return sanitized


def _row_get(row, key, index):
    try:
        return row[key]
    except (KeyError, TypeError, IndexError):
        return row[index]


class DatabaseManager:
    def __init__(self):
        self.connection_params = {
            "host": secret_manager.get_secret("db_host"),
            "port": secret_manager.get_secret("db_port"),
            "dbname": secret_manager.get_secret("db_name"),
            "user": secret_manager.get_secret("db_user"),
            "password": secret_manager.get_secret("db_password")
        }
        # Ensures that the log table exists
        self._ensure_log_table_exists()

    def get_connection(self):
        return psycopg2.connect(**self.connection_params)

    # ----- Logging -----
    def _ensure_log_table_exists(self):
        query = """
        CREATE TABLE IF NOT EXISTS db_logs (
            log_id serial PRIMARY KEY,
            action VARCHAR(50),
            table_name VARCHAR(50),
            user_name VARCHAR(50),
            details TEXT,
            log_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                conn.commit()

    def _log_action(self, action: str, table_name: str, details: str, user: str = None):
        if user is None:
            user = self.connection_params.get("user", "unknown")
        details = sanitize_log_details(details)
        query = """
        INSERT INTO db_logs (action, table_name, user_name, details)
        VALUES (%s, %s, %s, %s);
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (action, table_name, user, details))
                conn.commit()

    # ----- Low-level helper methods -----
    def _fetch_all(self, query, params=None):
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def _fetch_one(self, query, params=None):
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(query, params)
                return cur.fetchone()

    def _execute(self, query, params=None):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()

    # ----- Read operations (specific methods) -----
    def fetch_clubs(self) -> List[Club]:
        query = """
        SELECT c.club_id, c.club_name, c.street, c.city, c.zip_code, c.country, c.email, c.phone, c.webpage,
               c.president_id, c.president_name_text, c.foundation_date, c.logo_url,
               COUNT(ca.member_id) AS member_count,
               COALESCE(NULLIF(m.first_name || ' ' || m.last_name, ''), NULLIF(c.president_name_text, ''), '') as president_name
        FROM clubs c
        LEFT JOIN club_affiliations ca ON c.club_id = ca.club_id
        LEFT JOIN members m ON c.president_id = m.member_id
        GROUP BY c.club_id, c.club_name, m.first_name, m.last_name
        ORDER BY c.club_name;
        """
        rows = self._fetch_all(query)
        clubs = []
        for row in rows:
            clubs.append(Club(
                club_id=row['club_id'],
                name=row['club_name'],
                street=row['street'],
                city=row['city'],
                zip_code=row['zip_code'],
                country=row['country'],
                email=row['email'],
                phone=row['phone'],
                president_id=row['president_id'],
                president_name=row['president_name'],
                foundation_date=row['foundation_date'],
                member_count=row['member_count'],
                logo_url=row['logo_url'],
                webpage=row['webpage'],
                president_name_text=row['president_name_text'],
            ))
        return clubs

    def fetch_club_by_id(self, club_id: int) -> Club:
        query = """
        SELECT c.club_id, c.club_name, c.street, c.city, c.zip_code, c.country, 
               c.email, c.phone, c.webpage, c.president_id, c.president_name_text, c.foundation_date, c.logo_url,
               (SELECT COUNT(ca.member_id) FROM club_affiliations ca WHERE ca.club_id = c.club_id) AS member_count,
               COALESCE(NULLIF(m.first_name || ' ' || m.last_name, ''), NULLIF(c.president_name_text, ''), '') as president_name
        FROM clubs c
        LEFT JOIN members m ON c.president_id = m.member_id
        WHERE c.club_id = %s;
        """
        row = self._fetch_one(query, (club_id,))
        if row:
            return Club(
                club_id=row['club_id'],
                name=row['club_name'],
                street=row['street'],
                city=row['city'],
                zip_code=row['zip_code'],
                country=row['country'],
                email=row['email'],
                phone=row['phone'],
                president_id=row['president_id'],
                president_name=row['president_name'],
                foundation_date=row['foundation_date'],
                member_count=row['member_count'],
                logo_url=row['logo_url'],
                webpage=row['webpage'],
                president_name_text=row['president_name_text'],
            )
        return None

    # Separated methods for loading a member
    def fetch_member_by_id(self, member_id: int) -> Member:
        query = """
        SELECT m.member_id, m.member_status, m.title_prefix, m.first_name, m.last_name, m.title_suffix,
               m.birth_date_encrypted, m.street, m.city, m.zip_code, m.country,
               m.phone, m.email, m.ecp_hash,
               m.discounted_membership, ca.club_id as primary_club_id
        FROM members m
        JOIN club_affiliations ca ON ca.member_id = m.member_id
        WHERE m.member_id = %s AND ca.is_primary_club = TRUE
        ORDER BY m.last_name, m.first_name;
        """
        row = self._fetch_one(query, (member_id,))
        if row:
            return Member(
                status=row['member_status'],
                title_prefix=row['title_prefix'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                title_suffix=row['title_suffix'],
                encrypted_birth_date=row['birth_date_encrypted'],
                street=row['street'],
                city=row['city'],
                zip_code=row['zip_code'],
                country=row['country'],
                phone=row['phone'],
                email=row['email'],
                ecp_hash=row['ecp_hash'],
                discounted_membership=row['discounted_membership'],
                primary_club_id=row['primary_club_id'],
                member_id=row['member_id']
            )
        return None
    
    def fetch_member_by_hash(self, hash_ecp: str) -> Member:
        query = """
        SELECT m.member_id, m.member_status, m.title_prefix, m.first_name, m.last_name, m.title_suffix,
               m.birth_date_encrypted, m.street, m.city, m.zip_code, m.country,
               m.phone, m.email, m.ecp_hash,
               m.discounted_membership, ca.club_id as primary_club_id
        FROM members m
        JOIN club_affiliations ca ON ca.member_id = m.member_id
        WHERE m.ecp_hash = %s AND ca.is_primary_club = TRUE
        ORDER BY m.last_name, m.first_name;
        """
        row = self._fetch_one(query, (hash_ecp,))
        if row:
            return Member(
                status=row['member_status'],
                title_prefix=row['title_prefix'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                title_suffix=row['title_suffix'],
                encrypted_birth_date=row['birth_date_encrypted'],
                street=row['street'],
                city=row['city'],
                zip_code=row['zip_code'],
                country=row['country'],
                phone=row['phone'],
                email=row['email'],
                ecp_hash=row['ecp_hash'],
                discounted_membership=row['discounted_membership'],
                primary_club_id=row['primary_club_id'],
                member_id=row['member_id']
            )
        return None

    def fetch_members(self, club_id: int) -> List[Member]:
        current_year = datetime.datetime.now().year
        query = """
        SELECT
            m.member_id, m.member_status, m.title_prefix, m.first_name, m.last_name, m.title_suffix,
            m.birth_date_encrypted, m.street, m.city, m.zip_code, m.country,
            m.phone, m.email, m.ecp_hash, m.discounted_membership, m.is_directory_stub,
            ca_assoc.role AS club_role,
            (SELECT sub_ca.club_id FROM club_affiliations sub_ca
             WHERE sub_ca.member_id = m.member_id AND sub_ca.is_primary_club = TRUE LIMIT 1) as primary_club_id,
            EXISTS (
                SELECT 1 FROM membership_fees mf
                WHERE mf.member_id = m.member_id AND mf.year = %s
            ) as has_paid_current_year_fee
        FROM members m
        JOIN club_affiliations ca_assoc ON m.member_id = ca_assoc.member_id
        WHERE ca_assoc.club_id = %s
        ORDER BY CASE WHEN ca_assoc.role = 'president' THEN 0 ELSE 1 END, m.last_name, m.first_name;
        """
        rows = self._fetch_all(query, (current_year, club_id,))
        members = []
        for row in rows:
            members.append(Member(
                status=row['member_status'],
                title_prefix=row['title_prefix'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                title_suffix=row['title_suffix'],
                encrypted_birth_date=row['birth_date_encrypted'],
                street=row['street'],
                city=row['city'],
                zip_code=row['zip_code'],
                country=row['country'],
                phone=row['phone'],
                email=row['email'],
                ecp_hash=row['ecp_hash'],
                discounted_membership=row['discounted_membership'],
                primary_club_id=row['primary_club_id'],
                member_id=row['member_id'],
                has_paid_current_year_fee=row['has_paid_current_year_fee'],
                is_president=row['club_role'] == 'president',
                is_directory_stub=row['is_directory_stub'],
           ))
        return members

    def search_members_globally(self, search_terms: List[str]) -> List[Member]:
        current_year = datetime.datetime.now().year
        if not search_terms:
            return []
        base_query = """
        SELECT
            m.member_id, m.member_status, m.title_prefix, m.first_name, m.last_name, m.title_suffix,
            m.birth_date_encrypted, m.street, m.city, m.zip_code, m.country,
            m.phone, m.email, m.ecp_hash, m.discounted_membership, m.is_directory_stub,
            (SELECT sub_ca.club_id FROM club_affiliations sub_ca
             WHERE sub_ca.member_id = m.member_id AND sub_ca.is_primary_club = TRUE LIMIT 1) as primary_club_id,
            EXISTS (
                SELECT 1 FROM membership_fees mf
                WHERE mf.member_id = m.member_id AND mf.year = %s
            ) as has_paid_current_year_fee
        FROM members m
        """
        
        # Dynamické zostavenie WHERE klauzuly
        where_conditions = []
        params = [current_year]

        for term in search_terms:
            like_term = f"%{term}%"
            where_conditions.append("(m.first_name ILIKE %s OR m.last_name ILIKE %s)")
            params.extend([like_term, like_term])
        
        full_query = base_query + " WHERE " + " AND ".join(where_conditions) + " ORDER BY m.last_name, m.first_name;"
        rows = self._fetch_all(full_query, tuple(params))
        members = []
        for row in rows:
            members.append(Member(
                status=row['member_status'],
                title_prefix=row['title_prefix'],
                first_name=row['first_name'],
                last_name=row['last_name'],
                title_suffix=row['title_suffix'],
                encrypted_birth_date=row['birth_date_encrypted'],
                street=row['street'],
                city=row['city'],
                zip_code=row['zip_code'],
                country=row['country'],
                phone=row['phone'],
                email=row['email'],
                ecp_hash=row['ecp_hash'],
                discounted_membership=row['discounted_membership'],
                primary_club_id=row['primary_club_id'],
                member_id=row['member_id'], has_paid_current_year_fee=row['has_paid_current_year_fee'],
                is_directory_stub=row['is_directory_stub'],
            ))
        return members

    # Separated methods for club affiliations
    def fetch_memberships_by_member(self, member_id: int) -> List[Membership]:
        query = """
        SELECT c.club_id, ca.member_id, c.club_name, c.president_id, ca.is_primary_club, ca.role
        FROM club_affiliations ca
        JOIN clubs c ON c.club_id = ca.club_id
        WHERE ca.member_id = %s
        ORDER BY c.club_name;
        """
        rows = self._fetch_all(query, (member_id,))
        memberships = []
        for row in rows:
            memberships.append(Membership(
                club_id=row['club_id'],
                member_id=row['member_id'],
                club_name=row['club_name'],
                president_id=row['president_id'],
                is_primary_club=row['is_primary_club'],
                role=row['role'],
            ))
        return memberships

    def fetch_memberships_by_club(self, club_id: int) -> List[Membership]:
        query = """
        SELECT c.club_id, ca.member_id, c.club_name, c.president_id, ca.is_primary_club, ca.role
        FROM clubs c
        JOIN club_affiliations ca ON ca.club_id = c.club_id
        WHERE ca.club_id = %s
        ORDER BY CASE WHEN ca.role = 'president' THEN 0 ELSE 1 END, c.club_name;
        """
        rows = self._fetch_all(query, (club_id,))
        memberships = []
        for row in rows:
            memberships.append(Membership(
                club_id=row['club_id'],
                member_id=row['member_id'],
                club_name=row['club_name'],
                president_id=row['president_id'],
                is_primary_club=row['is_primary_club'],
                role=row['role'],
            ))
        return memberships

    def has_paid_fee(self, member_id: int, year: int) -> bool:
        query = "SELECT COUNT(*) as cnt FROM membership_fees WHERE member_id = %s AND year = %s;"
        record = self._fetch_one(query, (member_id, year))
        return record["cnt"] > 0 if record else False

    def _row_get(self, row, key, default=None):
        try:
            return row[key]
        except (KeyError, IndexError):
            return default

    def _build_ecp_from_row(self, row, member_id=None) -> Ecp:
        return Ecp(
            ecp_hash=row['ecp_hash'],
            gdpr_consent=row['gdpr_consent'],
            notifications_enabled=row['notifications_enabled'],
            photo_hash=row['photo_hash'],
            is_ecp_active=row['ecp_active'],
            check_hash=row['check_hash'],
            member_id=self._row_get(row, 'member_id', member_id),
            ecp_id=row['ecp_record_id'],
            qr_url=self._row_get(row, 'qr_url'),
            qr_key_id=self._row_get(row, 'qr_key_id'),
            qr_payload_hash=self._row_get(row, 'qr_payload_hash'),
            issued_at=self._row_get(row, 'issued_at'),
            valid_until=self._row_get(row, 'valid_until'),
            wallet_status=self._row_get(row, 'wallet_status'),
            wallet_object_id=self._row_get(row, 'wallet_object_id'),
            wallet_last_error=self._row_get(row, 'wallet_last_error'),
        )

    def fetch_ecp(self, hash_ecp: str) -> Ecp:
        query = """
        SELECT er.ecp_record_id, er.ecp_hash, er.gdpr_consent, er.notifications_enabled,
               er.photo_hash, er.ecp_active, er.check_hash, er.qr_url, er.qr_key_id,
               er.qr_payload_hash, er.issued_at, er.valid_until, er.wallet_status,
               er.wallet_object_id, er.wallet_last_error, m.member_id
        FROM ecp_records er
        JOIN members m ON m.ecp_hash = er.ecp_hash
        WHERE er.ecp_hash = %s;
        """
        row = self._fetch_one(query, (hash_ecp,))
        if row:
            return self._build_ecp_from_row(row)
        return None

    def fetch_ecp_record_by_photo_hash(self, photo_hash: str) -> Ecp: # New method
        query = """
        SELECT er.ecp_record_id, er.ecp_hash, er.gdpr_consent, er.notifications_enabled,
               er.photo_hash, er.ecp_active, er.check_hash, er.qr_url, er.qr_key_id,
               er.qr_payload_hash, er.issued_at, er.valid_until, er.wallet_status,
               er.wallet_object_id, er.wallet_last_error
        FROM ecp_records er
        WHERE er.photo_hash = %s;
        """
        row = self._fetch_one(query, (photo_hash,))
        if row:
            return self._build_ecp_from_row(row)
        return None

    def fetch_ecp_record_by_id(self, ecp_record_id: int) -> Ecp:
        query = """
        SELECT er.ecp_record_id, er.ecp_hash, er.gdpr_consent, er.notifications_enabled,
               er.photo_hash, er.ecp_active, er.check_hash, er.qr_url, er.qr_key_id,
               er.qr_payload_hash, er.issued_at, er.valid_until, er.wallet_status,
               er.wallet_object_id, er.wallet_last_error
        FROM ecp_records er
        WHERE er.ecp_record_id = %s;
        """
        row = self._fetch_one(query, (ecp_record_id,))
        if row:
            return self._build_ecp_from_row(row)
        return None

    def fetch_ecp_requests(self) -> List[EcpRequest]:
        query = """
        SELECT r.request_id, r.member_id, r.status, r.request_date, r.ecp_record_id, er.photo_hash
        FROM ecp_requests r
        LEFT JOIN ecp_records er ON r.ecp_record_id = er.ecp_record_id
        WHERE r.status = 'pending'
        ORDER BY r.request_date DESC;
        """
        rows = self._fetch_all(query)
        requests_list = []
        for row in rows:
            requests_list.append(EcpRequest(
                request_id=row["request_id"],
                member_id=row["member_id"],
                photo_hash=row["photo_hash"],
                status=row["status"],
                request_date=row["request_date"],
                ecp_record_id=row["ecp_record_id"],
            ))
        return requests_list
    
    def fetch_notifications(self):
        query = "SELECT notification_id, created_at, text, valid_from, valid_to, status FROM notifications ORDER BY created_at DESC;"
        return self._fetch_all(query)

    def delete_notification(self, notification_id: int):
        query = "DELETE FROM notifications WHERE notification_id = %s;"
        params = (notification_id,)
        self._execute(query, params)
        self._log_action("DELETE", "notifications", f"Deleted notification with ID: {notification_id}")

    # ----- Write operations (specific methods) -----
    def update_club(self, club: Club):
        query = """
        UPDATE clubs
        SET club_name = %s,
            street = %s,
            city = %s,
            zip_code = %s,
            country = %s,
            foundation_date = %s,
            phone = %s,
            email = %s,
            webpage = %s,
            president_id = %s,
            president_name_text = %s,
            logo_url = %s
        WHERE club_id = %s;
        """
        params = (
            club.name,
            club.street,
            club.city,
            club.zip_code,
            club.country,
            club.foundation_date,
            club.phone,
            club.email,
            club.webpage,
            club.president_id,
            club.president_name_text,
            club.logo_url,
            club.club_id
        )
        self._execute(query, params)
        self._log_action("UPDATE", "clubs", f"Updated club ID {club.club_id}")

    def insert_club(self, club: Club):
        query = """
        INSERT INTO clubs (
            club_name, street, city, zip_code, country, foundation_date,
            phone, email, webpage, president_id, president_name_text, logo_url
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING club_id;
        """
        params = (
            club.name,
            club.street,
            club.city,
            club.zip_code,
            club.country,
            club.foundation_date,
            club.phone,
            club.email,
            club.webpage,
            club.president_id,
            club.president_name_text,
            club.logo_url
        )
        new_id_row = self._fetch_one(query, params)
        if new_id_row:
            new_id = new_id_row[0]
            self._log_action("INSERT", "clubs", f"Inserted club ID {new_id}")
            return new_id
        return None

    def upsert_club_directory_entry(
        self,
        club_name: str,
        president_name_text: str,
        president_title_prefix: str,
        president_first_name: str,
        president_last_name: str,
        president_title_suffix: str,
        phone: str,
        email: str,
        webpage: str,
        country: str = "SK",
    ):
        update_query = """
        UPDATE clubs
        SET president_name_text = %s,
            phone = %s,
            email = %s,
            webpage = %s,
            country = COALESCE(NULLIF(country, ''), %s)
        WHERE lower(trim(club_name)) = lower(trim(%s))
        RETURNING club_id;
        """
        params = (president_name_text, phone, email, webpage, country, club_name)
        updated_row = self._fetch_one(update_query, params)
        if updated_row:
            club_id = updated_row[0]
            self._log_action("UPDATE", "clubs", f"Updated SSS directory club ID {club_id}")
        else:
            insert_query = """
            INSERT INTO clubs (club_name, president_name_text, phone, email, webpage, country)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING club_id;
            """
            insert_params = (club_name, president_name_text, phone, email, webpage, country)
            inserted_row = self._fetch_one(insert_query, insert_params)
            if not inserted_row:
                return None
            club_id = inserted_row[0]
            self._log_action("INSERT", "clubs", f"Inserted SSS directory club ID {club_id}")

        if president_name_text:
            member_id = self.upsert_directory_president_member(
                club_id=club_id,
                title_prefix=president_title_prefix,
                first_name=president_first_name,
                last_name=president_last_name,
                title_suffix=president_title_suffix,
                phone=phone,
                email=email,
                country=country,
            )
            if member_id:
                self.insert_memberships(
                    member_id=member_id,
                    club_id=club_id,
                    primary_club=True,
                    role="president",
                )
                self._execute(
                    "UPDATE clubs SET president_id = %s WHERE club_id = %s;",
                    (member_id, club_id),
                )
                self._log_action("UPDATE", "clubs", f"Linked SSS directory president member ID {member_id} to club ID {club_id}")
        return club_id

    def upsert_directory_president_member(
        self,
        club_id: int,
        title_prefix: str,
        first_name: str,
        last_name: str,
        title_suffix: str,
        phone: str,
        email: str,
        country: str = "SK",
    ):
        existing_president_query = """
        SELECT m.member_id, m.is_directory_stub
        FROM clubs c
        JOIN members m ON m.member_id = c.president_id
        WHERE c.club_id = %s
        LIMIT 1;
        """
        existing_president = self._fetch_one(existing_president_query, (club_id,))
        if existing_president:
            member_id = _row_get(existing_president, "member_id", 0)
            if _row_get(existing_president, "is_directory_stub", 1):
                self._update_directory_stub_member(
                    member_id,
                    title_prefix,
                    first_name,
                    last_name,
                    title_suffix,
                    phone,
                    email,
                    country,
                )
            return member_id

        same_name_query = """
        SELECT m.member_id, m.is_directory_stub
        FROM members m
        JOIN club_affiliations ca ON ca.member_id = m.member_id
        WHERE ca.club_id = %s
          AND lower(trim(m.first_name)) = lower(trim(%s))
          AND lower(trim(m.last_name)) = lower(trim(%s))
        ORDER BY m.is_directory_stub DESC, m.member_id
        LIMIT 1;
        """
        same_name = self._fetch_one(same_name_query, (club_id, first_name, last_name))
        if same_name:
            member_id = _row_get(same_name, "member_id", 0)
            if _row_get(same_name, "is_directory_stub", 1):
                self._update_directory_stub_member(
                    member_id,
                    title_prefix,
                    first_name,
                    last_name,
                    title_suffix,
                    phone,
                    email,
                    country,
                )
            return member_id

        insert_query = """
        INSERT INTO members (
            title_prefix, first_name, last_name, title_suffix, birth_date_encrypted,
            street, city, zip_code, country, phone, email, member_status,
            discounted_membership, is_directory_stub
        )
        VALUES (%s, %s, %s, %s, NULL, '', '', '', %s, %s, %s, 'active', false, true)
        RETURNING member_id;
        """
        inserted = self._fetch_one(
            insert_query,
            (title_prefix, first_name, last_name, title_suffix, country, phone, email),
        )
        if inserted:
            member_id = inserted[0]
            self._log_action("INSERT", "members", f"Inserted SSS directory president member ID {member_id}")
            return member_id
        return None

    def _update_directory_stub_member(
        self,
        member_id: int,
        title_prefix: str,
        first_name: str,
        last_name: str,
        title_suffix: str,
        phone: str,
        email: str,
        country: str,
    ):
        query = """
        UPDATE members
        SET title_prefix = %s,
            first_name = %s,
            last_name = %s,
            title_suffix = %s,
            country = COALESCE(NULLIF(country, ''), %s),
            phone = %s,
            email = %s
        WHERE member_id = %s
          AND is_directory_stub IS TRUE;
        """
        self._execute(
            query,
            (title_prefix, first_name, last_name, title_suffix, country, phone, email, member_id),
        )
        self._log_action("UPDATE", "members", f"Updated SSS directory president member ID {member_id}")

    def update_member(self, member: Member):
        query = """
        UPDATE members
        SET title_prefix = %s,
            first_name = %s,
            last_name = %s,
            title_suffix = %s,
            street = %s,
            city = %s,
            zip_code = %s,
            country = %s,
            phone = %s,
            email = %s,
            member_status = %s,
            discounted_membership = %s
        WHERE member_id = %s;
        """
        params = (
            member.title_prefix,
            member.first_name,
            member.last_name,
            member.title_suffix,
            member.street,
            member.city,
            member.zip_code,
            member.country,
            member.phone,
            member.email,
            member.status,
            member.discounted_membership,
            member.member_id
        )
        self._execute(query, params)
        self._log_action("UPDATE", "members", f"Updated member ID {member.member_id}")

    def insert_member(self, member: Member):
        query = """
        INSERT INTO members (
            title_prefix, first_name, last_name, title_suffix, birth_date_encrypted,
            street, city, zip_code, country, phone, email, member_status,
            discounted_membership, is_directory_stub
        )
        VALUES (
            %s, %s, %s, %s,
            CASE WHEN %s IS NULL THEN NULL ELSE encode(encrypt(%s, %s, 'aes'::text), 'hex') END,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING member_id;
        """
        # Convert birth_date to UTF-8 encoded bytes of its ISO format string, or None
        birth_date_payload = None
        if member.birth_date:
            # Ensure member.birth_date is a date object, then format and encode
            if isinstance(member.birth_date, (datetime.date, datetime.datetime)):
                birth_date_payload = member.birth_date.isoformat().encode('utf-8')
            else: # Handle cases where it might already be a string (though model suggests date)
                birth_date_payload = str(member.birth_date).encode('utf-8')

        # Ensure encryption key is UTF-8 encoded bytes
        encryption_key_bytes = secret_manager.get_secret("crypt_key").encode('utf-8')

        params = (
            member.title_prefix,
            member.first_name,
            member.last_name,
            member.title_suffix,
            birth_date_payload,  # Pass as bytes or None
            birth_date_payload,  # Pass as bytes or None for encryption when present
            encryption_key_bytes, # Pass key as bytes
            member.street,
            member.city,
            member.zip_code,
            member.country,
            member.phone,
            member.email,
            member.status,
            member.discounted_membership,
            member.is_directory_stub,
        )
        row = self._fetch_one(query, params)
        if row:
            new_id = row[0]
            self._log_action("INSERT", "members", f"Inserted member ID {new_id}")
            return new_id
        return None

    def delete_member(self, member_id: int):
        query = "DELETE FROM members WHERE member_id = %s;"
        self._execute(query, (member_id,))
        self._log_action("DELETE", "members", f"Deleted member with ID: {member_id}")

    def insert_memberships(
        self,
        member_id: int,
        club_id: int,
        primary_club: bool = False,
        role: str = "member",
    ):
        query = """
        INSERT INTO club_affiliations (member_id, club_id, is_primary_club, role)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (member_id, club_id)
        DO UPDATE SET
            is_primary_club = club_affiliations.is_primary_club OR EXCLUDED.is_primary_club,
            role = CASE
                WHEN club_affiliations.role = 'president' OR EXCLUDED.role = 'president'
                    THEN 'president'
                ELSE EXCLUDED.role
            END;
        """
        params = (member_id, club_id, primary_club, role)
        self._execute(query, params)
        self._log_action("INSERT", "club_affiliations", f"Inserted membership for member ID {member_id} in club ID {club_id}, primary: {primary_club}, role: {role}")

    def set_primary_memberships(self, member_id: int, club_id: int):
        query = """
        UPDATE club_affiliations
        SET is_primary_club = CASE WHEN club_id = %s THEN TRUE ELSE FALSE END
        WHERE member_id = %s;
        """
        params = (club_id, member_id)
        self._execute(query, params)
        self._log_action("UPDATE", "club_affiliations", f"Set primary membership for member ID {member_id} in club ID {club_id}")

    def delete_memberships(self, member_id: int, club_id: int):
        query = "DELETE FROM club_affiliations WHERE member_id = %s AND club_id = %s;"
        params = (member_id, club_id)
        self._execute(query, params)
        self._log_action("DELETE", "club_affiliations", f"Deleted membership for member ID {member_id} in club ID {club_id}")

    def insert_fee_record(self, member_id: int, year: int, hash_ecp: str = None, fee_type: str = "standard"):
        query = """
        INSERT INTO membership_fees (member_id, ecp_hash, year, fee_type)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (member_id, year, fee_type) DO NOTHING;
        """
        params = (member_id, hash_ecp, year, fee_type)
        self._execute(query, params)
        self._log_action("INSERT", "membership_fees", f"Inserted fee record for member ID {member_id} for year {year}")

    def insert_ecp(self, ecp: Ecp):
        query = """
        INSERT INTO ecp_records (ecp_hash, gdpr_consent, notifications_enabled, photo_hash, ecp_active, check_hash)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING ecp_record_id;
        """
        params = (
            ecp.ecp_hash,
            ecp.gdpr_consent,
            ecp.notifications_enabled,
            ecp.photo_hash,
            ecp.is_ecp_active,
            ecp.check_hash
            # ecp.member_id -- Removed as per requirement
        )
        row = self._fetch_one(query, params)
        if row:
            ecp.ecp_id = row[0]
            self._log_action("INSERT", "ecp_records", f"Inserted eCP record for member ID {ecp.member_id}")
            return ecp.ecp_id
        return None

    def update_ecp_active(self, current_ecp_hash: str, active: bool): # current_ecp_hash is the one to find the record
        query = "UPDATE ecp_records SET ecp_active = %s WHERE ecp_hash = %s;" 
        params = (active, current_ecp_hash)
        self._execute(query, params)
        self._log_action("UPDATE", "ecp_records", f"Updated eCP active status to {active}")

    def update_ecp_record_on_approval(self, ecp_record_id: int, new_generated_ecp_hash: str):
        query = """
        UPDATE ecp_records
        SET ecp_hash = %s, ecp_active = TRUE 
        WHERE ecp_record_id = %s;
        """
        params = (new_generated_ecp_hash, ecp_record_id)
        self._execute(query, params)
        self._log_action("UPDATE", "ecp_records", "Approved eCP record")

    def update_ecp_record_issuance(
        self,
        ecp_record_id: int,
        ecp_hash: str,
        qr_url: str,
        qr_key_id: str,
        qr_payload: dict,
        qr_payload_hash: str,
        issued_at,
        valid_until,
        wallet_status: str = "not_issued",
    ):
        query = """
        UPDATE ecp_records
        SET ecp_hash = %s,
            ecp_active = TRUE,
            qr_url = %s,
            qr_key_id = %s,
            qr_payload = %s,
            qr_payload_hash = %s,
            issued_at = %s,
            valid_until = %s,
            wallet_status = %s,
            wallet_last_error = NULL
        WHERE ecp_record_id = %s;
        """
        params = (
            ecp_hash,
            qr_url,
            qr_key_id,
            psycopg2.extras.Json(qr_payload),
            qr_payload_hash,
            issued_at,
            valid_until,
            wallet_status,
            ecp_record_id,
        )
        self._execute(query, params)
        self._log_action("UPDATE", "ecp_records", "Updated eCP issuance metadata")

    def update_member_ecp_hash(self, member_id: int, new_generated_ecp_hash: str):
        query = """
        UPDATE members
        SET ecp_hash = %s
        WHERE member_id = %s;
        """
        self._execute(query, (new_generated_ecp_hash, member_id))
        self._log_action("UPDATE", "members", f"Set eCP hash for member ID {member_id}")
    
    def delete_ecp_record(self, ecp_hash: str):
        query = "DELETE FROM ecp_records WHERE ecp_hash = %s;"
        self._execute(query, (ecp_hash,))
        self._log_action("DELETE", "ecp_records", "Deleted eCP record")

    def insert_ecp_request(self, member_id: int, ecp_record_id: int):
        query = """
        INSERT INTO ecp_requests (member_id, ecp_record_id, status, request_date)
        VALUES (%s, %s, 'pending', CURRENT_DATE);
        """
        self._execute(query, (member_id, ecp_record_id))
        self._log_action("INSERT", "ecp_requests", f"Inserted eCP request for member ID {member_id}")

    def update_ecp_request_status(self, request_id: int, new_status: str):
        query = "UPDATE ecp_requests SET status = %s WHERE request_id = %s;"
        params = (new_status, request_id)
        self._execute(query, params)
        log_details = f"Updated eCP request ID {request_id} to status {new_status}"
        self._log_action("UPDATE", "ecp_requests", log_details)

    def insert_notification(self, text: str, valid_from, valid_to):
        query = """
        INSERT INTO notifications (created_at, text, valid_from, valid_to, status)
        VALUES (NOW(), %s, %s, %s, %s);
        """
        params = (text, valid_from, valid_to, "pending")
        self._execute(query, params)
        self._log_action("INSERT", "notifications", f"Inserted notification: {text}")

    def delete_ecp_record_by_photo_hash(self, photo_hash: str):
        query = "DELETE FROM ecp_records WHERE photo_hash = %s;"
        self._execute(query, (photo_hash,))
        self._log_action("DELETE", "ecp_records", "Deleted eCP record by photo reference")

    def delete_ecp_record_by_id(self, ecp_record_id: int):
        query = "DELETE FROM ecp_records WHERE ecp_record_id = %s;"
        self._execute(query, (ecp_record_id,))
        self._log_action("DELETE", "ecp_records", "Deleted eCP record")

# Global instance, if needed
db_manager: DatabaseManager = None
