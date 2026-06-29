# eSpeleoSociety Backend API Skeleton

## Purpose

This is the first backend slice for moving database, eCP verification, and future portal access behind an HTTP API. It does not replace the desktop client yet. It creates a tested API boundary that the desktop client and future portals can migrate to endpoint by endpoint.

## Current Scope

Implemented API routes:

- `GET /api/v1/health`
- `GET /api/v1/clubs`
- `GET /api/v1/clubs/{club_id}/members`
- `GET /api/v1/ecp/verify/{token}`

OpenAPI contract:

- `docs/api/openapi.yaml`

## Auth Model

Authenticated routes use OAuth2-style bearer JWTs.

Development skeleton validation:

- algorithm: `HS256`
- audience: `espeleo-api`
- issuer: `espeleo-test`
- required subject claim: `sub`
- roles claim: `roles`, `scope`, or `realm_access.roles`
- club president scope: `club_ids`

Supported roles in this slice:

- `admin`
- `club_president`

Final production direction:

- replace shared-secret HS256 validation with OIDC/JWKS validation,
- keep the handler-level role checks,
- add service-layer authorization for every write operation.

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
- `GET /api/v1/clubs` has SQL-level filtering and keyset pagination; `GET /api/v1/clubs/{club_id}/members` still uses the desktop DB manager path before API-level pagination.
- JWT validation is development-only HS256. Production should use OIDC/JWKS.
- No write endpoints exist yet.
- No refresh tokens, login UI, or portal session handling exists yet.
- API request audit currently writes through the existing `db_logs` table; a dedicated API audit table and rate limiting are still required.

## Next Backend Slices

1. Add SQL-level pagination and search for club members.
2. Add a dedicated API audit table and rate limiting.
3. Add eCP revocation/renewal endpoints behind `admin`.
4. Add portal-member endpoint for "my profile" and "request eCP".
5. Replace HS256 development JWT validation with OIDC discovery and JWKS.
