-- Expand club directory contact support.
--
-- The public SSS club directory can contain multiple phone numbers,
-- multiple emails, and one or more web pages per club. It also names
-- the club president as public text, while the application keeps
-- clubs.president_id as an optional FK to a real member record.

BEGIN;

ALTER TABLE public.clubs
    ALTER COLUMN phone TYPE text,
    ALTER COLUMN email TYPE text,
    ADD COLUMN IF NOT EXISTS webpage text DEFAULT '',
    ADD COLUMN IF NOT EXISTS president_name_text text DEFAULT '';

ALTER TABLE public.members
    ALTER COLUMN phone TYPE text,
    ALTER COLUMN email TYPE text,
    ALTER COLUMN birth_date_encrypted DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS is_directory_stub boolean DEFAULT false NOT NULL;

ALTER TABLE public.club_affiliations
    ADD COLUMN IF NOT EXISTS role character varying(30) DEFAULT 'member' NOT NULL;

UPDATE public.club_affiliations AS club_affiliations
SET role = 'president'
FROM public.clubs AS clubs
WHERE clubs.club_id = club_affiliations.club_id
  AND clubs.president_id = club_affiliations.member_id;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'club_affiliations_role_check'
    ) THEN
        ALTER TABLE public.club_affiliations
            ADD CONSTRAINT club_affiliations_role_check
            CHECK ((role)::text = ANY ((ARRAY[
                'member'::character varying,
                'president'::character varying
            ])::text[]));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_club_affiliations_role
    ON public.club_affiliations USING btree (role);

COMMIT;
