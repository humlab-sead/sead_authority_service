# PR Draft: Add `ResolutionOutcome.target_id` to `POST /identity/resolve`

Suggested title:

`feat(identity): add optional target_id to resolution outcomes`

Suggested description:

## Summary

This change extends `POST /identity/resolve` so each `ResolutionOutcome` may include optional `target_id: int | null`.

The field carries the opaque, entity-scoped aggregate identity value issued by SIMS. Its integer representation is unchanged for the current Shape Shifter response model; Shape Shifter interprets the value using its target model.

## Problem

Shape Shifter can already:

- resolve identities through SIMS
- confirm Binding Sets
- associate change request names with confirmed Binding Sets

But it cannot complete artifact generation for configured tracked-entity operations when SIMS does not return the aggregate identity value.

Current downstream behavior is explicit: Shape Shifter stops before artifact generation with `SIMS target ID allocation capability incomplete` when a required SIMS-issued aggregate identity value is missing.

## Solution

Add optional `target_id` to each `ResolutionOutcome` returned by `POST /identity/resolve`.

SIMS owns tracked identities and is the sole minter of entity-scoped aggregate identity values. A generic allocator uses validated entity configuration and guarantees uniqueness within the SIMS identity store. SIMS does not inspect SEAD tables, columns, sequences, or database constraints. The site allocator is a disposable prototype, not the target architecture.

Expected behavior:

- return non-null `target_id` when SIMS matches an existing identity with a stored aggregate identity value
- return non-null `target_id` when the generic configured allocator creates a new tracked identity
- for an enabled allocation operation, fail rather than return a successful outcome with a null ID
- use the same allocator implementation across configured entity types
- keep the field optional so existing clients remain compatible
- exclude existing-data migration, production validation, deployment, and cutover from this development task

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