import os
from pathlib import Path
import unittest


SCHEMA_PATH = Path("database/schema.sql")


class DatabaseSchemaSqlTest(unittest.TestCase):
    def test_schema_sql_is_restorable_not_raw_adminer_dump(self):
        schema = SCHEMA_PATH.read_text(encoding="utf-8")

        self.assertIn("CREATE EXTENSION IF NOT EXISTS pgcrypto", schema)
        self.assertNotIn("CREATE DATABASE", schema)
        self.assertNotIn("\\connect", schema)
        self.assertNotIn("LANGUAGE c AS ''", schema)

    def test_schema_sql_contains_author_tables_and_ecp_request_fk(self):
        schema = SCHEMA_PATH.read_text(encoding="utf-8")

        for table_name in (
            "members",
            "clubs",
            "club_affiliations",
            "membership_fees",
            "ecp_records",
            "ecp_requests",
            "member_certificates",
            "notifications",
            "ess_config",
            "db_logs",
        ):
            self.assertIn(f"CREATE TABLE IF NOT EXISTS public.{table_name}", schema)

        self.assertIn("ecp_record_id integer", schema)
        self.assertIn(
            "FOREIGN KEY (ecp_record_id) REFERENCES public.ecp_records(ecp_record_id)",
            schema,
        )
        ecp_requests_definition = schema.split(
            "CREATE TABLE IF NOT EXISTS public.ecp_requests",
            1,
        )[1].split(");", 1)[0]
        self.assertNotIn("photo_hash", ecp_requests_definition)

    def test_schema_sql_contains_ecp_qr_metadata_columns(self):
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        ecp_records_definition = schema.split(
            "CREATE TABLE IF NOT EXISTS public.ecp_records",
            1,
        )[1].split(");", 1)[0]

        for expected_column in (
            "qr_url text",
            "qr_key_id character varying(100)",
            "qr_payload jsonb",
            "qr_payload_hash character varying(64)",
            "issued_at timestamp",
            "valid_until date",
            "wallet_status character varying(30) DEFAULT 'not_issued'",
            "wallet_object_id text",
            "wallet_last_error text",
        ):
            self.assertIn(expected_column, ecp_records_definition)

    def test_qr_metadata_migration_is_available(self):
        migration = Path("database/migrations/2026-06-23-ecp-qr-metadata.sql").read_text(
            encoding="utf-8"
        )

        self.assertIn("ALTER TABLE public.ecp_records", migration)
        self.assertIn("ADD COLUMN IF NOT EXISTS qr_url text", migration)
        self.assertIn("ADD COLUMN IF NOT EXISTS valid_until date", migration)

    def test_schema_sql_can_apply_to_configured_postgres(self):
        database_url = os.environ.get("ESPELEO_TEST_DATABASE_URL")
        if not database_url:
            self.skipTest("Set ESPELEO_TEST_DATABASE_URL to run PostgreSQL schema integration test.")

        import psycopg2

        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(schema)
                cur.execute(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                    """
                )
                created_tables = {row[0] for row in cur.fetchall()}

        self.assertTrue({
            "members",
            "clubs",
            "ecp_records",
            "ecp_requests",
        }.issubset(created_tables))


if __name__ == "__main__":
    unittest.main()
