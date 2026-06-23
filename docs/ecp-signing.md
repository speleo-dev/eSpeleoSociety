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

The QR image is uploaded as a PNG object under the `ecp_qr/` object prefix using the issued eCP hash as the object name. If signing configuration is missing, invalid, or the QR upload fails, the eCP is not activated.

The database stores the QR URL, signing key id, signed payload, payload hash, issue timestamp, validity date, and Wallet issuance status on the eCP record. Existing databases need the QR metadata migration before this code path can run.

## Required Secrets

Configure these secrets in the encrypted desktop secrets file:

- `ecp_signing_key_id`: stable key identifier, for example `sss-ecp-2026-01`.
- `ecp_signing_private_key_b64`: base64 encoding of the PEM private key.

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
