-- Read access to the authority schema
--
-- This file must run after every schema object exists. `authority.sql` starts
-- with `drop schema if exists authority cascade`, so the schema and its objects
-- are recreated on every deployment and their privileges go with them. A grant
-- placed before the objects exist would either be dropped with the schema or
-- silently cover nothing, because `GRANT ... ON ALL ... IN SCHEMA` only affects
-- objects that already exist when it runs.
--
-- The `fuzzy_*` search functions are SECURITY INVOKER and read the entity
-- materialized views, so a caller needs all three of:
--   * USAGE on the schema     (without it every call fails with
--                              "permission denied for schema authority")
--   * EXECUTE on the routines (covers the `fuzzy_*` functions and procedures)
--   * SELECT on the views     (`ON ALL TABLES` includes materialized views)
--
-- Grantee: PUBLIC, so any role that can connect to the database may run the
-- read-only search. To restrict access, replace PUBLIC with the roles your
-- deployment uses, for example the role named by
-- SEAD_AUTHORITY_OPTIONS_DATABASE_USER.

grant usage on schema authority to public;

grant select on all tables in schema authority to public;
grant execute on all routines in schema authority to public;

-- Apply the same access to objects created after this file runs. Default
-- privileges are stored per owning role, so this covers later objects created by
-- the role that performs the deployment.

alter default privileges in schema authority grant select on tables to public;
alter default privileges in schema authority grant execute on routines to public;
