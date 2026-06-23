# Fix Log

## Reader and Purpose

This document is for the next maintainer of the eSpeleoSociety codebase. After reading it, they should know what was fixed, how to verify it locally without production secrets, and which issues still need a larger API/OAuth2 migration.

## Current Local State

The desktop GUI can start from a local virtual environment. If no encrypted secrets file exists, the application opens the setup dialog first. That is expected because database, Google Cloud, and cryptographic settings are not yet configured locally.

Run the GUI:

```bash
cd /home/dankez/eSpeleoSociety
.venv/bin/python main.py
```

Run the focused test suite:

```bash
cd /home/dankez/eSpeleoSociety
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -v
```

## Completed Fixes

### Technical Documentation

- Added a top-level project entry point with links to the main technical documents.
- Added a detailed technical manual covering the current product concept, architecture, UI flows, database tables, eCP issuance, SEPA processing, audit logging, security model, testing, local DB setup, known technical debt, and API/OAuth2 roadmap.

### Runtime Environment

- Added a dependency manifest for the current PyQt desktop application.
- Created a local virtual environment during this session.
- Confirmed the GUI starts far enough to show the initial setup flow when no encrypted secrets file is present.
- Added ignore rules for local virtual environments, Python bytecode caches, environment files, and encrypted local secrets.

### SEPA Payment Import

- Moved transaction classification into a pure Python module so payment import behavior can be tested without PyQt or PostgreSQL.
- Fixed the SEPA processing path so it returns processed transactions instead of silently returning `None`.
- Fixed payment saving year lookup by using the imported `datetime` correctly.
- Replaced GUI color comparison as business logic with a stable transaction `status`.
- Added tests for valid payments and unknown references with expected payment amounts.

### Optional Dependencies

- Changed cloud storage and AES imports so the utility module can be imported even when optional runtime dependencies are not yet installed.
- The code now raises a targeted runtime error only when a cloud or AES feature is actually used without its dependency.

### eCP Request Handling

- Fixed the Google Wallet placeholder helper so it accepts both request objects and dictionaries.
- Fixed pending eCP request lookup to use the same photo reference written by the request insert path.
- Fixed eCP record loading by selecting the `check_hash` field it reads.

### Author Schema Alignment

- Stored and analyzed the PostgreSQL schema export sent by the author on 2026-06-20.
- Realigned eCP request SQL with the author schema: `ecp_requests` now links to `ecp_records` through `ecp_record_id`.
- Removed the invalid `ecp_records.member_id` join assumption from photo-based eCP record lookup.
- Added eCP record lookup, approval update, and deletion paths based on `ecp_record_id`.
- Changed `insert_ecp` to return the created `ecp_record_id` for request linking.
- Updated DB contract tests so they protect the real schema instead of the previous temporary `photo_hash` request shape.

### Local PostgreSQL Schema Bootstrap

- Added a clean development/test PostgreSQL bootstrap schema derived from the author Adminer export.
- Replaced Adminer-exported pgcrypto C function stubs with `CREATE EXTENSION IF NOT EXISTS pgcrypto`.
- Omitted Adminer database/session commands so the schema can be applied to an already-created disposable database.
- Added static schema tests that verify the expected author tables and the `ecp_requests.ecp_record_id` foreign key.
- Added an optional PostgreSQL integration test gated by `ESPELEO_TEST_DATABASE_URL`; it is skipped during normal unit test runs when no test database is configured.

### Audit Logging

- Added audit log sanitization before log messages are written.
- Removed the largest raw object dumps from write-operation log messages.
- Redacted sensitive values such as eCP hashes, photo references, contact data, addresses, birth dates, credentials, and crypto keys.
- Added tests covering audit redaction.

### Offline eCP QR Foundation

- Added an Ed25519-based signed eCP payload module.
- The payload contains basic member, club, status, issue date, and validity date data.
- Offline verification works with a public key only.
- Tampered and expired payloads are rejected.
- Added tests for successful verification, tampering, and expiration.

### Signed eCP QR Issuance Flow

- Added an eCP issuance service that builds a signed offline-verifiable claim, serializes it into QR data, and renders a PNG QR image.
- Added signing secret loading for `ecp_signing_key_id`, `ecp_signing_private_key_b64`, and manually supplied PEM keys.
- Added one-year default eCP validity with leap-year handling.
- Wired direct eCP issuance and eCP request approval to generate and upload the signed QR before activating the eCP.
- Added QR metadata persistence for QR URL, key id, signed payload, payload hash, issue timestamp, validity date, and Wallet status.
- Added an additive DB migration for existing databases and updated the development bootstrap schema.
- Added signing fields to the secrets setup dialog.
- Added documentation for signing key generation, required secrets, offline verification, and the transitional backend migration caveat.

## Not Yet Done

- Google Wallet integration is still a placeholder.
- The eCP private signing key still lives in the desktop secrets file as a transitional step; final signing should move behind the API backend.
- The desktop client still uses direct database access; the API/OAuth2 migration is documented but not implemented.
- The database is not yet protected behind a backend-only network boundary.
- The member portal and club president portal do not exist yet.
- Real database integration tests require a configured PostgreSQL database and encrypted local secrets.
- The schema still lacks portal identity mapping, role assignments, eCP validity fields, Wallet issuance state, and a payment import ledger.

## Author Database Schema Snapshot

The author sent an Adminer PostgreSQL 14.13 schema export on 2026-06-20. It is stored as a reference SQL artifact and analyzed in the database documentation. The export confirms the current production-oriented tables for members, clubs, club affiliations, membership fees, eCP records, eCP requests, certificates, notifications, configuration, and DB logs.

Important finding: the dump conflicted with the previous temporary eCP request query contract. The code and tests now follow the real `ecp_record_id` relationship, and signed QR issuance now persists QR metadata and validity dates. The next eCP fix should implement real Google Wallet issuance state transitions.

## API/OAuth2 Direction

The next architectural step is to keep the desktop app as a thick administration client but move database, Google Cloud, Wallet, audit, and authorization decisions behind an HTTPS backend API. The desktop client and future web portals should authenticate through OAuth2/OIDC with PKCE and should never contain a database password or service account JSON.

The API migration plan is captured in the documentation added during this work. It defines the target roles, first API boundaries, QR signing expectation, and the order of migration.

## Verification Snapshot

At the end of the first stabilization pass, the focused tests passed and project Python files parsed successfully:

- Focused tests: 11 tests passed.
- Parser check: 35 project Python files parsed successfully.
- Dependency import check in the local virtual environment passed.
- No Python bytecode cache files remained in the project worktree.

After the author schema alignment fix:

- Focused tests: 16 tests passed.
- DB contract tests now cover `ecp_record_id` request joins, request inserts, eCP record lookup by ID, approval updates by ID, deletion by ID, and returning `ecp_record_id` from eCP record creation.

After the local PostgreSQL schema bootstrap:

- Static schema tests pass and verify the schema is not a raw Adminer dump.
- PostgreSQL apply test is available but skipped unless `ESPELEO_TEST_DATABASE_URL` points at a disposable database.

After the signed eCP QR issuance and metadata persistence wiring:

- Focused tests cover payload signing, verification, tamper rejection, expiration, one-year validity calculation, secret loading, PNG QR generation, upload handoff, GUI wiring, setup fields, QR metadata schema, additive migration, and DB issuance update contracts.
