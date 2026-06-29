# API and OAuth2 Migration Plan

## Goal

Keep the desktop application as a thick administration client, but remove direct database access from every client machine. PostgreSQL must only be reachable from a backend API runtime on the server/private network.

## Target Architecture

- **Backend API:** Owns all PostgreSQL access, GCS/Wallet credentials, eCP issuance rules, payment import writes, audit logging, and authorization decisions.
- **Admin desktop client:** PyQt application calling HTTPS API endpoints. It stores no DB password and authenticates through OAuth2/OIDC Authorization Code + PKCE.
- **Member portal:** Web portal for members to view profile data, request eCP, upload/replace photo, see request status, and see payment status.
- **Club president portal:** Web portal role for managing members of the president's own club only.
- **Database:** Private network only. No inbound access except from backend API service identity.

## Auth Model

- Use an OAuth2/OIDC provider with Authorization Code + PKCE for public clients.
- Access token audience must be the backend API.
- Backend derives authorization from token claims and server-side membership/club assignments.
- Minimum roles:
  - `admin`: full society administration.
  - `club_president`: CRUD limited to assigned club members and club eCP requests.
  - `member`: own profile, own eCP request, own payment/eCP status.

## First API Boundaries

1. `GET /clubs`
2. `GET /clubs/{club_id}`
3. `GET /clubs/{club_id}/members`
4. `GET /members/search?q=...`
5. `POST /members`
6. `PATCH /members/{member_id}`
7. `POST /members/{member_id}/fees`
8. `POST /members/{member_id}/ecp-requests`
9. `GET /ecp-requests?status=pending`
10. `POST /ecp-requests/{request_id}/approve`
11. `POST /ecp-requests/{request_id}/reject`
12. `POST /sepa-statements/import`

## eCP Offline QR Requirement

The QR payload must not be just a random hash. It should contain a signed, minimal offline-verifiable claim:

- schema version
- member id or opaque public member id
- display name
- primary club id/name
- membership status
- paid year or valid-until date
- issued-at timestamp
- expires-at timestamp
- key id
- signature

Use an asymmetric signature for offline verification so scanner apps can verify with a public key. Keep private signing keys only in the backend.

The desktop client currently has a transitional signed-QR implementation so issued eCP cards can be verified offline before the backend exists. During the API migration, move the private signing key and QR generation behind the backend and remove private signing secrets from desktop installations.

## Implemented Backend Skeleton

The first backend slice now exists under `backend/` and is documented in `docs/api/backend-api.md`.

Implemented routes:

- `GET /api/v1/health`
- `GET /api/v1/clubs`
- `GET /api/v1/clubs/{club_id}/members`
- `GET /api/v1/ecp/verify/{token}`

Contract:

- `docs/api/openapi.yaml`

Current skeleton choices:

- WSGI adapter with no web framework dependency.
- Development JWT validation through HS256.
- Roles: `admin`, `club_president`.
- `club_president` access is constrained by JWT `club_ids`.
- Public eCP verification endpoint returns only verification-safe details and excludes contact/address/birth-date fields.

Production hardening still required:

- Replace HS256 with OIDC/JWKS validation.
- Move list pagination/filtering into SQL.
- Add audit logging and rate limiting.
- Add write endpoints only after service-layer authorization is in place.

## Migration Sequence

1. Add API client abstraction to the PyQt app while keeping `DatabaseManager` for current behavior.
2. Implement backend read endpoints for clubs and members.
3. Switch the desktop client read paths to API client calls.
4. Implement backend write endpoints with audit logging and role checks.
5. Switch desktop write paths to API client calls.
6. Move GCS upload and Google Wallet issuance behind backend endpoints.
7. Implement member portal request flow for eCP.
8. Implement president portal scoped member management.
9. Remove DB credentials from desktop `secrets.properties`.
10. Restrict PostgreSQL networking to backend-only access.

## Non-Negotiable Controls

- No DB password in desktop or portal clients.
- No service account JSON in desktop or portal clients.
- Backend authorization must be object-level, not only role-level.
- Audit logs must store actor, action, entity type/id, result, and timestamp, not raw PII snapshots.
- eCP approval must be transactional: DB update, QR claim generation, Wallet issuance state, and request status must not diverge silently.
