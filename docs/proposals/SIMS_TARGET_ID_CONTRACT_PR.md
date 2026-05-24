# PR Draft: Add `ResolutionOutcome.target_id` to `POST /identity/resolve`

Suggested title:

`feat(identity): add optional target_id to resolution outcomes`

Suggested description:

## Summary

This change extends `POST /identity/resolve` so each `ResolutionOutcome` may include optional `target_id: int | null`.

The field represents the authoritative target-facing SEAD integer ID resolved or allocated for that entity. It is needed by Shape Shifter's `sead_change_request` Delivery 1 flow to materialize PK/FK values into generated SQL.

## Problem

Shape Shifter can already:

- resolve identities through SIMS
- confirm Binding Sets
- associate change request names with confirmed Binding Sets

But it still cannot complete Delivery 1 SQL generation for newly allocated provider-owned rows when SIMS does not return the target-facing integer ID that must appear in emitted SQL columns.

Current downstream behavior is explicit: Shape Shifter stops before SQL generation with `SIMS target ID allocation capability incomplete` when `target_id` is missing.

## Solution

Add optional `target_id` to each `ResolutionOutcome` returned by `POST /identity/resolve`.

Expected behavior:

- return non-null `target_id` when SIMS matches an existing entity that already has the authoritative SEAD integer ID
- return non-null `target_id` when SIMS allocates a new entity and knows the integer ID Shape Shifter must emit
- return `null` only when Binding Set creation succeeds but integer-ID materialization is still unavailable
- keep the field optional so existing clients remain compatible

## Validation

Downstream Shape Shifter support is already in place:

- `ResolutionOutcome.target_id` is accepted by the local client DTO
- the runtime adapter passes `target_id` through when present
- tests cover both `target_id` present and absent cases

Relevant downstream references:

- [SIMS_TARGET_ID_CONTRACT.md](./SIMS_TARGET_ID_CONTRACT.md)
- [SIMS_TARGET_ID_CONTRACT_ISSUE.md](./SIMS_TARGET_ID_CONTRACT_ISSUE.md)
- `humlab-sead/sead_shape_shifter:backend/app/models/sims.py`
- `humlab-sead/sead_shape_shifter:backend/app/services/ingester_runtime.py`

## Files

Suggested upstream change areas in `sead_authority_service`:

- identity response model defining `ResolutionOutcome`
- `POST /identity/resolve` response serialization
- tests for matched and newly allocated outcomes
- contract or API documentation for the optional `target_id` field