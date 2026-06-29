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

### Project Input Configuration And SMTP Notifications

- Ignored the local `docs/projekt/` directory because it contains email exports, screenshots, and plaintext configuration with sensitive values.
- Added missing setup fields from the original configuration screen: Google Wallet issuer ID, SMTP server, SMTP port, SMTP user, SMTP password, and log level.
- Masked DB password, SMTP password, crypt key, and eCP signing private key fields in the setup dialog.
- Added a testable SMTP notification module.
- Wired direct eCP issuance and eCP request approval to attempt an email notification after successful issuance.
- Email notification failure is warning-only and does not roll back an already issued or approved eCP.

### Club And Member Integrity

- Changed primary club updates so selecting a new primary club clears other primary club flags for the same member.
- Made member-club affiliation inserts idempotent with `ON CONFLICT`.
- Made membership fee inserts idempotent per member/year/fee type.
- Added a membership integrity migration that collapses existing duplicate primary-club and fee rows before creating unique indexes.
- Updated the development/test schema with the new integrity indexes.

## Not Yet Done

- Google Wallet integration is still a placeholder.
- SMTP notification is still desktop-side and has no backend outbox, retry, or delivery history.
- The eCP private signing key still lives in the desktop secrets file as a transitional step; final signing should move behind the API backend.
- The desktop client still uses direct database access; the API/OAuth2 migration is documented but not implemented.
- The database is not yet protected behind a backend-only network boundary.
- The member portal and club president portal do not exist yet.
- Real database integration tests require a configured PostgreSQL database and encrypted local secrets.
- The schema still lacks portal identity mapping, full authorization assignments, eCP validity fields, Wallet issuance state, and a payment import ledger.

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

## Local Runtime Configuration Check

- The desktop app crashed after saving setup values because the encrypted local configuration used database name `lacisss`, while the Websupport PostgreSQL server accepts the project database as `eSpeleoSoc`.
- Verified the encrypted `secrets.properties` can be decrypted with the local test PIN and contains DB host `db.r5.websupport.sk`, port `5432`, user value present, and password value present.
- Tested PostgreSQL connectivity against candidate database names without printing the password. `lacisss` failed with "database does not exist"; `eSpeleoSoc` connected successfully.
- Updated only the local encrypted DB name to `eSpeleoSoc`; no password or secret value was written into documentation.
- Relaunched `main.py`; the GUI process stayed alive after startup with the corrected local DB name.
- Added root-level local artifacts `codex-session`, `os`, and `sys` to `.gitignore`. The `os` and `sys` files were accidental ImageMagick/PostScript screen-capture artifacts and must not be committed.

## SSS Club Directory Import And Webpage Support

- Added native `clubs.webpage` support so the club list can show a separate webpage column instead of mixing web links into phone or email fields.
- Changed the development/test schema and additive migration so `clubs.phone` and `clubs.email` are `text`. This preserves multiple phone numbers and multiple email addresses as comma-separated values.
- Added `clubs.president_name_text` for the original public chairperson name imported from the SSS directory.
- Added support for SSS directory presidents as member records: `members.is_directory_stub` marks imported public records that do not yet have complete member identity data such as birth date.
- Relaxed `members.birth_date_encrypted` so directory stub members can exist without inventing a fake birth date.
- Added `club_affiliations.role` with current values `member` and `president`.
- The SSS import now creates or reuses a president member, inserts primary club affiliation with role `president`, and sets `clubs.president_id`.
- Existing real president members are reused and not overwritten by public directory data; only directory stub members are refreshed from the import.
- Updated the desktop DB read/write contract to fetch, insert, update, and upsert `webpage` and `president_name_text`.
- Updated the List of SSS Clubs table to include a `Webpage` column. Long phone, email, and webpage values are kept in the cell and exposed through tooltips instead of being truncated in the model.
- Updated the club management dialog and club detail header to display/edit webpage and public president text.
- Updated the member list to show an explicit `Role` column and to sort club presidents first.
- Added `tools/import_sss_clubs.py` for repeatable import from `https://sss.sk/zoznam-oblastnych-skupin/`. The dry-run parser currently reads 53 rows from the public SSS table.
- Import parsing keeps repeated contact values as `value1, value2`: multiple phones stay in `phone`, multiple emails stay in `email`, and HTTP/HTTPS links stay in `webpage`.
- Added focused tests for the parser, club DB contracts, schema columns, and the additive migration.
- Applied the additive migration and imported/updated 53 public SSS club directory rows in the configured PostgreSQL database. Post-import verification showed 57 clubs total, 53 rows with public president text, 53 rows with phone, 57 rows with email, and 31 rows with webpage.
- Re-applied the import after adding president-member support. Post-import verification showed 53 clubs with `president_id`, 53 `club_affiliations.role = 'president'` rows, and 53 directory stub members. `Speleoklub Nitra` was verified with `doc. Mgr. Tomáš Lánczos, PhD.` as primary club member with role `president`.

