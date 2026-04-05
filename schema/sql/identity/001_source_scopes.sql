-- SIMS: source_scopes
-- Represents the external namespace within which Source Identities are unique.
-- Hierarchical: a scope may have a parent scope (system → provider → dataset).

create table sead_identity.source_scopes (
    scope_uuid uuid not null default gen_random_uuid(),
    scope_name text not null,
    parent_scope_uuid uuid references sead_identity.source_scopes (scope_uuid),
    description text,
    created_at timestamptz not null default now(),
    created_by text,

    constraint source_scopes_pkey primary key (scope_uuid),
    constraint source_scopes_name_unique unique (scope_name)
);

comment on table sead_identity.source_scopes is
'External namespace within which Source Identities are unique. '
'Hierarchical via parent_scope_uuid (system → provider → dataset).';
