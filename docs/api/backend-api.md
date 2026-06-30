# eSpeleoSociety Backend API Skeleton

## Purpose

This is the first backend slice for moving database, eCP verification, and future portal access behind an HTTP API. It does not replace the desktop client yet. It creates a tested API boundary that the desktop client and future portals can migrate to endpoint by endpoint.

## Current Scope

Implemented API routes:

- `GET /api/v1/health`
- `GET /api/v1/clubs`
- `GET /api/v1/clubs/{club_id}/members`
- `PATCH /api/v1/members/{member_id}`
- `GET /api/v1/me`
- `POST /api/v1/me/ecp-requests`
- `GET /api/v1/ecp/verify/{token}`

OpenAPI contract:

- `docs/api/openapi.yaml`

## Auth Model

Authenticated routes use OAuth2-style bearer JWTs. The backend now supports production-style OIDC/JWKS validation and keeps HS256 only as a local/development fallback.

Production OIDC/JWKS validation:

- configure `ESPELEO_OIDC_JWKS_URL` or secret `oidc_jwks_url`
- configure `ESPELEO_API_ISSUER` / secret `api_issuer`
- configure `ESPELEO_API_AUDIENCE` / secret `api_audience`
- optional algorithms: `ESPELEO_OIDC_ALGORITHMS` or secret `oidc_algorithms`, comma-separated, default `RS256`
- supported role sources: `roles`, `scope`, `realm_access.roles`, and OIDC `resource_access.*.roles`

Development fallback validation:

- algorithm: `HS256`
- audience: `espeleo-api`
- issuer: `espeleo-test`
- required subject claim: `sub`
- roles claim: `roles`, `scope`, or `realm_access.roles`
- club president scope: `club_ids`
- member portal link: `member_id` or `memberId`

Supported roles in this slice:

- `admin`
- `club_president`
- `member`

Authorization model:

- keep the handler-level role checks,
- add object-level authorization for every write operation.

## Endpoint Semantics

### `GET /api/v1/health`

Public health check.

Response:

```json
{"status":"ok","version":"v1"}
```

### `GET /api/v1/clubs`

Requires `admin` or `club_president`.

Query:

- `limit`: default `50`, max `200`
- `cursor`: opaque cursor from the previous response
- `filter`: optional case-insensitive search over club name, city, email, phone, webpage, and public president text
- `q`: alias for `filter`

The current implementation performs club filtering and pagination in SQL using keyset pagination over `club_id`. It fetches `limit + 1` rows to decide whether a `nextCursor` should be returned.

Response:

```json
{
  "items": [
    {
      "id": 1,
      "name": "Speleo Club",
      "street": "",
      "city": "",
      "zipCode": "",
      "country": "SK",
      "email": "",
      "phone": "",
      "webpage": "",
      "presidentName": "",
      "memberCount": 0
    }
  ],
  "nextCursor": null
}
```

### `GET /api/v1/clubs/{club_id}/members`

Requires:

- `admin`, or
- `club_president` with `{club_id}` present in the JWT `club_ids` claim.

The response includes operational member data needed for administration. This endpoint should not be exposed to ordinary members.

### `PATCH /api/v1/members/{member_id}`

Requires:

- `admin`, or
- `club_president` when the target member belongs to one of the caller's JWT `club_ids`.

This is the first administrative write endpoint behind the backend API. It intentionally exposes only a narrow profile edit surface:

```json
{
  "status": "active",
  "titlePrefix": "Mgr.",
  "firstName": "Ada",
  "lastName": "Lovelace",
  "titleSuffix": "",
  "email": "ada@example.sk",
  "phone": "0901",
  "discountedMembership": false
}
```

Writable fields map to `members.member_status`, titles, first/last name, email, phone, and `discounted_membership`.

Not writable through this endpoint:

- encrypted birth date,
- address fields,
- eCP hashes and verification secrets,
- portrait/photo URLs or hashes,
- club affiliations and club roles.

Rules:

- request body must be a JSON object,
- at least one supported field is required,
- unknown fields return `422 unknown_member_update_field`,
- `status` must be one of `applicant`, `active`, `inactive`, `blocked`,
- `firstName` and `lastName` cannot be blank when supplied,
- `club_president` callers are checked against `club_affiliations` before any update runs.

Response `200` returns the same member summary shape as the club member list.

### `GET /api/v1/me`

Requires role `member` and a JWT `member_id` or `memberId` claim.

This endpoint is the first member portal API slice. It returns the authenticated member's own profile and eCP/request status without exposing internal hashes, encrypted birth date, or address fields.

Response:

```json
{
  "id": 101,
  "status": "active",
  "titlePrefix": "",
  "firstName": "Ada",
  "lastName": "Lovelace",
  "titleSuffix": "",
  "displayName": "Ada Lovelace",
  "email": "ada@example.sk",
  "phone": "0901",
  "portraitUrl": "https://storage.example/portrait.jpg",
  "primaryClub": {
    "id": 1,
    "name": "Speleo Club"
  },
  "hasEcp": true,
  "ecp": {
    "active": true,
    "validUntil": "2027-06-29",
    "verificationUrl": "https://storage.example/ecp_verify/token.html",
    "cardImageUrl": "https://storage.example/card.jpg",
    "cardPdfUrl": "https://storage.example/card.pdf",
    "walletStatus": "issued"
  },
  "pendingEcpRequest": {
    "id": 55,
    "status": "pending",
    "requestDate": "2026-06-29"
  }
}
```

