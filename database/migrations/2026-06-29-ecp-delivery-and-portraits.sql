-- Add eCP delivery assets and reusable member portrait metadata.
-- This is additive and safe for existing databases.

BEGIN;

ALTER TABLE public.ecp_records
    ADD COLUMN IF NOT EXISTS verification_url text,
    ADD COLUMN IF NOT EXISTS card_image_url text,
    ADD COLUMN IF NOT EXISTS card_pdf_url text,
    ADD COLUMN IF NOT EXISTS legal_document_url text;

ALTER TABLE public.members
    ADD COLUMN IF NOT EXISTS portrait_url text,
    ADD COLUMN IF NOT EXISTS portrait_hash character varying(64),
    ADD COLUMN IF NOT EXISTS portrait_face_detected boolean DEFAULT false NOT NULL,
    ADD COLUMN IF NOT EXISTS portrait_updated_at timestamp;

CREATE INDEX IF NOT EXISTS idx_members_portrait_hash
    ON public.members USING btree (portrait_hash);

COMMIT;
