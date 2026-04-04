-- SIMS: bindings
-- One source-to-tracked identity correspondence within a Binding Set.
-- A Source Identity normally has at most one Binding in a current confirmed Binding Set.

create table sead_identity.bindings (
    binding_uuid          uuid  not null default gen_random_uuid(),
    binding_set_uuid      uuid  not null references sead_identity.binding_sets (binding_set_uuid),
    source_identity_uuid  uuid  not null references sead_identity.source_identities (source_identity_uuid),
    tracked_identity_uuid uuid  not null references sead_identity.tracked_identities (tracked_identity_uuid),
    method                text  not null
                                check (method in (
                                    'exact_match',
                                    'business_key',
                                    'uuid_accepted',
                                    'uuid_mapped',
                                    'manual',
                                    'allocated'
                                )),
    provenance            jsonb,

    constraint bindings_pkey primary key (binding_uuid),
    constraint bindings_set_source_unique
        unique (binding_set_uuid, source_identity_uuid)
);

create index bindings_source_identity_idx
    on sead_identity.bindings (source_identity_uuid);

create index bindings_tracked_identity_idx
    on sead_identity.bindings (tracked_identity_uuid);

comment on table sead_identity.bindings is
    'One source-to-tracked identity correspondence within a Binding Set. '
    'method records how the binding was established. '
    'provenance (JSONB) carries supporting evidence and resolution context.';

comment on column sead_identity.bindings.method is
    'How the binding was established: '
    'exact_match = identity_value matched directly; '
    'business_key = matched via serialized business key; '
    'uuid_accepted = provider UUID accepted as SEAD identity (FR-11); '
    'uuid_mapped = provider UUID retained as provider key, SEAD UUID allocated; '
    'manual = human review; '
    'allocated = no match found, new Tracked Identity minted.';