## Inline Table Editing

- Enabled double-click inline editing in the List of SSS Clubs table for editable data columns: club name, address fields, country, email, phone, webpage, and displayed president text.
- Club table edits are persisted immediately through `db.update_club`; member count and action button cells remain read-only because they are derived/control cells.
- Added sorting and filtering controls to the List of SSS Clubs header.
- The club table now starts sorted by club name A-Z, supports Z-A through the header button, and also supports regular Qt header-click sorting for other columns.
- The club filter searches across club name, address fields, country, email, phone, webpage, president text, and member count.
- Inline club editing now stores `club_id` on each table item so editing remains safe after the table is sorted or filtered.
- Enabled double-click inline editing in the members table inside a club.
- Fixed-choice member fields use dropdown editors: `status` supports `applicant`, `active`, `inactive`, `blocked`; club role supports `member` and `president`.
- Member text/date edits persist immediately: title prefix, full name, title suffix, birth date, address, phone, and email.
- Birth date inline edits accept empty value or ISO `YYYY-MM-DD`; invalid date text is rejected and reverted.
- Changing a member role to `president` clears any previous president role in that club, sets the member as primary in that club, and updates `clubs.president_id`.
- Changing a president role back to `member` clears `clubs.president_id` only if it pointed to that member.
- Added pure parser tests for inline full-name, address, and date editing plus DB contract tests for birth-date updates and role changes.

## eCP Delivery, QR Detail Page, Email Attachments, And Portraits

- Added `ecp_documents.py` with the public legal document URL for the current general exception PDF: `https://sss.sk/wp-content/uploads/2026/06/vynimka.pdf`.
- Extended the signed QR claim so it can include `verification_url` and `legal_documents`.
- The QR remains GDPR-minimal: tests assert it does not include birth date, email, phone, street, or contact/address fields.
- Added `ecp_card.py` to generate the member card from the same signed QR payload as:
  - JPG card asset under `ecp_cards/{ecp_hash}.jpg`,
  - PDF card asset under `ecp_cards/{ecp_hash}.pdf`,
  - tokenized static verification HTML under `ecp_verify/{random_token}.html`.
- The verification HTML contains member name, member ID, club, status, issue date, validity, signing key ID, payload hash, portrait image URL when available, QR/JPG/PDF links, and legal document links.
- The static page includes `noindex`, `nofollow`, `noarchive`, and `no-referrer` metadata.
- Security caveat: because this is still a static GCS page, protection is based on an unguessable random URL token and non-indexing metadata. It is not equivalent to authenticated access control. True revocation, access logging, rate limiting, and role-based detailed data access still belong in the future API/OAuth2 backend.
- Added `issue_and_upload_ecp_delivery_bundle()` in `ecp_issuance.py`. It:
  - builds a random verification page URL first,
  - signs the QR claim with that URL included,
  - uploads the QR PNG,
  - generates and uploads JPG/PDF card assets,
  - uploads the static verification page,
  - returns all bytes and URLs for DB persistence and email sending.
