-- eSpeleoSociety development/test schema bootstrap.
--
-- Source of truth: Adminer PostgreSQL 14.13 schema export sent by the project
-- author on 2026-06-20. This file is intentionally not a raw Adminer dump:
-- it omits database/session commands and Adminer-exported pgcrypto C function
-- stubs. Apply this only to a disposable local/test database.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS public.membership_fees CASCADE;
DROP TABLE IF EXISTS public.member_certificates CASCADE;
DROP TABLE IF EXISTS public.ecp_requests CASCADE;
DROP TABLE IF EXISTS public.club_affiliations CASCADE;
DROP TABLE IF EXISTS public.notifications CASCADE;
DROP TABLE IF EXISTS public.ess_config CASCADE;
DROP TABLE IF EXISTS public.db_logs CASCADE;
DROP TABLE IF EXISTS public.clubs CASCADE;
DROP TABLE IF EXISTS public.ecp_records CASCADE;
DROP TABLE IF EXISTS public.members CASCADE;

DROP SEQUENCE IF EXISTS public.clubs_club_id_seq;
DROP SEQUENCE IF EXISTS public.db_logs_log_id_seq;
DROP SEQUENCE IF EXISTS public.ecp_records_ecp_record_id_seq;
DROP SEQUENCE IF EXISTS public.ecp_requests_request_id_seq;
DROP SEQUENCE IF EXISTS public.members_member_id_seq;
DROP SEQUENCE IF EXISTS public.membership_fees_fee_id_seq;
DROP SEQUENCE IF EXISTS public.notifications_notification_id_seq;

CREATE SEQUENCE public.clubs_club_id_seq
    INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE SEQUENCE public.db_logs_log_id_seq
    INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE SEQUENCE public.ecp_records_ecp_record_id_seq
    INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE SEQUENCE public.ecp_requests_request_id_seq
    INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE SEQUENCE public.members_member_id_seq
    INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE SEQUENCE public.membership_fees_fee_id_seq
    INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE SEQUENCE public.notifications_notification_id_seq
    INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE IF NOT EXISTS public.members (
    member_id integer DEFAULT nextval('public.members_member_id_seq'::regclass) NOT NULL,
    first_name character varying(100) NOT NULL,
    last_name character varying(100) NOT NULL,
    birth_date_encrypted text NOT NULL,
    email character varying(255) DEFAULT '',
    phone character varying(20) DEFAULT '',
    ecp_hash character varying(64),
    member_status character varying(20) DEFAULT 'applicant',
    discounted_membership boolean DEFAULT false,
    title_prefix character varying(50) DEFAULT '',
    title_suffix character varying(50) DEFAULT '',
    street character varying(255),
    city character varying(100),
    zip_code character varying(20),
    country character varying(100),
    member_since date,
    CONSTRAINT members_pkey PRIMARY KEY (member_id),
    CONSTRAINT members_member_status_check
        CHECK ((member_status)::text = ANY ((ARRAY[
            'applicant'::character varying,
            'active'::character varying,
            'inactive'::character varying,
            'blocked'::character varying
        ])::text[]))
);

ALTER SEQUENCE public.members_member_id_seq OWNED BY public.members.member_id;

CREATE UNIQUE INDEX members_ecp_hash_key
    ON public.members USING btree (ecp_hash);

CREATE TABLE IF NOT EXISTS public.clubs (
    club_id integer DEFAULT nextval('public.clubs_club_id_seq'::regclass) NOT NULL,
    club_name character varying(255) NOT NULL,
    phone character varying(20) DEFAULT '',
    email character varying(255) DEFAULT '',
    president_id integer,
    foundation_date date,
    logo_url text,
    street character varying(255),
    city character varying(100),
    zip_code character varying(10),
    country character varying(100),
    CONSTRAINT clubs_pkey PRIMARY KEY (club_id)
);

ALTER SEQUENCE public.clubs_club_id_seq OWNED BY public.clubs.club_id;

CREATE UNIQUE INDEX clubs_email_key
    ON public.clubs USING btree (email);

CREATE TABLE IF NOT EXISTS public.club_affiliations (
    member_id integer NOT NULL,
    club_id integer NOT NULL,
    is_primary_club boolean DEFAULT false,
    CONSTRAINT club_affiliations_pkey PRIMARY KEY (member_id, club_id)
);

CREATE TABLE IF NOT EXISTS public.db_logs (
    log_id integer DEFAULT nextval('public.db_logs_log_id_seq'::regclass) NOT NULL,
    action character varying(50),
    table_name character varying(50),
    user_name character varying(50),
    details text,
    log_timestamp timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT db_logs_pkey PRIMARY KEY (log_id)
);

ALTER SEQUENCE public.db_logs_log_id_seq OWNED BY public.db_logs.log_id;

