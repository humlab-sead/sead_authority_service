# Proposal: SIMS `target_id` Contract For Delivery 1

## Status

- Proposed change request
- Scope: `POST /identity/resolve` response contract
- Goal: Return target-facing SEAD integer IDs needed by Shape Shifter's `sead_change_request` Delivery 1 flow for PK/FK materialization

## Summary

Shape Shifter Delivery 1 is blocked on one upstream capability. The current SIMS resolve flow returns Binding Set metadata and tracked identity UUIDs, but not the target-facing integer ID that must appear in generated SQL.

The recommended change is small: extend each `ResolutionOutcome` in `POST /identity/resolve` so it may include `target_id: int | null`. Keep the field optional for rollout safety. Populate it whenever SIMS can resolve or allocate the authoritative SEAD integer ID for the requested entity.

This is the smallest change that closes the remaining Delivery 1 gap without redesigning Binding Sets, tracked identities, or the current resolve workflow.

## Problem

Shape Shifter's `sead_change_request` ingester must emit SQL containing target-facing SEAD integer IDs in primary-key and foreign-key columns.

Today the downstream runtime seam is ready to consume that field, but the authority-service contract does not provide it. That leaves Shape Shifter in an awkward state:

- SIMS can still create and confirm Binding Sets
- Shape Shifter can still associate a change request name with the Binding Set
- Shape Shifter cannot materialize new provider-owned rows into SQL because it does not know the integer IDs to emit

The current ingester therefore fails explicitly with `SIMS target ID allocation capability incomplete` when allocation succeeds at the Binding Set layer but no target-facing integer ID is returned.

## Scope

This proposal covers:

- the `POST /identity/resolve` response contract in `sead_authority_service`
- the meaning of the new `target_id` field
- rollout expectations for backward compatibility
- validation expectations from the Shape Shifter side

## Non-Goals

- redesigning the Binding Set model
- changing the meaning of tracked identity UUIDs
- adding new endpoints to SIMS
- solving Delivery 2 change detection or rollback concerns
- defining how every entity type should allocate internally inside SIMS

## Current Behavior

Current downstream behavior in Shape Shifter:

- `humlab-sead/sead_shape_shifter:backend/app/models/sims.py` already accepts optional `ResolutionOutcome.target_id`
- `humlab-sead/sead_shape_shifter:backend/app/services/ingester_runtime.py` passes `target_id` through to the ingester when SIMS returns it
- `humlab-sead/sead_shape_shifter:ingesters/sead_change_request/orchestration.py` treats missing `target_id` as a Delivery 1 hard stop for rows that require SIMS allocation

That means Shape Shifter is already forward-compatible with the proposed upstream change.

## Proposed Design

### API change

Extend each `ResolutionOutcome` returned by `POST /identity/resolve` with:

```json
{
  "target_id": 12345
}
```

Field contract:

- name: `target_id`
- type: integer or null
- semantics: the authoritative target-facing SEAD integer ID resolved or allocated for this entity
- presence: optional during rollout, expected when the entity is allocatable or resolvable to a target row for Delivery 1

### Behavior rules

- If SIMS matches an existing tracked identity that already has a target-facing SEAD integer ID, return that integer in `target_id`.
- If SIMS allocates a new entity and also allocates the authoritative target-facing SEAD integer ID needed for SQL materialization, return it in `target_id`.
- If SIMS can create the Binding Set outcome but cannot yet produce the target-facing integer ID, return `null`.
- The absence of `target_id` must not change existing Binding Set or tracked-identity behavior.

### Backward compatibility

- Existing clients must continue to work if they ignore `target_id`.
- Shape Shifter will treat `target_id` as optional until the upstream service guarantees it for Delivery 1 entity types.
- During rollout, null is acceptable for non-Delivery-1 use cases, but it remains a blocking condition for Shape Shifter change-request generation.

## Risks And Tradeoffs

- Returning `target_id` makes the resolve response more coupled to the target system than the current tracked-identity-only contract.
- If different entity types reach target integer allocation through different internal paths, SIMS implementation complexity may rise.
- A partial rollout where only some entity types populate `target_id` is still useful, but Shape Shifter must keep failing explicitly for unsupported cases.

## Testing And Validation

Validation already present in Shape Shifter:

- runtime adapter tests cover both `target_id` present and `target_id` absent paths in `humlab-sead/sead_shape_shifter:backend/tests/ingesters/test_sead_change_request_runtime.py`
- ingester tests cover the explicit capability-gap failure when `target_id` is absent in `humlab-sead/sead_shape_shifter:backend/tests/ingesters/test_sead_change_request_ingester.py`

Validation expected in `sead_authority_service`:

- contract tests for `POST /identity/resolve` including `target_id`
- tests for matched and newly allocated outcomes
- tests proving old clients remain compatible when the field is added

## Acceptance Criteria

- `POST /identity/resolve` may return `target_id` on each `ResolutionOutcome`
- the field is documented as the target-facing SEAD integer ID
- Shape Shifter receives non-null `target_id` values for Delivery 1 allocatable entity types
- Shape Shifter no longer fails with `SIMS target ID allocation capability incomplete` for supported entity types
- existing SIMS clients remain compatible without code changes

## Recommended Delivery Order

1. Extend the authority-service response model with optional `target_id`.
2. Populate `target_id` for one Delivery 1 entity type end to end.
3. Validate Shape Shifter change-request generation against that entity type.
4. Expand coverage to the remaining Delivery 1 allocatable entity types.

## Final Recommendation

Implement the optional `ResolutionOutcome.target_id` field in `sead_authority_service` and populate it wherever SIMS can already determine the authoritative target-facing SEAD integer ID.

That is the smallest upstream change that unblocks full Delivery 1 materialization in Shape Shifter.