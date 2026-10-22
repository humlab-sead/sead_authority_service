# Issue Draft: Add `ResolutionOutcome.target_id` to `POST /identity/resolve`

Suggested title:

`add optional target_id to resolution outcomes for change-request materialization`

Suggested body:

## Problem

Shape Shifter's `sead_change_request` Delivery 1 flow needs the SIMS-issued aggregate identity value when generating artifacts for tracked entities. `POST /identity/resolve` currently does not return that value for all configured allocation operations.

Current downstream behavior is explicit: when SIMS does not return a required aggregate identity value, Shape Shifter stops before artifact generation with `SIMS target ID allocation capability incomplete`.

## Solution

Extend each `ResolutionOutcome` in `POST /identity/resolve` so it may include the current adapter field:

```json
{
  "target_id": 12345
}
```

Requirements:

- field name: `target_id`
- type: `int | null`
- meaning: the opaque, entity-scoped aggregate identity value issued by SIMS; Shape Shifter may translate it according to its target model
- rollout: keep the field optional so existing clients remain compatible
- ownership: SIMS allocates the value through generic code driven by validated entity configuration and guarantees uniqueness within its own identity store; it does not inspect or enforce SEAD schema or database constraints

Expected behavior:

- return `target_id` when SIMS can match an existing entity to its stored aggregate identity value
- return `target_id` when SIMS allocates a new entity using the generic configured mechanism
- for an enabled allocation operation, fail rather than return a successful outcome with a null ID
- use the same allocator implementation for configured entity types; entity types are not hard-coded allocator branches

## Files

Relevant downstream references in Shape Shifter:

- `humlab-sead/sead_shape_shifter:docs/proposals/CHANGE_REQUEST_INGESTER/SEAD_CHANGE_REQUEST_INGESTER.md`
- `humlab-sead/sead_shape_shifter:backend/app/models/sims.py`
- `humlab-sead/sead_shape_shifter:backend/app/services/ingester_runtime.py`
- `humlab-sead/sead_shape_shifter:ingesters/sead_change_request/orchestration.py`

Related authority-service handoff note:

- [SIMS_TARGET_ID_CONTRACT.md](./SIMS_TARGET_ID_CONTRACT.md)

Suggested acceptance criteria:

- `POST /identity/resolve` may return `target_id` on each `ResolutionOutcome`
- the field is documented as the opaque SIMS-issued aggregate identity value carried through the current adapter field
- existing clients remain compatible if they ignore the field
- configured types use generic allocation and SIMS-store uniqueness
- Shape Shifter receives non-null `target_id` values for configured allocation or binding operations that require the value
- the work does not include existing-data migration, production validation, deployment, or cutover