# Proposal: SIMS `target_id` Contract For Delivery 1

## Status

- The generic allocation path is implemented in the current candidate. Production adoption, existing-data migration, and cutover remain separate operational work.
- Scope: `POST /identity/resolve` request and response contract
- Goal: Return SIMS-issued aggregate identity values through the current Shape Shifter response boundary

## Summary

SIMS owns tracked aggregate identities and is the sole minter of their entity-scoped identity values. Its generic allocation mechanism is configured by entity type, stores the identity value and tracked UUID, and guarantees uniqueness within the SIMS identity store. SEAD consumes the returned value under the SIMS–SEAD trust contract. SIMS does not inspect SEAD, map identities to SEAD tables or columns, or guarantee SEAD database integrity.

The current `ResolutionOutcome.target_id` field is the Shape Shifter adapter's response name for the SIMS-issued value. The disposable `site` and `sample` paths are evidence for the current candidate implementation, not a requirement for entity-specific allocation code or a limit on the generic mechanism.

Production migration, operational adoption, deployment, and cutover are outside the current development task.

## Approved Identity-Allocation Decision

For a new tracked aggregate, SIMS allocates and persists its entity-scoped aggregate identity value and tracked UUID. SIMS uses a generic mechanism driven by validated configuration and guarantees uniqueness within its own identity store. It also stores scoped source identities and their associations with the tracked aggregate.

The initial prototype used `sead_identity.internal_id_allocators` and a SEAD-specific `sead_internal_id` column. The current tracked-identity record uses `aggregate_id`; the old column is renamed by an additive SQL migration. SIMS must not depend on consumer tables, columns, sequences, or constraints. The trust contract requires every tracked entity represented in SEAD to have a corresponding SIMS identity; establishing this for existing production data is separate operational work.

## Problem

Shape Shifter's `sead_change_request` ingester must receive identity values for tracked aggregates and use them when generating target artifacts. SIMS currently exposes a `target_id` response field, but its generic identity mechanism must not depend on SEAD's schema or table-key model.

The site allocator and response path are implemented as a prototype, but they are not the generic configurable design. Remaining development gaps include:

- generic entity-scoped configuration and allocation
- enforcing uniqueness within SIMS for generic allocations
- capability reporting and end-to-end Shape Shifter consumption of the generic response

Shape Shifter must fail explicitly when a configured SIMS identity operation or required artifact insertion path is unavailable.

## Scope

This proposal covers:

- the `POST /identity/resolve` identity-value response contract owned by the Authority Service
- selection of an existing SIMS identity through its SIMS-issued aggregate ID
- generic, configurable entity-scoped identity allocation and SIMS-store uniqueness
- fail-closed behavior when required SIMS configuration or allocator state is unavailable
- the Authority Service compatibility and validation handoff to Shape Shifter

## Non-Goals

- redesigning the Binding Set model
- changing the meaning of tracked identity UUIDs
- adding new endpoints to SIMS
- solving Delivery 2 change detection or rollback concerns
- Shape Shifter target-model planning, SEAD reconciliation, approval of uncertain matches, and artifact generation
- Change Control submission transactions, package supersession, and deployment eligibility
- production migration, deployment, and cutover; SEAD schema mapping and SEAD database-integrity enforcement
- entity-specific allocator implementations; the site allocator prototype does not establish generic request-level concurrency behavior

## Current Behavior

Current Authority Service behavior:

- `ResolutionOutcome.aggregate_id` is serialized as `target_id` for API compatibility. The value is SIMS-issued and opaque to SIMS consumers.
- Requests select an existing SIMS identity with `approved_aggregate_id`; SIMS looks up that value only in its own identity store.
- The allocator update and tracked-identity insert occur in one statement. A unique partial index prevents duplicate non-null `(entity_type, aggregate_id)` values in SIMS.
- Allocator and retry tests verify entity-scoped value reuse without querying consumer tables or sequences.

Current downstream behavior in Shape Shifter:

- `humlab-sead/sead_shape_shifter:backend/app/models/sims.py` already accepts optional `ResolutionOutcome.target_id`
- `humlab-sead/sead_shape_shifter:backend/app/services/ingester_runtime.py` passes `target_id` through to the ingester when SIMS returns it
- `humlab-sead/sead_shape_shifter:ingesters/sead_change_request/orchestration.py` treats missing `target_id` as a Delivery 1 hard stop for rows that require SIMS allocation

Shape Shifter can consume the field, but the complete approved-miss-to-artifact path has not yet been verified.

## Proposed Design

### API change

Each `ResolutionOutcome` returned by `POST /identity/resolve` may include:

```json
{
  "target_id": 12345
}
```

Field contract:

- name: `target_id`
- type: `int | null`, unchanged from the current Shape Shifter response model
- semantics: the integer is an opaque SIMS-issued, entity-scoped aggregate identity value; the field name is an adapter contract and does not imply that SIMS knows a SEAD table or column
- presence: required when the caller requested a configured allocation or binding operation that returns an aggregate identity value

When the caller selects an existing identity, it supplies `approved_aggregate_id`. SIMS looks up that value only in its own entity-scoped identity store. It does not map the value to a consumer table or column.

### Identity ownership

