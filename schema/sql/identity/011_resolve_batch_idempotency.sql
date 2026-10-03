-- SIMS: resolve_batches
-- Idempotency record for one scoped resolve run.

create table sead_identity.resolve_batches (
    scope_name text not null,
    run_id text not null,
    request_fingerprint text not null,
    result jsonb not null,
    created_at timestamptz not null default now(),

    constraint resolve_batches_pkey primary key (scope_name, run_id)
);

comment on table sead_identity.resolve_batches is
'One completed resolve batch per scoped run key. The result JSONB stores the full response for exact replay. Reusing a run key with a different request fingerprint is a client conflict.';
