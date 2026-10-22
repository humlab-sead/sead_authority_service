-- SIMS Identity Schema
-- Creates the sead_identity schema and required PostgreSQL extensions.
-- Decision D1: sead_identity schema (separate from authority/reconciliation).
-- Decision D2: gen_random_uuid() for UUID generation (PostgreSQL-side).

create schema if not exists sead_identity;

create extension if not exists pgcrypto;  -- provides gen_random_uuid()
