-- Persist signed eCP QR and Google Wallet issuance metadata.
-- Safe to apply to an existing database; it only adds missing columns.

BEGIN;

ALTER TABLE public.ecp_records
    ADD COLUMN IF NOT EXISTS qr_url text,
    ADD COLUMN IF NOT EXISTS qr_key_id character varying(100),
    ADD COLUMN IF NOT EXISTS qr_payload jsonb,
    ADD COLUMN IF NOT EXISTS qr_payload_hash character varying(64),
    ADD COLUMN IF NOT EXISTS issued_at timestamp,
    ADD COLUMN IF NOT EXISTS valid_until date,
    ADD COLUMN IF NOT EXISTS wallet_status character varying(30) DEFAULT 'not_issued',
    ADD COLUMN IF NOT EXISTS wallet_object_id text,
    ADD COLUMN IF NOT EXISTS wallet_last_error text;

CREATE INDEX IF NOT EXISTS idx_ecp_records_valid_until
    ON public.ecp_records USING btree (valid_until);

CREATE INDEX IF NOT EXISTS idx_ecp_records_wallet_status
    ON public.ecp_records USING btree (wallet_status);

COMMIT;
