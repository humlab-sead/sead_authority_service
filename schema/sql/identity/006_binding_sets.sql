-- SIMS: binding_sets
-- Atomic batch of identity resolution outcomes. The governance unit for lifecycle, audit,
-- and Change Request association (FR-26).
-- All Bindings within a set share the set's lifecycle — confirmed or rejected together.

create table sead_identity.binding_sets (
    binding_set_uuid uuid not null default gen_random_uuid(),
    submission_uuid uuid references sead_identity.submissions (submission_uuid),
    lifecycle_state text not null default 'proposed' check (lifecycle_state in ('proposed', 'confirmed', 'rejected', 'superseded', 'invalidated')),
    change_request_name text,
    created_at timestamptz not null default now(),
    created_by text,
    confirmed_at timestamptz,

    constraint binding_sets_pkey primary key (binding_set_uuid)
);

create index binding_sets_submission_idx on sead_identity.binding_sets (submission_uuid) where submission_uuid is not null;

create index binding_sets_change_request_idx on sead_identity.binding_sets (change_request_name) where change_request_name is not null;

comment on table sead_identity.binding_sets is
'Atomic batch of Bindings. Owns lifecycle state, audit trail, and Change Request reference. '
'All Bindings within a set are confirmed or rejected together (FR-26). '
'change_request_name references a Sqitch change in the SEAD Change Control System (FR-27).';
