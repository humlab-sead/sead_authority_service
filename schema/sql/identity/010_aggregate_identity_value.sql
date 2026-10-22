-- Replace the legacy target-table key name with SIMS aggregate identity terminology.

alter table sead_identity.tracked_identities
    rename column sead_internal_id to aggregate_id;

alter index if exists sead_identity.tracked_identities_sead_internal_id_idx
    rename to tracked_identities_entity_aggregate_id_idx;

alter index if exists sead_identity.tracked_identities_entity_internal_id_unique_idx
    rename to tracked_identities_entity_aggregate_id_unique_idx;

comment on table sead_identity.tracked_identities is
'SIMS-owned identities for tracked aggregates. SIMS mints entity-scoped aggregate IDs and tracked UUIDs; consumers interpret aggregate IDs using their own data models.';

comment on column sead_identity.tracked_identities.aggregate_id is
'SIMS-minted, entity-scoped aggregate identity value. It does not identify a consumer table or column.';
