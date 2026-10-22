-- SIMS: submissions
-- Represents a delivered batch or ingest event within a single Source Scope.
-- Temporal provenance anchor for all Source Identities observed in a delivery.

create table sead_identity.submissions (
    submission_uuid uuid not null default gen_random_uuid(),
    scope_uuid uuid not null references sead_identity.source_scopes (scope_uuid),
    submission_name text not null,
    status text not null default 'pending' check (status in ('pending', 'completed', 'failed')),
    created_at timestamptz not null default now(),
    created_by text,
    completed_at timestamptz,

    constraint submissions_pkey primary key (submission_uuid)
);

create index submissions_scope_idx on sead_identity.submissions (scope_uuid);

comment on table sead_identity.submissions is
'A delivered batch or ingest event within a single Source Scope. '
'Groups all Source Identities observed in one delivery for traceability (FR-21, FR-22).';
