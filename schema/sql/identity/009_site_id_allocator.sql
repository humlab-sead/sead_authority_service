-- SIMS-owned integer ID allocation for explicitly enabled entity candidates.
-- Allocator rows are created by bootstrap only after existing IDs are loaded.

create table if not exists sead_identity.internal_id_allocators (
    entity_type text not null primary key,
    next_internal_id bigint not null check (next_internal_id > 0),
    initialized_at timestamptz not null default now(),
    initialized_by text
);

create unique index if not exists tracked_identities_entity_internal_id_unique_idx
on sead_identity.tracked_identities (entity_type, sead_internal_id)
where sead_internal_id is not null;

comment on table sead_identity.internal_id_allocators is
'SIMS-owned next-ID state. A row exists only after the entity type has been initialized from existing target IDs.';