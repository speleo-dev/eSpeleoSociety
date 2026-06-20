# Author Database Schema Analysis

## Reader and Purpose

This note is for maintainers aligning the desktop client, future API backend, and portal work with the current PostgreSQL schema sent by the project author on 2026-06-20. After reading it, they should know what the schema contains, where it conflicts with current code assumptions, and which database changes are needed before the API/OAuth2 migration.

## What This Is

The supplied SQL is an Adminer 5.4.2 export from PostgreSQL 14.13 for database `eSpeleoSoc`. It contains schema DDL only: table definitions, sequences, constraints, indexes, and pgcrypto-related function exports. It does not contain application data.

The export should be treated as a reference snapshot, not a ready migration. The many `CREATE FUNCTION ... LANGUAGE c AS ''` statements are Adminer representations of pgcrypto functions. A proper restore or migration should install pgcrypto with `CREATE EXTENSION IF NOT EXISTS pgcrypto;` instead of redefining those functions manually.

## Data Model Summary

The schema has these main areas:

- `members`: core member identity, status, contact details, encrypted birth date, and current `ecp_hash`.
- `clubs`: club records, president reference, contact/address fields, and logo URL.
- `club_affiliations`: many-to-many member-to-club assignments with `is_primary_club`.
- `membership_fees`: member fee records by year and optional `ecp_hash`.
- `ecp_records`: eCP record hash, photo reference, active flag, GDPR/notification flags, and `check_hash`.
- `ecp_requests`: member request workflow linked to `ecp_records` through `ecp_record_id`.
- `member_certificates`: certificates per member with sequence number, issue/valid dates, and URL.
- `notifications`: scheduled notification text with validity window.
- `ess_config`: key/value application configuration.
- `db_logs`: current audit log table.

## Confirmed Relationships

- A member can belong to multiple clubs through `club_affiliations`.
- A club can have a president through `clubs.president_id -> members.member_id`.
- An eCP request belongs to a member through `ecp_requests.member_id`.
- An eCP request points at its pending or issued eCP record through `ecp_requests.ecp_record_id -> ecp_records.ecp_record_id`.
- A member's currently active eCP is linked indirectly through `members.ecp_hash -> ecp_records.ecp_hash`.
- A fee can reference both the member and the eCP hash that was current for that fee.

## Code Conflicts Found And Fixed

The author schema changed the next fix priority because it disproved two assumptions that were present in the desktop client:

- `ecp_requests` does not have a `photo_hash` column. The previous code inserted and joined eCP requests by `photo_hash`, which would fail against this schema.
- `ecp_records` does not have a `member_id` column. The previous code tried to join `ecp_records` to `members` with `er.member_id`, which would fail against this schema.

The request path now uses `ecp_requests.ecp_record_id`. The GUI can still expose `photo_hash`, but it fetches that value by joining `ecp_requests.ecp_record_id` to `ecp_records.ecp_record_id`.

Alignment completed in the desktop client:

1. eCP record creation returns `ecp_record_id`.
2. eCP request creation inserts `member_id`, `ecp_record_id`, `status`, and `request_date`.
3. Pending request fetch joins `ecp_requests.ecp_record_id = ecp_records.ecp_record_id`.
4. Photo lookup fetches `ecp_records` by `photo_hash` without joining on nonexistent `ecp_records.member_id`.
5. DB contract tests now assert the author schema relationship.

## Security Observations

- Birth dates are encrypted in PostgreSQL with pgcrypto, but the current desktop architecture still requires the encryption key and DB password on client machines. After the API migration, encryption and decryption should happen only inside the backend.
- `db_logs.details` is free text. It should not store raw member snapshots, eCP hashes, photo hashes, secrets, or decrypted PII.
- `ess_config` can become sensitive depending on stored keys. It should not hold plaintext secrets in a database reachable by thick clients.
- There is no user/account/role table in this schema. OAuth2 identities and role mapping will need new tables or an external identity provider mapping strategy.
- The eCP QR signing key must not be stored in the desktop client or portal. It belongs in backend-side secret management.

## Functional Gaps Against Target Product

The schema supports a basic desktop administration flow, but it is not yet enough for the planned member and club-president portals:

- No portal user identity mapping.
- No role assignments for `admin`, `club_president`, and `member`.
- No object-level authorization table for president-to-club scope beyond `clubs.president_id`.
- No eCP validity dates in `ecp_records`.
- No signed offline QR payload storage, key id, signature metadata, or QR version.
- No Google Wallet state fields such as wallet object id, issuance status, last error, or issued timestamp.
- No payment import ledger fields such as amount, variable symbol/reference, transaction id, statement id, booked date, or source bank account.
- No unique protection against duplicate fee rows for the same member/year/fee type.
- No explicit eCP request status check constraint.

## Performance and Integrity Gaps

Potentially useful indexes before the backend exposes list/search endpoints:

- `club_affiliations(club_id)` for club member lists.
- `clubs(president_id)` for president scope lookups.
- `ecp_requests(status, request_date)` for pending request queues.
- `ecp_requests(ecp_record_id)` because it is a foreign key and join column.
- `membership_fees(member_id, year)` for current-year fee checks.
- `members(last_name, first_name)` or trigram/full-text indexes for member search.
- `members(email)` if email lookup becomes part of portal identity matching.

Potential constraints:

- Only one primary club per member.
- Unique fee per member/year/fee type.
- Non-empty email uniqueness should be partial rather than `UNIQUE(email)` with empty string defaults.
- Request status should be constrained to the allowed workflow states.
- `ecp_records.photo_hash` should probably be unique if one uploaded photo maps to one eCP record.

## Backend Migration Implications

The API backend should own this schema directly and should publish stable DTOs to the desktop client and portals. Do not expose table shapes as client contracts. The first API slice should include an explicit eCP request DTO that returns:

- request id
- member id
- applicant display name
- request status
- request date
- eCP record id
- photo reference or temporary signed photo URL

That DTO hides the current database join path and lets the schema evolve later without breaking clients.

## Next Recommended Fix

The next code change can continue from the now-aligned eCP request handling and wire signed offline QR issuance:

- build the signed QR claim from member, club, paid-year, and validity data,
- store the signed payload or its immutable metadata,
- generate the QR image from the signed payload,
- keep the private signing key out of the desktop client in the final backend design,
- add integration tests once a disposable PostgreSQL database is available.

The desktop client still uses direct DB access, so this should remain a transitional implementation until the API backend owns eCP issuance.
