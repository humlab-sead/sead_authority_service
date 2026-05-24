# Issue Draft: Add `ResolutionOutcome.target_id` to `POST /identity/resolve`

Suggested title:

`add optional target_id to resolution outcomes for change-request materialization`

Suggested body:

## Problem

Shape Shifter's `sead_change_request` Delivery 1 flow can resolve and confirm SIMS Binding Sets, but it still cannot materialize new provider-owned rows into SQL because `POST /identity/resolve` does not return the target-facing SEAD integer ID needed in emitted PK/FK columns.

Current downstream behavior is explicit: when SIMS returns Binding Set metadata without a target-facing integer ID, Shape Shifter stops before SQL generation with `SIMS target ID allocation capability incomplete`.

## Solution

Extend each `ResolutionOutcome` in `POST /identity/resolve` so it may include:

```json
{
  "target_id": 12345
}
```

Requirements:

- field name: `target_id`
- type: `int | null`
- meaning: the authoritative target-facing SEAD integer ID resolved or allocated for that entity
- rollout: keep the field optional so existing clients remain compatible

Expected behavior:

- return `target_id` when SIMS can match an existing entity to its target-facing integer ID
- return `target_id` when SIMS allocates a new entity and knows the integer ID Shape Shifter must emit
- return `null` only when Binding Set creation succeeds but integer-ID materialization is still unavailable

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
- the field is documented as the target-facing SEAD integer ID
- existing clients remain compatible if they ignore the field
- Shape Shifter receives non-null `target_id` values for Delivery 1 allocatable entity types