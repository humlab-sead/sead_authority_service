-- SIMS: source_identities
-- Persistent identity for a domain entity as expressed within a Source Scope.
-- Carries all identity signals supplied by the provider.
-- Uniqueness enforced per (scope, entity_type, identity_type, identity_value) — supports idempotency (FR-12, FR-13).

create table sead_identity.source_identities (
    source_identity_uuid uuid        not null default gen_random_uuid(),
    scope_uuid           uuid        not null references sead_identity.source_scopes (scope_uuid),
    entity_type          text        not null,
    identity_type        text        not null
                                     check (identity_type in ('uuid', 'business_key', 'provider_key', 'authority_key')),
    identity_value       text        not null,
    identity_signals     jsonb,
    created_at           timestamptz not null default now(),
    created_by           text,

    constraint source_identities_pkey primary key (source_identity_uuid),
    constraint source_identities_unique
        unique (scope_uuid, entity_type, identity_type, identity_value)
);

create index source_identities_scope_entity_idx
    on sead_identity.source_identities (scope_uuid, entity_type);

comment on table sead_identity.source_identities is
    'Persistent identity for a domain entity as expressed within a Source Scope. '
    'Carries identity signals (UUID, business key, provider key, authority key). '
    'Unique per (scope, entity_type, identity_type, identity_value) for idempotency (FR-12, FR-13).';

comment on column sead_identity.source_identities.identity_signals is
    'Additional identity evidence as JSONB: authority keys, alternative identifiers, '
    'reconciliation hints. Opaque to SIMS; interpreted by resolution strategy.';