- Direct eCP issuance now uses the delivery bundle and emails the generated JPG/PDF card as attachments.
- eCP request approval now uses the same delivery bundle and emails the generated JPG/PDF card as attachments.
- The email body now includes the online verification URL, card URLs when available, and the legal PDF URL.
- Added mass eCP card sending from the members list. It does not issue new cards; it sends email for selected members that already have an eCP record, using stored verification/card URLs.
- Added reusable member portrait support:
  - `members.portrait_url`,
  - `members.portrait_hash`,
  - `members.portrait_face_detected`,
  - `members.portrait_updated_at`.
- Member add/edit dialog now supports portrait photo upload without showing photos in member tables.
- Added `face_detection.py` to normalize portrait uploads to JPEG, reject tiny images, and run OpenCV Haar face detection when `opencv-python-headless` is installed.
- If OpenCV is unavailable or no face is detected, the user gets a warning and can decide whether to continue with the portrait.
- eCP issuance preloads a saved member portrait when available, while still allowing a fresh eCP photo to be loaded in the issuance dialog.
- Added additive migration `database/migrations/2026-06-29-ecp-delivery-and-portraits.sql`.
- Updated `database/schema.sql` with delivery and portrait columns.
- Applied the migration to the configured PostgreSQL database and verified all 8 new columns exist.
- Removed the four explicit test clubs from the configured database: `Test1`, `Test2`, `Test 3`, and `Test4`.
- Verified that the configured database now returns 0 club names matching `test`, `skus`, or `skúš`.
- Verified the legal PDF URL with HTTP HEAD: it returns `HTTP 200`, content type `application/pdf`, and last modified timestamp `2026-06-01 18:46:31 UTC`.
- Added/updated tests for QR GDPR-minimal claims, delivery bundle upload flow, card JPG/PDF generation, email attachments, schema migration, DB query contracts, portrait preparation, and flow wiring.
- Full local verification after this change:
  - `rtk .venv/bin/python -m unittest discover -s tests -v`: 63 tests passed, 1 PostgreSQL integration test skipped because `ESPELEO_TEST_DATABASE_URL` is not set.
  - `rtk .venv/bin/python -m compileall -q .`: passed.

## Backend API/OAuth2 Skeleton

- Added a new `backend/` package as the first step toward moving DB, eCP verification, and portal access behind an HTTP API.
- Added `backend.app.ApiApp` with a testable `handle_request()` interface.
- Added WSGI adapter and development server:
  - `backend/wsgi.py`
  - `backend/dev_server.py`
- Added development OAuth2-style bearer JWT validation in `backend/auth.py`.
- Current JWT skeleton validates:
  - HS256 signature,
  - audience `espeleo-api`,
  - issuer `espeleo-test`,
  - subject `sub`,
  - roles from `roles`, `scope`, or `realm_access.roles`,
  - club president restrictions through `club_ids`.
- Implemented first API routes:
  - `GET /api/v1/health` public,
  - `GET /api/v1/clubs` for `admin` or `club_president`,
  - `GET /api/v1/clubs/{club_id}/members` for `admin` or president of that club,
  - `GET /api/v1/ecp/verify/{token}` public tokenized eCP online verification.
- Added cursor pagination helpers with default limit `50` and max limit `200`.
- Added public API serializers so endpoint JSON does not expose internal model names.
- Added eCP verification serializer that intentionally excludes email, phone, address, and birth date.
- Added `DatabaseApiRepository` adapter over the existing `db_manager`.
- Added token validation before DB lookup for eCP online verification tokens.
- Added OpenAPI contract at `docs/api/openapi.yaml`.
- Added backend API manual at `docs/api/backend-api.md`.
- Updated `docs/api-oauth2-migration-plan.md` with the implemented skeleton and hardening gaps.
- Added tests for health, missing bearer token, admin club list pagination, club president member authorization, eCP public verification sanitization, WSGI adapter behavior, and DB repository token lookup.
- Full local verification after this backend skeleton:
  - `rtk .venv/bin/python -m unittest discover -s tests -v`: 73 tests passed, 1 PostgreSQL integration test skipped because `ESPELEO_TEST_DATABASE_URL` is not set.
  - `rtk .venv/bin/python -m compileall -q .`: passed.
  - `rtk git diff --check`: passed.

