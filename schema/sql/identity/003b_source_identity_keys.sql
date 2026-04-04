-- SIMS: source_identity_keys
-- Identity evidence for a Source Identity — one row per key type per source identity.
-- Allows a provider to supply multiple key types (UUID + business key + provider key)
-- for the same entity. SIMS resolution tries each key in turn.
--
-- Uniqueness: (source_identity_uuid, key_type) — one value per key type per identity.
-- Lookup index: (key_type, key_value) enables efficient reverse-lookup by key.

create table sead_identity.source_identity_keys (
    key_uuid             uuid not null default gen_random_uuid(),
    source_identity_uuid uuid not null
                              references sead_identity.source_identities (source_identity_uuid),
    key_type             text not null
                              check (key_type in ('uuid', 'business_key', 'provider_key', 'authority_key')),
    key_value            text not null,

    constraint source_identity_keys_pkey
        primary key (key_uuid),
    constraint source_identity_keys_type_unique
        unique (source_identity_uuid, key_type)
);

create index source_identity_keys_source_idx
    on sead_identity.source_identity_keys (source_identity_uuid);

create index source_identity_keys_lookup_idx
    on sead_identity.source_identity_keys (key_type, key_value);

comment on table sead_identity.source_identity_keys is
    'Identity evidence for a Source Identity. Each row is one key (uuid, business_key, '
    'provider_key, or authority_key). A source identity may carry multiple key types — '
    'e.g. both a provider UUID and a business key — enabling multi-signal resolution. '
    'Uniqueness is enforced per (source_identity_uuid, key_type).';
