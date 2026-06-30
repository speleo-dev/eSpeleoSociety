# Signed Offline eCP QR

## Reader and Purpose

This note is for the maintainer configuring eCP issuance. After reading it, they should be able to generate a signing key, configure the desktop client, and understand what offline QR verification can trust.

## Current Behavior

The eCP issuance and approval flows now create an Ed25519-signed QR payload before activating the eCP. The QR contains a compact JSON payload with:

- schema version,
- member id,
- display name,
- primary club name,
- member status,
- issue timestamp,
- valid-until date,
- paid year,
- signing key id,
- Ed25519 signature.

The issuance flow no longer uploads a standalone QR PNG object for Google Wallet. Google Wallet should render the same signed payload through its native barcode support: `barcode.type = QR_CODE` and `barcode.value = issued_qr.qr_data`. The generated PNG bytes are kept only as an in-memory rendering source for the JPG/PDF card assets.

The database stores the optional legacy QR URL, signing key id, signed payload, payload hash, issue timestamp, validity date, public verification URL, card URLs, legal document URL, and Wallet issuance status on the eCP record. Existing databases need the QR metadata migration before this code path can run.

Public online verification URLs are tokenized static pages. In production the intended public base is:

```text
https://ecp.sss.sk/v/{token}
```

The corresponding generated HTML object is stored under `v/{token}.html` when `ecp_verification_base_url` is configured.

## Required Secrets

Configure these secrets in the encrypted desktop secrets file:

- `ecp_signing_key_id`: stable key identifier, for example `sss-ecp-2026-01`.
- `ecp_signing_private_key_b64`: base64 encoding of the PEM private key.
- `ecp_verification_base_url`: public base URL for tokenized verification pages, for example `https://ecp.sss.sk/v`.
- `ecp_verification_webroot`: local filesystem path to the verification hosting webroot when the app/backend can write there directly, for example the `ecp.sss.sk` Apache directory on the hosting server.

The signing loader also accepts `ecp_signing_private_key_pem` when the encrypted secrets file is edited manually. The setup dialog exposes the base64 form because it is easier to paste into a single-line field.

Generate a new key pair from the project environment:

```bash
python - <<'PY'
import base64
from ecp_qr import generate_ecp_signing_key_pair

private_pem, public_pem = generate_ecp_signing_key_pair()
print("ecp_signing_key_id=sss-ecp-2026-01")
print("ecp_signing_private_key_b64=" + base64.b64encode(private_pem).decode("ascii"))
print()
print(public_pem.decode("utf-8"))
PY
```

Store the private value only in secrets. Publish the public key to scanner/verifier applications.

## Offline Verification

Offline verifiers need the public key for the matching key id. They can verify the QR payload with the public key only. The private key is never needed for scanning.

Verification rejects:

- modified payload data,
- invalid signatures,
- expired `valid_until` dates,
- unknown public keys for the key id.

## Database Migration

Apply the QR metadata migration to existing databases before issuing new eCP records:

```bash
psql "$DATABASE_URL" -f database/migrations/2026-06-23-ecp-qr-metadata.sql
```

The development bootstrap schema already includes these columns.

## Backend Migration Note

Keeping the private signing key in the desktop client is a transitional step. The target API backend should own eCP issuance and signing. Desktop and portal clients should call the backend and should never store the private signing key.
