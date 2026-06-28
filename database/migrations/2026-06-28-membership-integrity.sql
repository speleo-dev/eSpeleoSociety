-- Tighten club membership and fee integrity.
--
-- Keeps at most one primary club per member and one fee row per
-- member/year/fee_type. Existing duplicate rows are collapsed before indexes
-- are created so the migration can run on current data.

WITH ranked_primary AS (
    SELECT
        member_id,
        club_id,
        ROW_NUMBER() OVER (PARTITION BY member_id ORDER BY club_id) AS row_number
    FROM public.club_affiliations
    WHERE is_primary_club IS TRUE
)
UPDATE public.club_affiliations AS club_affiliations
SET is_primary_club = FALSE
FROM ranked_primary
WHERE club_affiliations.member_id = ranked_primary.member_id
  AND club_affiliations.club_id = ranked_primary.club_id
  AND ranked_primary.row_number > 1;

DELETE FROM public.membership_fees AS membership_fees
USING (
    SELECT
        fee_id,
        ROW_NUMBER() OVER (
            PARTITION BY member_id, year, fee_type
            ORDER BY fee_id
        ) AS row_number
    FROM public.membership_fees
) AS ranked_fees
WHERE membership_fees.fee_id = ranked_fees.fee_id
  AND ranked_fees.row_number > 1;

CREATE UNIQUE INDEX IF NOT EXISTS idx_club_affiliations_one_primary
    ON public.club_affiliations USING btree (member_id)
    WHERE is_primary_club;

CREATE INDEX IF NOT EXISTS idx_club_affiliations_club_id
    ON public.club_affiliations USING btree (club_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_membership_fees_member_year_type
    ON public.membership_fees USING btree (member_id, year, fee_type);
