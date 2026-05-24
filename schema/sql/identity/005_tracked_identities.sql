-- SIMS: tracked_identities
-- The SEAD-side identity anchor for a domain entity.
-- Owns the SEAD universal UUID (FR-1) and the optional integer PK (FR-2).
-- Carries content_hash for aggregate-level change detection (FR-24).

create table sead_identity.tracked_identities (
    tracked_identity_uuid uuid not null default gen_random_uuid(),
    entity_type text not null,
    sead_internal_id bigint,
    content_hash text,
    lifecycle_state text not null default 'allocated'
    check (lifecycle_state in ('allocated', 'pending_materialization', 'materialized', 'invalidated')),
    created_at timestamptz not null default now(),
    created_by text,
    materialized_at timestamptz,

    constraint tracked_identities_pkey primary key (tracked_identity_uuid)
);

create index tracked_identities_entity_type_idx
on sead_identity.tracked_identities (entity_type);

create index tracked_identities_sead_internal_id_idx
on sead_identity.tracked_identities (entity_type, sead_internal_id)
where sead_internal_id is not null;

comment on table sead_identity.tracked_identities is
'SEAD-side identity anchor. tracked_identity_uuid IS the SEAD universal identity (FR-1). '
'sead_internal_id maps to the relational PK once materialized (FR-2). '
'content_hash supports aggregate-level change detection (FR-24).';

comment on column sead_identity.tracked_identities.content_hash is
'Opaque aggregate content hash computed by the submitting system (Shape Shifter). '
'SIMS stores and compares; does not compute. Hash determinism is the submitting system''s responsibility.';
