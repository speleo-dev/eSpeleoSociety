# Database Bootstrap

## Purpose

This directory contains a development and test bootstrap schema derived from the PostgreSQL schema export sent by the project author on 2026-06-20.

Use it for disposable local databases and CI integration tests. Do not apply it directly to production because it drops and recreates tables.

## Apply Locally

Create an empty PostgreSQL database, then apply the schema:

```bash
psql "$ESPELEO_TEST_DATABASE_URL" -f database/schema.sql
```

The schema installs `pgcrypto`, creates the author-provided tables, sequences, indexes, and foreign keys, and keeps the `ecp_requests.ecp_record_id -> ecp_records.ecp_record_id` relationship that the desktop code now expects.

## Integration Test

The unit test suite always runs static schema checks. The PostgreSQL integration check runs only when this environment variable is set:

```bash
ESPELEO_TEST_DATABASE_URL=postgresql://user:password@localhost:5432/espeleo_test \
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest tests.test_database_schema_sql -v
```

Run this only against a disposable database. The bootstrap schema intentionally drops existing application tables before recreating them.