If the token is authenticated but has no member link, the API returns `403` with code `member_identity_required`.

### `POST /api/v1/me/ecp-requests`

Requires role `member` and a JWT `member_id` or `memberId` claim.

Creates a pending eCP request for the authenticated member. The request body is JSON with an uploaded portrait/photo encoded as base64. The backend stores the photo through the configured storage uploader, creates an inactive `ecp_records` row, and links `ecp_requests.ecp_record_id` so the existing admin approval flow can process it.

Request:

```json
{
  "photoBase64": "<base64 image bytes>",
  "contentType": "image/jpeg",
  "gdprConsent": true,
  "notificationsEnabled": true
}
```

Rules:

- `photoBase64` is required.
- decoded photo size must be 5 MB or smaller.
- `contentType` must be `image/jpeg` or `image/png`.
- `gdprConsent` must be explicitly `true`.
- `notificationsEnabled` defaults to `true`.
- if the member already has a pending eCP request, the API returns `409 ecp_request_already_pending` and does not upload a new photo.

Response `201`:

```json
{
  "id": 77,
  "memberId": 101,
  "ecpRecordId": 88,
  "photoHash": "photo-hash",
  "photoUrl": "https://storage.example/ecp_request_photos/photo-hash.jpg",
  "status": "pending",
  "requestDate": "2026-06-29"
}
```

Validation errors use `422` with stable codes such as `invalid_request_body`, `photo_required`, `invalid_photo_base64`, `photo_too_large`, `unsupported_photo_content_type`, and `gdpr_consent_required`. Duplicate pending requests use `409 ecp_request_already_pending`.

### `GET /api/v1/ecp/verify/{token}`

Public tokenized online eCP verification endpoint.

The response intentionally excludes:

- email,
- phone,
- address,
- birth date.

It returns only verification-oriented information: display name, club, status, validity, portrait/card links, legal document link, and signed QR payload hash.

## Error Shape

All API errors use the same envelope:

```json
{
  "error": {
    "code": "forbidden",
    "message": "Authenticated caller is not allowed to access this resource.",
    "requestId": "req_..."
  }
}
```

HTTP status codes are used honestly:

- `401` missing or invalid token,
- `403` authenticated but not allowed,
- `404` resource or route not found.

## Audit Logging

`ApiApp` records a compact audit event after each handled request when the configured repository or explicit audit sink implements `record_api_audit_event(event)`.

Stored audit fields:

- request id,
- HTTP method,
- route template,
- status code,
- authenticated subject or `anonymous`,
- sorted roles,
- outcome,
- error code.

The audit event intentionally stores route templates such as `/api/v1/ecp/verify/{token}` instead of raw request paths, so tokenized eCP verification URLs are not written to `db_logs`.

## Running Locally

The skeleton has no web framework dependency. It uses a WSGI adapter and Python's development server.

```bash
cd /home/dankez/eSpeleoSociety
ESPELEO_SECRETS_PIN=<local-secrets-pin> \
ESPELEO_OIDC_JWKS_URL=https://idp.example/realms/espeleo/protocol/openid-connect/certs \
ESPELEO_API_ISSUER=https://idp.example/realms/espeleo \
ESPELEO_API_AUDIENCE=espeleo-api \
ESPELEO_API_PORT=8080 \
.venv/bin/python -m backend.dev_server
```

For local tests without an OIDC provider, use the development fallback:

```bash
ESPELEO_API_JWT_SECRET=dev-secret \
ESPELEO_API_PORT=8080 \
.venv/bin/python -m backend.dev_server
```

Health check:

```bash
curl http://127.0.0.1:8080/api/v1/health
```

For protected routes, send:

```text
Authorization: Bearer <jwt>
```

## Known Limitations

- The API still uses the existing PostgreSQL schema and DB manager.
- `GET /api/v1/clubs` and `GET /api/v1/clubs/{club_id}/members` have SQL-level filtering and keyset pagination.
- OIDC discovery and login/session handling are not implemented; the API validates already-issued bearer access tokens.
- HS256 remains available only as a development fallback when no JWKS URL is configured.
- Only the first narrow admin member update endpoint exists; create/delete, fee writes, eCP approval, club role changes, and SEPA writes still need backend endpoints.
- No refresh tokens, login UI, or portal session handling exists yet.
- `POST /api/v1/me/ecp-requests` accepts JSON/base64 upload as a transitional API shape. A production portal can later switch to multipart or direct-to-storage signed upload without changing the approval data model.
- API request audit currently writes through the existing `db_logs` table; a dedicated API audit table and rate limiting are still required.

## Next Backend Slices

1. Add a dedicated API audit table and rate limiting.
2. Switch one desktop read path to `api_client.py` while keeping DB fallback behind a feature flag/config switch.
3. Add idempotency keys for `POST /api/v1/me/ecp-requests`.
4. Add admin/president write endpoints for member create, club affiliation/role, fees, and eCP request approval.
5. Add OIDC Authorization Code + PKCE login flow for the desktop and web portals.