CREATE TABLE IF NOT EXISTS public.ecp_records (
    ecp_record_id integer DEFAULT nextval('public.ecp_records_ecp_record_id_seq'::regclass) NOT NULL,
    ecp_hash character varying(64) NOT NULL,
    gdpr_consent boolean DEFAULT true NOT NULL,
    notifications_enabled boolean DEFAULT true NOT NULL,
    photo_hash text NOT NULL,
    ecp_active boolean DEFAULT false NOT NULL,
    check_hash character varying(64) NOT NULL,
    qr_url text,
    qr_key_id character varying(100),
    qr_payload jsonb,
    qr_payload_hash character varying(64),
    issued_at timestamp,
    valid_until date,
    wallet_status character varying(30) DEFAULT 'not_issued',
    wallet_object_id text,
    wallet_last_error text,
    CONSTRAINT ecp_records_pkey PRIMARY KEY (ecp_record_id)
);

ALTER SEQUENCE public.ecp_records_ecp_record_id_seq OWNED BY public.ecp_records.ecp_record_id;

CREATE UNIQUE INDEX ecp_records_ecp_hash_key
    ON public.ecp_records USING btree (ecp_hash);

CREATE INDEX idx_ecp_records_valid_until
    ON public.ecp_records USING btree (valid_until);

CREATE INDEX idx_ecp_records_wallet_status
    ON public.ecp_records USING btree (wallet_status);

CREATE TABLE IF NOT EXISTS public.ecp_requests (
    request_id integer DEFAULT nextval('public.ecp_requests_request_id_seq'::regclass) NOT NULL,
    member_id integer NOT NULL,
    status character varying(20) DEFAULT 'pending' NOT NULL,
    request_date date NOT NULL,
    ecp_record_id integer,
    CONSTRAINT ecp_requests_pkey PRIMARY KEY (request_id)
);

ALTER SEQUENCE public.ecp_requests_request_id_seq OWNED BY public.ecp_requests.request_id;

CREATE TABLE IF NOT EXISTS public.ess_config (
    config_key character varying(255) NOT NULL,
    config_value text,
    CONSTRAINT ess_config_pkey PRIMARY KEY (config_key)
);

CREATE TABLE IF NOT EXISTS public.member_certificates (
    member_id integer NOT NULL,
    sequence_number integer NOT NULL,
    name text NOT NULL,
    issue_date date,
    valid_until date,
    url text,
    CONSTRAINT member_certificates_pkey PRIMARY KEY (member_id, sequence_number)
);

CREATE INDEX idx_member_certificates_member_id
    ON public.member_certificates USING btree (member_id);

CREATE TABLE IF NOT EXISTS public.membership_fees (
    fee_id integer DEFAULT nextval('public.membership_fees_fee_id_seq'::regclass) NOT NULL,
    member_id integer NOT NULL,
    ecp_hash character varying(64),
    year integer NOT NULL,
    fee_type character varying(20) DEFAULT 'standard',
    CONSTRAINT membership_fees_pkey PRIMARY KEY (fee_id)
);

ALTER SEQUENCE public.membership_fees_fee_id_seq OWNED BY public.membership_fees.fee_id;

CREATE TABLE IF NOT EXISTS public.notifications (
    notification_id integer DEFAULT nextval('public.notifications_notification_id_seq'::regclass) NOT NULL,
    created_at timestamp NOT NULL,
    text text NOT NULL,
    valid_from timestamp NOT NULL,
    valid_to timestamp NOT NULL,
    status character varying(10) NOT NULL,
    CONSTRAINT notifications_pkey PRIMARY KEY (notification_id)
);

ALTER SEQUENCE public.notifications_notification_id_seq OWNED BY public.notifications.notification_id;

ALTER TABLE ONLY public.club_affiliations
    ADD CONSTRAINT club_affiliations_club_id_fkey
    FOREIGN KEY (club_id) REFERENCES public.clubs(club_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.club_affiliations
    ADD CONSTRAINT club_affiliations_member_id_fkey
    FOREIGN KEY (member_id) REFERENCES public.members(member_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.clubs
    ADD CONSTRAINT clubs_president_id_fkey
    FOREIGN KEY (president_id) REFERENCES public.members(member_id) ON DELETE SET NULL;

ALTER TABLE ONLY public.ecp_requests
    ADD CONSTRAINT ecp_requests_ecp_record_id_fkey
    FOREIGN KEY (ecp_record_id) REFERENCES public.ecp_records(ecp_record_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.ecp_requests
    ADD CONSTRAINT ecp_requests_member_id_fkey
    FOREIGN KEY (member_id) REFERENCES public.members(member_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.member_certificates
    ADD CONSTRAINT member_certificates_member_id_fkey
    FOREIGN KEY (member_id) REFERENCES public.members(member_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.membership_fees
    ADD CONSTRAINT membership_fees_ecp_hash_fkey
    FOREIGN KEY (ecp_hash) REFERENCES public.ecp_records(ecp_hash) ON DELETE CASCADE;

ALTER TABLE ONLY public.membership_fees
    ADD CONSTRAINT membership_fees_member_id_fkey
    FOREIGN KEY (member_id) REFERENCES public.members(member_id) ON DELETE CASCADE;

COMMIT;
