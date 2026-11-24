-- SIMS: scope_entity_contracts
-- Registered business-key contract for one entity type within a provider scope.
--
-- The ordered key list is the identity contract that consumers (for example
-- Shape Shifter) must use when they build the business identity value sent to
-- SIMS. Registration is idempotent: an exact ordered match is accepted, and a
-- different ordered list is rejected without partial writes.
--
-- Only provider scopes (for example 'provider://<code>/<schema>') use these
-- contracts. Internal scopes such as 'sead://admin', 'sead://migration', and
-- 'sead://reconciliation' are not required to register one.

create table sead_identity.scope_entity_contracts (
    contract_uuid uuid not null default gen_random_uuid(),
    scope_uuid uuid not null references sead_identity.source_scopes (scope_uuid),
    entity_type text not null,
    business_keys text[] not null,
    created_at timestamptz not null default now(),
    created_by text,

    constraint scope_entity_contracts_pkey primary key (contract_uuid),
    constraint scope_entity_contracts_unique unique (scope_uuid, entity_type),
    constraint scope_entity_contracts_keys_not_empty check (cardinality(business_keys) > 0)
);

create index scope_entity_contracts_scope_idx
on sead_identity.scope_entity_contracts (scope_uuid);

comment on table sead_identity.scope_entity_contracts is
'Registered business-key contract for one entity type within a provider scope. '
'business_keys stores the ordered key names used to build the business identity '
'value. One contract per (scope, entity type). Registration accepts an exact '
'ordered match and rejects a different ordered list.';
