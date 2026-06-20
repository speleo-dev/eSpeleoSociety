-- Adminer 5.4.2 PostgreSQL 14.13 dump
-- Source: schema excerpt sent by the project author on 2026-06-20.
-- Notes:
-- - This file is stored as a reference artifact for code/schema alignment.
-- - It is an Adminer export, not a tested restore migration.
-- - The pgcrypto function stubs below should normally be represented by
--   CREATE EXTENSION IF NOT EXISTS pgcrypto; in a restore/migration script.

CREATE DATABASE "eSpeleoSoc";
\connect "eSpeleoSoc";

DROP FUNCTION IF EXISTS "armor";;
CREATE FUNCTION "armor" (IN "1" bytea) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "armor";;
CREATE FUNCTION "armor" (IN "1" bytea, IN "2" ARRAY, IN "3" ARRAY) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "crypt";;
CREATE FUNCTION "crypt" (IN "1" text, IN "2" text) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "dearmor";;
CREATE FUNCTION "dearmor" (IN "1" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "decrypt";;
CREATE FUNCTION "decrypt" (IN "1" bytea, IN "2" bytea, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "decrypt_iv";;
CREATE FUNCTION "decrypt_iv" (IN "1" bytea, IN "2" bytea, IN "3" bytea, IN "4" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "digest";;
CREATE FUNCTION "digest" (IN "1" text, IN "2" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "digest";;
CREATE FUNCTION "digest" (IN "1" bytea, IN "2" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "encrypt";;
CREATE FUNCTION "encrypt" (IN "1" bytea, IN "2" bytea, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "encrypt_iv";;
CREATE FUNCTION "encrypt_iv" (IN "1" bytea, IN "2" bytea, IN "3" bytea, IN "4" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "gen_random_bytes";;
CREATE FUNCTION "gen_random_bytes" (IN "1" integer) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "gen_random_uuid";;
CREATE FUNCTION "gen_random_uuid" () RETURNS uuid LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "gen_salt";;
CREATE FUNCTION "gen_salt" (IN "1" text) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "gen_salt";;
CREATE FUNCTION "gen_salt" (IN "1" text, IN "2" integer) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "hmac";;
CREATE FUNCTION "hmac" (IN "1" text, IN "2" text, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "hmac";;
CREATE FUNCTION "hmac" (IN "1" bytea, IN "2" bytea, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_armor_headers";;
CREATE FUNCTION "pgp_armor_headers" (IN "1" text, OUT "key" text, OUT "value" text) RETURNS record LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_key_id";;
CREATE FUNCTION "pgp_key_id" (IN "1" bytea) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_decrypt";;
CREATE FUNCTION "pgp_pub_decrypt" (IN "1" bytea, IN "2" bytea) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_decrypt";;
CREATE FUNCTION "pgp_pub_decrypt" (IN "1" bytea, IN "2" bytea, IN "3" text) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_decrypt";;
CREATE FUNCTION "pgp_pub_decrypt" (IN "1" bytea, IN "2" bytea, IN "3" text, IN "4" text) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_decrypt_bytea";;
CREATE FUNCTION "pgp_pub_decrypt_bytea" (IN "1" bytea, IN "2" bytea) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_decrypt_bytea";;
CREATE FUNCTION "pgp_pub_decrypt_bytea" (IN "1" bytea, IN "2" bytea, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_decrypt_bytea";;
CREATE FUNCTION "pgp_pub_decrypt_bytea" (IN "1" bytea, IN "2" bytea, IN "3" text, IN "4" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_encrypt";;
CREATE FUNCTION "pgp_pub_encrypt" (IN "1" text, IN "2" bytea) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_encrypt";;
CREATE FUNCTION "pgp_pub_encrypt" (IN "1" text, IN "2" bytea, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_encrypt_bytea";;
CREATE FUNCTION "pgp_pub_encrypt_bytea" (IN "1" bytea, IN "2" bytea) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_pub_encrypt_bytea";;
CREATE FUNCTION "pgp_pub_encrypt_bytea" (IN "1" bytea, IN "2" bytea, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_sym_decrypt";;
CREATE FUNCTION "pgp_sym_decrypt" (IN "1" bytea, IN "2" text) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_sym_decrypt";;
CREATE FUNCTION "pgp_sym_decrypt" (IN "1" bytea, IN "2" text, IN "3" text) RETURNS text LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_sym_decrypt_bytea";;
CREATE FUNCTION "pgp_sym_decrypt_bytea" (IN "1" bytea, IN "2" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_sym_decrypt_bytea";;
CREATE FUNCTION "pgp_sym_decrypt_bytea" (IN "1" bytea, IN "2" text, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_sym_encrypt";;
CREATE FUNCTION "pgp_sym_encrypt" (IN "1" text, IN "2" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_sym_encrypt";;
CREATE FUNCTION "pgp_sym_encrypt" (IN "1" text, IN "2" text, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_sym_encrypt_bytea";;
CREATE FUNCTION "pgp_sym_encrypt_bytea" (IN "1" bytea, IN "2" text) RETURNS bytea LANGUAGE c AS '';

DROP FUNCTION IF EXISTS "pgp_sym_encrypt_bytea";;
CREATE FUNCTION "pgp_sym_encrypt_bytea" (IN "1" bytea, IN "2" text, IN "3" text) RETURNS bytea LANGUAGE c AS '';

DROP TABLE IF EXISTS "club_affiliations";
CREATE TABLE "public"."club_affiliations" (
    "member_id" integer NOT NULL,
    "club_id" integer NOT NULL,
    "is_primary_club" boolean DEFAULT false,
    CONSTRAINT "club_affiliations_pkey" PRIMARY KEY ("member_id", "club_id")
)
WITH (oids = false);


DROP TABLE IF EXISTS "clubs";
DROP SEQUENCE IF EXISTS "public".clubs_club_id_seq;
CREATE SEQUENCE "public".clubs_club_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."clubs" (
    "club_id" integer DEFAULT nextval('clubs_club_id_seq') NOT NULL,
    "club_name" character varying(255) NOT NULL,
    "phone" character varying(20) DEFAULT '',
    "email" character varying(255) DEFAULT '',
    "president_id" integer,
    "foundation_date" date,
    "logo_url" text,
    "street" character varying(255),
    "city" character varying(100),
    "zip_code" character varying(10),
    "country" character varying(100),
    CONSTRAINT "clubs_pkey" PRIMARY KEY ("club_id")
)
WITH (oids = false);

CREATE UNIQUE INDEX clubs_email_key ON public.clubs USING btree (email);


DROP TABLE IF EXISTS "db_logs";
DROP SEQUENCE IF EXISTS "public".db_logs_log_id_seq;
CREATE SEQUENCE "public".db_logs_log_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."db_logs" (
    "log_id" integer DEFAULT nextval('db_logs_log_id_seq') NOT NULL,
    "action" character varying(50),
    "table_name" character varying(50),
    "user_name" character varying(50),
    "details" text,
    "log_timestamp" timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "db_logs_pkey" PRIMARY KEY ("log_id")
)
WITH (oids = false);


DROP TABLE IF EXISTS "ecp_records";
DROP SEQUENCE IF EXISTS "public".ecp_records_ecp_record_id_seq;
CREATE SEQUENCE "public".ecp_records_ecp_record_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."ecp_records" (
    "ecp_record_id" integer DEFAULT nextval('ecp_records_ecp_record_id_seq') NOT NULL,
    "ecp_hash" character varying(64) NOT NULL,
    "gdpr_consent" boolean DEFAULT true NOT NULL,
    "notifications_enabled" boolean DEFAULT true NOT NULL,
    "photo_hash" text NOT NULL,
    "ecp_active" boolean DEFAULT false NOT NULL,
    "check_hash" character varying(64) NOT NULL,
    CONSTRAINT "ecp_records_pkey" PRIMARY KEY ("ecp_record_id")
)
WITH (oids = false);

CREATE UNIQUE INDEX ecp_records_ecp_hash_key ON public.ecp_records USING btree (ecp_hash);


DROP TABLE IF EXISTS "ecp_requests";
DROP SEQUENCE IF EXISTS "public".ecp_requests_request_id_seq;
CREATE SEQUENCE "public".ecp_requests_request_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."ecp_requests" (
    "request_id" integer DEFAULT nextval('ecp_requests_request_id_seq') NOT NULL,
    "member_id" integer NOT NULL,
    "status" character varying(20) DEFAULT 'pending' NOT NULL,
    "request_date" date NOT NULL,
    "ecp_record_id" integer,
    CONSTRAINT "ecp_requests_pkey" PRIMARY KEY ("request_id")
)
WITH (oids = false);


DROP TABLE IF EXISTS "ess_config";
CREATE TABLE "public"."ess_config" (
    "config_key" character varying(255) NOT NULL,
    "config_value" text,
    CONSTRAINT "ess_config_pkey" PRIMARY KEY ("config_key")
)
WITH (oids = false);


DROP TABLE IF EXISTS "member_certificates";
CREATE TABLE "public"."member_certificates" (
    "member_id" integer NOT NULL,
    "sequence_number" integer NOT NULL,
    "name" text NOT NULL,
    "issue_date" date,
    "valid_until" date,
    "url" text,
    CONSTRAINT "member_certificates_pkey" PRIMARY KEY ("member_id", "sequence_number")
)
WITH (oids = false);

CREATE INDEX idx_member_certificates_member_id ON public.member_certificates USING btree (member_id);


DROP TABLE IF EXISTS "members";
DROP SEQUENCE IF EXISTS "public".members_member_id_seq;
CREATE SEQUENCE "public".members_member_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."members" (
    "member_id" integer DEFAULT nextval('members_member_id_seq') NOT NULL,
    "first_name" character varying(100) NOT NULL,
    "last_name" character varying(100) NOT NULL,
    "birth_date_encrypted" text NOT NULL,
    "email" character varying(255) DEFAULT '',
    "phone" character varying(20) DEFAULT '',
    "ecp_hash" character varying(64),
    "member_status" character varying(20) DEFAULT 'applicant',
    "discounted_membership" boolean DEFAULT false,
    "title_prefix" character varying(50) DEFAULT '',
    "title_suffix" character varying(50) DEFAULT '',
    "street" character varying(255),
    "city" character varying(100),
    "zip_code" character varying(20),
    "country" character varying(100),
    "member_since" date,
    CONSTRAINT "members_pkey" PRIMARY KEY ("member_id"),
    CONSTRAINT "members_member_status_check" CHECK ((((member_status)::text = ANY ((ARRAY['applicant'::character varying, 'active'::character varying, 'inactive'::character varying, 'blocked'::character varying])::text[]))))
)
WITH (oids = false);

CREATE UNIQUE INDEX members_ecp_hash_key ON public.members USING btree (ecp_hash);


DROP TABLE IF EXISTS "membership_fees";
DROP SEQUENCE IF EXISTS "public".membership_fees_fee_id_seq;
CREATE SEQUENCE "public".membership_fees_fee_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."membership_fees" (
    "fee_id" integer DEFAULT nextval('membership_fees_fee_id_seq') NOT NULL,
    "member_id" integer NOT NULL,
    "ecp_hash" character varying(64),
    "year" integer NOT NULL,
    "fee_type" character varying(20) DEFAULT 'standard',
    CONSTRAINT "membership_fees_pkey" PRIMARY KEY ("fee_id")
)
WITH (oids = false);


DROP TABLE IF EXISTS "notifications";
DROP SEQUENCE IF EXISTS "public".notifications_notification_id_seq;
CREATE SEQUENCE "public".notifications_notification_id_seq INCREMENT 1 MINVALUE 1 MAXVALUE 2147483647 CACHE 1;

CREATE TABLE "public"."notifications" (
    "notification_id" integer DEFAULT nextval('notifications_notification_id_seq') NOT NULL,
    "created_at" timestamp NOT NULL,
    "text" text NOT NULL,
    "valid_from" timestamp NOT NULL,
    "valid_to" timestamp NOT NULL,
    "status" character varying(10) NOT NULL,
    CONSTRAINT "notifications_pkey" PRIMARY KEY ("notification_id")
)
WITH (oids = false);


ALTER TABLE ONLY "public"."club_affiliations" ADD CONSTRAINT "club_affiliations_club_id_fkey" FOREIGN KEY (club_id) REFERENCES clubs(club_id) ON DELETE CASCADE;
ALTER TABLE ONLY "public"."club_affiliations" ADD CONSTRAINT "club_affiliations_member_id_fkey" FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE;

ALTER TABLE ONLY "public"."clubs" ADD CONSTRAINT "clubs_president_id_fkey" FOREIGN KEY (president_id) REFERENCES members(member_id) ON DELETE SET NULL;

ALTER TABLE ONLY "public"."ecp_requests" ADD CONSTRAINT "ecp_requests_ecp_record_id_fkey" FOREIGN KEY (ecp_record_id) REFERENCES ecp_records(ecp_record_id) ON DELETE CASCADE;
ALTER TABLE ONLY "public"."ecp_requests" ADD CONSTRAINT "ecp_requests_member_id_fkey" FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE;

ALTER TABLE ONLY "public"."member_certificates" ADD CONSTRAINT "member_certificates_member_id_fkey" FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE;

ALTER TABLE ONLY "public"."membership_fees" ADD CONSTRAINT "membership_fees_ecp_hash_fkey" FOREIGN KEY (ecp_hash) REFERENCES ecp_records(ecp_hash) ON DELETE CASCADE;
ALTER TABLE ONLY "public"."membership_fees" ADD CONSTRAINT "membership_fees_member_id_fkey" FOREIGN KEY (member_id) REFERENCES members(member_id) ON DELETE CASCADE;

-- 2026-06-20 10:49:34 UTC
