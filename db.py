import psycopg2
import psycopg2.extras
from config import secret_manager
from typing import List
from model import Club, Membership, Ecp, EcpRequest, Member # EcpRequest model might need photo_hash
import datetime # Pridaný import
class DatabaseManager:
    def __init__(self):
        self.connection_params = {
            "host": secret_manager.get_secret("db_host"),
            "port": secret_manager.get_secret("db_port"),
            "dbname": secret_manager.get_secret("db_name"),
            "user": secret_manager.get_secret("db_user"),
            "password": secret_manager.get_secret("db_password")
        }
        # Zabezpečí, že logovacia tabuľka existuje
        self._ensure_log_table_exists()

    def get_connection(self):
        return psycopg2.connect(**self.connection_params)

    # ----- Logovanie -----
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
        query = """
        INSERT INTO db_logs (action, table_name, user_name, details)
        VALUES (%s, %s, %s, %s);
        """
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (action, table_name, user, details))
                conn.commit()

    # ----- Low-level helper metódy -----
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

    # ----- Čítacie operácie (špecifické metódy) -----
    def fetch_clubs(self) -> List[Club]:
        query = """
        SELECT c.club_id, c.club_name, c.street, c.city, c.zip_code, c.country, c.email, c.phone,
               c.president_id, c.foundation_date, c.logo_url,
               COUNT(ca.member_id) AS member_count,
               COALESCE(m.first_name || ' ' || m.last_name, '') as president_name
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
                logo_url=row['logo_url']
            ))
        return clubs

    def fetch_club_by_id(self, club_id: int) -> Club:
        query = """
        SELECT c.club_id, c.club_name, c.street, c.city, c.zip_code, c.country, 
               c.email, c.phone, c.president_id, c.foundation_date, c.logo_url,
               (SELECT COUNT(ca.member_id) FROM club_affiliations ca WHERE ca.club_id = c.club_id) AS member_count,
               COALESCE(m.first_name || ' ' || m.last_name, '') as president_name
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
                logo_url=row['logo_url']
            )
        return None

    # Rozdelené metódy pre načítanie člena
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
            m.phone, m.email, m.ecp_hash, m.discounted_membership,
            (SELECT sub_ca.club_id FROM club_affiliations sub_ca
             WHERE sub_ca.member_id = m.member_id AND sub_ca.is_primary_club = TRUE LIMIT 1) as primary_club_id,
            EXISTS (
                SELECT 1 FROM membership_fees mf
                WHERE mf.member_id = m.member_id AND mf.year = %s
            ) as has_paid_current_year_fee
        FROM members m
        JOIN club_affiliations ca_assoc ON m.member_id = ca_assoc.member_id
        WHERE ca_assoc.club_id = %s
        ORDER BY m.last_name, m.first_name;
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
                has_paid_current_year_fee=row['has_paid_current_year_fee']
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
            m.phone, m.email, m.ecp_hash, m.discounted_membership,
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
                member_id=row['member_id'], has_paid_current_year_fee=row['has_paid_current_year_fee']
            ))
        return members

    # Rozdelené metódy pre klubové príslušnosti
    def fetch_memberships_by_member(self, member_id: int) -> List[Membership]:
        query = """
        SELECT c.club_id, ca.member_id, c.club_name, c.president_id, ca.is_primary_club
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
                is_primary_club=row['is_primary_club']
            ))
        return memberships

    def fetch_memberships_by_club(self, club_id: int) -> List[Membership]:
        query = """
        SELECT c.club_id, ca.member_id, c.club_name, c.president_id, ca.is_primary_club
        FROM clubs c
        JOIN club_affiliations ca ON ca.club_id = c.club_id
        WHERE ca.club_id = %s
        ORDER BY c.club_name;
        """
        rows = self._fetch_all(query, (club_id,))
        memberships = []
        for row in rows:
            memberships.append(Membership(
                club_id=row['club_id'],
                member_id=row['member_id'],
                club_name=row['club_name'],
                president_id=row['president_id'],
                is_primary_club=row['is_primary_club']
            ))
        return memberships

    def has_paid_fee(self, member_id: int, year: int) -> bool:
        query = "SELECT COUNT(*) as cnt FROM membership_fees WHERE member_id = %s AND year = %s;"
        record = self._fetch_one(query, (member_id, year))
        return record["cnt"] > 0 if record else False

    def fetch_ecp(self, hash_ecp: str) -> Ecp:
        query = """
        SELECT er.ecp_hash, er.gdpr_consent, er.notifications_enabled, er.photo_hash, er.ecp_active, er.check_hash, m.member_id
        FROM ecp_records er
        JOIN members m ON m.ecp_hash = er.ecp_hash
        WHERE er.ecp_hash = %s;
        """
        row = self._fetch_one(query, (hash_ecp,))
        if row:
            return Ecp(
                ecp_hash=row['ecp_hash'],
                gdpr_consent=row['gdpr_consent'],
                notifications_enabled=row['notifications_enabled'],
                photo_hash=row['photo_hash'],
                is_ecp_active=row['ecp_active'], 
                check_hash=row['check_hash'], 
                member_id=row['member_id']
            )
        return None

    def fetch_ecp_record_by_photo_hash(self, photo_hash: str) -> Ecp: # New method
        query = """
        SELECT er.ecp_hash, er.gdpr_consent, er.notifications_enabled, er.photo_hash, er.ecp_active, m.member_id
        FROM ecp_records er 
        LEFT JOIN members m ON er.member_id = m.member_id  -- Assuming ecp_records.member_id exists
        WHERE er.photo_hash = %s;
        """
        # LEFT JOIN members m ON er.member_id = m.member_id -- Assuming ecp_records has member_id
        # If ecp_records doesn't have member_id directly, this join needs adjustment or member_id comes from elsewhere.
        # For now, assuming ecp_records has member_id.
        row = self._fetch_one(query, (photo_hash,))
        if row:
            return Ecp(
                ecp_hash=row['ecp_hash'], # This might be NULL if not yet approved
                gdpr_consent=row['gdpr_consent'],
                notifications_enabled=row['notifications_enabled'],
                photo_hash=row['photo_hash'],
                is_ecp_active=row['ecp_active'], 
                check_hash=row.get('check_hash'), 
                member_id=row['member_id'] 
            )
        return None

    def fetch_ecp_requests(self) -> List[EcpRequest]:
        query = """
        SELECT r.request_id, r.member_id, r.status, r.request_date, er.photo_hash
        FROM ecp_requests r
        JOIN ecp_records er ON r.ecp_record_id = er.ecp_record_id
        WHERE r.status = 'pending'
        ORDER BY r.request_date DESC;
        """
        rows = self._fetch_all(query)
        requests_list = []
        for row in rows:
            requests_list.append(EcpRequest(
                # Načítame photo_hash z tabuľky ecp_records (aliased ako er)
                # a approved_ecp_hash z tabuľky ecp_requests (aliased ako r)
                request_id=row["request_id"],
                member_id=row["member_id"],
                photo_hash=row["photo_hash"], # Toto je hash fotky z ecp_records
                status=row["status"],
                request_date=row["request_date"]
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

    # ----- Zápisové operácie (špecifické metódy) -----
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
            president_id = %s,
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
            club.president_id,
            club.logo_url,
            club.club_id
        )
        self._execute(query, params)
        self._log_action("UPDATE", "clubs", f"Updated club ID {club.club_id} with data: {club.__dict__}")

    def insert_club(self, club: Club):
        query = """
        INSERT INTO clubs (club_name, street, city, zip_code, country, foundation_date, phone, email, president_id, logo_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            club.president_id,
            club.logo_url
        )
        new_id_row = self._fetch_one(query, params)
        if new_id_row:
            new_id = new_id_row[0]
            self._log_action("INSERT", "clubs", f"Inserted club with data: {club.__dict__}")
            return new_id
        return None

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
        self._log_action("UPDATE", "members", f"Updated member ID {member.member_id} with data: {member.__dict__}")

    def insert_member(self, member: Member):
        query = """
        INSERT INTO members (title_prefix, first_name, last_name, title_suffix, birth_date_encrypted, street, city, zip_code, country, phone, email, member_status, discounted_membership)
        VALUES (%s, %s, %s, %s, encode(encrypt(%s, %s, 'aes'::text), 'hex'), %s, %s, %s, %s, %s, %s, %s, %s)
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
            encryption_key_bytes, # Pass key as bytes
            member.street,
            member.city,
            member.zip_code,
            member.country,
            member.phone,
            member.email,
            member.status,
            member.discounted_membership
        )
        row = self._fetch_one(query, params)
        if row:
            new_id = row[0]
            self._log_action("INSERT", "members", f"Inserted member with data: {member.__dict__}")
            return new_id
        return None

    def delete_member(self, member_id: int):
        query = "DELETE FROM members WHERE member_id = %s;"
        self._execute(query, (member_id,))
        self._log_action("DELETE", "members", f"Deleted member with ID: {member_id}")

    def insert_memberships(self, member_id: int, club_id: int, primary_club: bool = False):
        query = """
        INSERT INTO club_affiliations (member_id, club_id, is_primary_club)
        VALUES (%s, %s, %s);
        """
        params = (member_id, club_id, primary_club)
        self._execute(query, params)
        self._log_action("INSERT", "club_affiliations", f"Inserted membership for member ID {member_id} in club ID {club_id}, primary: {primary_club}")

    def set_primary_memberships(self, member_id: int, club_id: int):
        query = "UPDATE club_affiliations SET is_primary_club = %s WHERE member_id = %s AND club_id = %s;"
        params = (True, member_id, club_id)
        self._execute(query, params)
        self._log_action("UPDATE", "club_affiliations", f"Set primary membership for member ID {member_id} in club ID {club_id}")

    def delete_memberships(self, member_id: int, club_id: int):
        query = "DELETE FROM club_affiliations WHERE member_id = %s AND club_id = %s;"
        params = (member_id, club_id)
        self._execute(query, params)
        self._log_action("DELETE", "club_affiliations", f"Deleted membership for member ID {member_id} in club ID {club_id}")

    def insert_fee_record(self, member_id: int, year: int, hash_ecp: str = None):
        query = "INSERT INTO membership_fees (member_id, ecp_hash, year) VALUES (%s, %s, %s);"
        params = (member_id, hash_ecp, year)
        self._execute(query, params)
        self._log_action("INSERT", "membership_fees", f"Inserted fee record for member ID {member_id} for year {year}")

    def insert_ecp(self, ecp: Ecp):
        query = """
        INSERT INTO ecp_records (ecp_hash, gdpr_consent, notifications_enabled, photo_hash, ecp_active, check_hash)
        VALUES (%s, %s, %s, %s, %s, %s);
        """
        params = (
            ecp.ecp_hash,
            ecp.gdpr_consent,
            ecp.notifications_enabled,
            ecp.photo_hash,
            ecp.is_ecp_active,
            ecp.check_hash
            # ecp.member_id -- Odstránené podľa požiadavky
        )
        self._execute(query, params)
        self._log_action("INSERT", "ecp_records", f"Inserted eCP record: {ecp.__dict__}")

    def update_ecp_active(self, current_ecp_hash: str, active: bool): # current_ecp_hash is the one to find the record
        query = "UPDATE ecp_records SET ecp_active = %s WHERE ecp_hash = %s;" 
        params = (active, current_ecp_hash)
        self._execute(query, params)
        self._log_action("UPDATE", "ecp_records", f"Updated eCP active status for hash {current_ecp_hash} to {active}")

    def update_ecp_record_on_approval(self, photo_hash: str, new_generated_ecp_hash: str):
        query = """
        UPDATE ecp_records
        SET ecp_hash = %s, ecp_active = TRUE 
        WHERE photo_hash = %s;
        """
        params = (new_generated_ecp_hash, photo_hash)
        self._execute(query, params)
        self._log_action("UPDATE", "ecp_records", f"Approved eCP record for photo_hash {photo_hash}, new ecp_hash: {new_generated_ecp_hash}")

    def update_member_ecp_hash(self, member_id: int, new_generated_ecp_hash: str):
        query = """
        UPDATE members
        SET ecp_hash = %s
        WHERE member_id = %s;
        """
        self._execute(query, (new_generated_ecp_hash, member_id))
        self._log_action("UPDATE", "members", f"Set ecp_hash for member_id {member_id} to {new_generated_ecp_hash}")
    
    def delete_ecp_record(self, ecp_hash: str):
        query = "DELETE FROM ecp_records WHERE ecp_hash = %s;"
        self._execute(query, (ecp_hash,))
        self._log_action("DELETE", "ecp_records", f"Deleted eCP record with hash {ecp_hash}")

    def insert_ecp_request(self, member_id: int, photo_hash: str):
        query = """
        INSERT INTO ecp_requests (member_id, photo_hash, status, request_date)
        VALUES (%s, %s, 'pending', CURRENT_DATE);
        """
        self._execute(query, (member_id, photo_hash))
        self._log_action("INSERT", "ecp_requests", f"Inserted eCP request for member ID {member_id} with photo_hash {photo_hash}")

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
        self._log_action("DELETE", "ecp_records", f"Deleted eCP record with photo_hash {photo_hash}")

# Globálna inštancia, ak je potrebná
db_manager: DatabaseManager = None