## Backend API Audit And SQL Club Pagination

- Changed `GET /api/v1/clubs` so the API handler calls `DatabaseApiRepository.list_clubs(limit, cursor, filter_text)` instead of loading all clubs and paginating in memory.
- Added keyset cursor helpers for id-based pagination:
  - `encode_id_cursor(last_id)`,
  - `decode_id_cursor(cursor)`.
- Implemented SQL-level club listing in `DatabaseApiRepository`:
  - filters by club name, city, email, phone, webpage, and public president text,
  - escapes SQL LIKE wildcards,
  - caps filter text at 100 characters,
  - uses `c.club_id > last_id`,
  - fetches `limit + 1` rows to decide whether `nextCursor` should be returned.
- Avoided importing the desktop `model` package from `backend.repository` because the current desktop model layer has a circular import through `model.member -> db -> model`.
- Added a lightweight `ClubRecord` API record with the attributes required by the API serializer.
- Added `backend.audit.AuditEvent` for compact API request audit records.
- `ApiApp` now records an audit event after handled requests when the repository or supplied audit sink implements `record_api_audit_event(event)`.
- Audit records intentionally store route templates such as `/api/v1/ecp/verify/{token}` instead of raw eCP verification URLs, so token values are not persisted to `db_logs`.
- Implemented `DatabaseApiRepository.record_api_audit_event()` over the existing sanitized `db_logs` writer as a transitional audit path.
- Updated `docs/api/backend-api.md` with club filter semantics, SQL pagination, and audit behavior.
- Updated `docs/api/openapi.yaml` with the `filter` query parameter for `/clubs`.
- Updated `docs/api-oauth2-migration-plan.md` to mark SQL club pagination and transitional API request audit as implemented.
- Added tests for:
  - API handler delegating club pagination/filtering to the repository,
  - API audit event creation for authenticated club listing,
  - public eCP verification audit without raw token persistence,
  - DB repository SQL filter/keyset pagination contract,
  - DB repository audit logging contract.

## Member Portal Profile API

- Added the first member portal API endpoint: `GET /api/v1/me`.
- Extended the development JWT auth context with a transitional member identity link:
  - `member_id`,
  - `memberId`.
- `GET /api/v1/me` requires role `member` and one of those member identity claims.
- If the token is authenticated but not linked to a member, the API returns `403` with error code `member_identity_required`.
- The endpoint reads only the authenticated member's own profile through `DatabaseApiRepository.fetch_member_portal_profile(member_id)`.
- The profile response includes:
  - member id,
  - status,
  - display name and title/name fields,
  - email and phone,
  - portrait URL,
  - primary club id/name,
  - eCP active/validity/card/wallet status,
  - latest pending eCP request summary.
- The profile response intentionally does not expose:
  - `ecp_hash`,
  - encrypted birth date,
  - address fields,
  - DB/internal record hashes.
- Added `member_profile_to_api()` serializer.
- Added SQL lookup for member portal profiles with joins to:
  - primary club affiliation,
  - current eCP record by `members.ecp_hash`,
  - latest pending `ecp_requests` row.
- `POST /api/v1/me/ecp-requests` is intentionally not implemented in this slice. The existing approval flow requires an `ecp_record_id` with a valid `photo_hash`, so the next safe step is backend photo upload plus request creation in one flow.
- Updated `docs/api/backend-api.md`, `docs/api/openapi.yaml`, and `docs/api-oauth2-migration-plan.md`.
- Added tests for:
  - member role fetching its own portal profile,
  - missing member identity claim returning `member_identity_required`,
  - DB repository profile mapping and avoiding `birth_date_encrypted` selection.
