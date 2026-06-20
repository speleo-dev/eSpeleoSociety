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

## Not Yet Done

- The signed eCP QR payload is not yet wired into the GUI issuance dialog.
- Author-provided PostgreSQL schema from 2026-06-20 shows that eCP request handling must be realigned: `ecp_requests` uses `ecp_record_id`, not `photo_hash`, and `ecp_records` has no `member_id`.
- Google Wallet integration is still a placeholder.
- The desktop client still uses direct database access; the API/OAuth2 migration is documented but not implemented.
- The database is not yet protected behind a backend-only network boundary.
- The member portal and club president portal do not exist yet.
- Real database integration tests require a configured PostgreSQL database and encrypted local secrets.

## Author Database Schema Snapshot

The author sent an Adminer PostgreSQL 14.13 schema export on 2026-06-20. It is stored as a reference SQL artifact and analyzed in the database documentation. The export confirms the current production-oriented tables for members, clubs, club affiliations, membership fees, eCP records, eCP requests, certificates, notifications, configuration, and DB logs.

Important finding: the dump conflicts with the current temporary eCP request query contract. The next fix should update the code and tests to follow the real schema before continuing with signed QR issuance.

## API/OAuth2 Direction

The next architectural step is to keep the desktop app as a thick administration client but move database, Google Cloud, Wallet, audit, and authorization decisions behind an HTTPS backend API. The desktop client and future web portals should authenticate through OAuth2/OIDC with PKCE and should never contain a database password or service account JSON.

The API migration plan is captured in the documentation added during this work. It defines the target roles, first API boundaries, QR signing expectation, and the order of migration.

## Verification Snapshot

At the end of this work, the focused tests passed and project Python files parsed successfully:

- Focused tests: 11 tests passed.
- Parser check: 35 project Python files parsed successfully.
- Dependency import check in the local virtual environment passed.
- No Python bytecode cache files remained in the project worktree.
