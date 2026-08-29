---
name: espeleo-migrations
description: Write and review PostgreSQL schema changes for eSpeleoSociety safely - migration file conventions, transactionality, encrypted PII columns, referential integrity and rollback planning. Use when adding a column or table, changing constraints, writing a file in database/migrations/, editing database/schema.sql, or when asked to "pridaj stlpec", "zmen schemu", "napis migraciu", "add a migration".
---

# eSpeleoSociety Migration Skill

The database is the source of truth for member PII, membership fees and issued
eCP records. A bad migration loses financial history or leaks personal data, so
every schema change follows this procedure.

## Layout

- `database/schema.sql` — the full current schema, used to bootstrap a fresh
  database and asserted by `tests/test_database_schema_sql.py`.
- `database/migrations/YYYY-MM-DD-short-slug.sql` — incremental changes applied
  to existing databases.
- `database/README.md` — bootstrap instructions.

**Every schema change edits both**: the migration file for existing databases
and `schema.sql` so a fresh bootstrap ends up identical. They drifting apart is
the most common failure mode here.

## Migration file rules

1. **Wrap the whole file in a transaction.**

   ```sql
   BEGIN;
   -- statements
   COMMIT;
   ```

   Without this, a failure halfway leaves a half-applied schema.
   `2026-06-28-membership-integrity.sql` is the existing counter-example — do not
   copy its style.

2. **Be idempotent and additive.** Use `IF NOT EXISTS` / `IF EXISTS`, add
   nullable columns or columns with defaults, and backfill in a separate
   statement. Existing migrations state "additive and safe for existing
   databases" in a header comment — keep that convention and that header.

3. **Never `DROP` a column holding member data in the same migration that stops
   writing to it.** Stop writing, ship, verify, then drop in a later migration.

4. **Guard destructive `ON DELETE` behavior.** `membership_fees` cascades from
   `ecp_hash`, meaning deleting an eCP record deletes financial history. Prefer
   `ON DELETE RESTRICT` or a soft-delete flag for anything with legal or
   financial meaning.

5. **Adding a `UNIQUE` constraint requires a duplicate check first.** For
   example `members.email` currently has no `UNIQUE` constraint; before adding
   one, ship a query that lists existing duplicates and a plan to resolve them,
   otherwise the migration fails on production data.

6. **Encrypted columns.** Birth dates and other sensitive fields are encrypted.
   Do not add a plaintext copy of an encrypted column for convenience, do not
   index the ciphertext expecting equality search to be meaningful, and
   remember that `pgcrypto` `encrypt()` with a fixed IV makes identical values
   produce identical ciphertext — prefer `pgp_sym_encrypt`.

7. **No secrets in SQL.** Keys and passwords come from the encrypted config, not
   from a migration file or a default value.

## Procedure

1. Read `database/schema.sql` for the affected tables and their existing
   constraints and indexes.
2. Write the migration file with today's date and a descriptive slug.
3. Mirror the change into `database/schema.sql`.
4. Update `backend/repository.py` and/or `db.py` queries, plus the serializers
   and the OpenAPI contract if the change is visible over the API.
5. Verify:

   ```bash
   python3 tools/preflight_check.py migrations
   PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_database_schema_sql tests.test_db_query_contracts -v
   ```

6. Apply against a disposable database and run the integration test:

   ```bash
   ESPELEO_TEST_DATABASE_URL=postgresql://user:pass@localhost/espeleo_test \
     PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_database_schema_sql -v
   ```

   Never test a migration against the production database.

## Rollback plan

State the rollback in a comment at the top of every migration: either the
inverse SQL, or an explicit note that the change is irreversible and why
(for example, a backfill that loses the original value). "Restore from backup"
is only acceptable when you have confirmed a backup exists and say when it was
taken.

## Connection handling

`db.DatabaseManager` opens a new connection per operation and never closes them
explicitly, which exhausts `max_connections` under load. If your change adds new
query paths, use the existing `DatabaseManager.transaction()` context manager
rather than adding another bare connection, and prefer batching over per-row
queries.