- SIMS is the sole minter of tracked aggregate identity values and stores each value with its tracked UUID and entity type.
- A generic allocator uses validated configuration to select entity-scoped allocation behavior; adding a supported entity type must not require a new allocator code path.
- SIMS guarantees uniqueness only within its own identity store. It does not inspect SEAD, map identity values to SEAD tables or columns, or enforce SEAD database constraints.
- The current `target_id` response name is an integration detail. It carries a SIMS-issued aggregate identity value to Shape Shifter, whose adapter and artifact logic are responsible for target-model use.
- New tracked identities receive fresh values not derived from source business, provider, or authority keys.
- Every tracked entity represented in SEAD must have a corresponding SIMS identity under the trust contract. Existing-data migration and cutover are not part of this development task.

### Behavior rules

- If SIMS resolves an existing tracked identity, return its stored aggregate identity value in the current `target_id` response field.
- If the caller supplies `approved_aggregate_id`, resolve it only against SIMS-owned identities. Do not infer or verify a consumer table, column, or row.
- If SIMS allocates a new tracked identity, persist and return its aggregate identity value and tracked UUID atomically.
- If configuration or SIMS storage cannot provide the required value, fail the operation rather than return a successful Binding Set without an identity.
- The absence of `target_id` must not change existing Binding Set or tracked-identity behavior.

### Backward compatibility

- Existing clients must continue to work if they ignore `target_id`.
- Shape Shifter will treat `target_id` as optional until the upstream service guarantees it for Delivery 1 entity types.
- During rollout, null is acceptable for non-Delivery-1 use cases, but it remains a blocking condition for Shape Shifter change-request generation.

## Risks And Tradeoffs

- The existing field name `target_id` is target-oriented. Keep target-schema translation in Shape Shifter and avoid using that name as the SIMS domain concept.
- A generic allocator requires a clear configuration contract and uniqueness scope for each entity type.
- Entity support must be configuration-driven; unconfigured or invalid entries fail explicitly instead of receiving entity-specific fallback behavior.

## Testing And Validation

Verified for the site prototype:

- Authority Service repository and service unit tests pass.
- Disposable tests confirm allocation and retry reuse for the current site prototype.
- Existing-row inventory and bootstrap observations document the old prototype's test setup only. They do not establish SIMS responsibility to validate, read, or modify SEAD.

Still required for development validation of the generic contract:

- Shape Shifter-approved miss through generic SIMS allocation and artifact generation with the returned identity value
- same-source and distinct-source concurrency and pending-binding behavior in SIMS
- Shape Shifter validation of its `site` and untracked `site_location` artifact paths; these are not SIMS identity responsibilities
- tests showing multiple configured entity types use the same SIMS allocator mechanism

Existing Shape Shifter checks:

- runtime adapter tests cover both `target_id` present and `target_id` absent paths in `humlab-sead/sead_shape_shifter:backend/tests/ingesters/test_sead_change_request_runtime.py`
- ingester tests cover the explicit capability-gap failure when `target_id` is absent in `humlab-sead/sead_shape_shifter:backend/tests/ingesters/test_sead_change_request_ingester.py`

Additional Authority Service validation:

- tests proving old clients remain compatible when the field is added
- concurrent allocation and uniqueness enforcement within the SIMS identity store

Existing-data migration, deployment checks, competing-writer coordination, and cutover are separate operational work outside this development task.

## Acceptance Criteria

- `P-AC-1`: The resolve response returns the stored aggregate identity value for an approved existing identity and returns a newly allocated value for a configured new identity.
- `P-AC-2`: The current `target_id` response field is documented as an adapter-level carrier for the SIMS-issued aggregate identity value, not as a SIMS table/column mapping.
- `P-AC-3`: The generic allocator uses validated entity configuration and fails closed when required SIMS-owned configuration or state is unavailable.
- `P-AC-4`: SIMS enforces identity-value uniqueness within its own store and atomically associates each value with its tracked UUID and entity type.
- `P-AC-5`: Disposable tests prove multiple configured entity types use the same allocator mechanism and retries reuse the same identity values without duplicate SIMS records.
- `P-AC-6`: Existing clients remain compatible when they ignore `target_id`.

## Planning Handoff

- Use the [completed cross-system identity allocation phase plan](https://github.com/humlab-sead/sead_shape_shifter/blob/main/docs/proposals/CHANGE_REQUEST_INGESTER/done/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md) for sequencing and integration acceptance.
- The Authority Service owns generic identity storage, configuration, allocation, SIMS-store uniqueness, and the response carrying the aggregate identity value.
- Shape Shifter owns target-model interpretation, reconciliation and approval, capability preflight, and artifact generation. SEAD owns integrity of its own persisted data.
- The current development task excludes existing-data migration, production validation, deployment, and cutover. Create a separate operational plan for adopting the trust contract with existing SEAD data.

## Final Recommendation

Treat the site target-ID behavior as a disposable-verified prototype, not the generic architecture. Implement a configurable allocator that mints and stores entity-scoped aggregate identity values and tracked UUIDs through shared code. SIMS guarantees uniqueness within its own store and remains unaware of SEAD tables, columns, sequences, and database constraints. SEAD consumes SIMS-issued identities under the trust contract. Existing-data migration, production checks, and cutover are outside this development task.

This proposal defines the Authority Service's part of the work; it does not claim full Delivery 1 materialization is unblocked.