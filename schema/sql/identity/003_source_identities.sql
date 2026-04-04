-- SIMS: source_identities
-- Header record representing a provider's claim about one domain entity within a Source Scope.
-- Identity evidence (keys) are stored in source_identity_keys (see 003b).
-- Idempotency (FR-12, FR-13) is enforced at the key level: before inserting a new header,
-- the repository looks up whether any of the submitted keys already exist.

create table sead_identity.source_identities (
    source_identity_uuid uuid        not null default gen_random_uuid(),
    scope_uuid           uuid        not null references sead_identity.source_scopes (scope_uuid),
    entity_type          text        not null,
    created_at           timestamptz not null default now(),
    created_by           text,

    constraint source_identities_pkey primary key (source_identity_uuid)
);

create index source_identities_scope_entity_idx
    on sead_identity.source_identities (scope_uuid, entity_type);

comment on table sead_identity.source_identities is
    'Header record for a provider entity identity within a Source Scope. '
    'A source identity groups all key evidence (UUID, business key, provider key, authority key) '
    'for one provider entity. Keys live in source_identity_keys (one-to-many).';

