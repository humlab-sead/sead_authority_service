# Adopt Existing `site` Rows into SIMS as `materialized`

## Status

- Proposed change request — draft for review
- Scope: One-time adoption of existing SEAD `site` rows as SIMS tracked identities, and initialization of the `site` ID allocator.
- Goal: Make every existing `site` ID bindable through SIMS, so that reconciled existing sites can be imported through the change-request ingester.

## Summary

SIMS binds an existing ID only when a tracked identity exists for it. Existing `site` rows were created before SIMS and have none. The [SIMS target ID contract](./SIMS_TARGET_ID_CONTRACT/SIMS_TARGET_ID_CONTRACT.md) requires every tracked SEAD entity to have a SIMS identity and leaves existing-data adoption as separate operational work. This proposal is that work for `site` only.

Run an idempotent backfill that creates one `materialized` tracked identity per existing `site_id`, with `aggregate_id` equal to that `site_id`, and initializes the `site` allocator above the highest existing ID. Run a check afterward that every SEAD site has an identity and every `site` identity has a SEAD row.

The [Shape Shifter reconciliation MVP](https://github.com/humlab-sead/sead_shape_shifter/blob/main/docs/proposals/RECONCILIATION_MVP/RECONCILIATION_MVP.md) and the [candidate-check proposal](./RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md) depend on this work only for end-to-end import. Reconciliation links can be created without it.

## Problem

- `POST /identity/resolve` with an `approved_aggregate_id` looks up that value in SIMS's own identity store. With no tracked identity for the ID, binding an existing `site` fails, even though the SEAD row exists.
- The `site` ID allocator row is created only by bootstrap, after existing IDs are loaded. Until then, allocating a new `site` ID fails with an error telling the operator to bootstrap existing IDs first.
- The planned SIMS rule that approved-ID binding requires a `materialized` identity ([AS-AC-5](./RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md)) would make the gap permanent: adopted identities must already be `materialized` to pass it.
- No plan or owner for this work exists. The contract and the proposals index both list it as separate operational work.

## Scope

- Create a `materialized` tracked identity for every existing `site_id`, using the `site_id` as `aggregate_id`.
- Initialize the `site` allocator so the next minted ID is above the highest existing `site_id`.
- Make the backfill safe to rerun, so it can catch up rows added before cutover.
- Verify the result in both directions and report mismatches.

## Non-Goals

- Entity types other than `site`.
- SEAD cutover: stopping SEAD's own `site_id` generation and coordinating competing writers. See the contract's list of separate operational work.
- Creating source identities, submissions, or Binding Sets for existing rows. SIMS creates those when a change request resolves a row.
- Making SIMS read SEAD tables at runtime. The backfill is a one-time operation outside the service.
- Changing the identity policy, the allocator design, or `aggregate_id` semantics.

## Current Behavior

Verified in the Authority Service repository:

- A tracked identity has an entity type, an `aggregate_id`, a lifecycle state (`allocated`, `pending_materialization`, `materialized`, `invalidated`), a `materialized_at` time, and a generated UUID ([schema](../../schema/sql/identity/005_tracked_identities.sql), [rename](../../schema/sql/identity/010_aggregate_identity_value.sql)).
- A unique index covers `(entity_type, aggregate_id)` ([allocator schema](../../schema/sql/identity/009_site_id_allocator.sql)).
- Minting reads and increments `internal_id_allocators.next_internal_id` for the entity type, and fails when no allocator row exists ([repository](../../src/identity/repository.py#L391)).
- The identity policy enables `bind_existing` and `allocate_new` for `site` ([policy](../../config/identity_policy.yml#L75)).
- SIMS configuration maps `site` to `tbl_sites.site_id` ([entities](../../config/entities.yml#L184)).

Not verified:

- Whether any `site` identities or allocator row exist in the target environments.
- Whether `sead_identity` and `tbl_sites` are in the same database.
- Whether SEAD still generates `site_id` outside SIMS.
- The number of existing `site` rows.

## Proposed Design

**Backfill.** Insert one tracked identity per `tbl_sites.site_id` that has none: `entity_type = 'site'`, `aggregate_id = site_id`, `lifecycle_state = 'materialized'`, `materialized_at` set to the run time, and `created_by` naming this operation. Skip any `site_id` that already has an identity, so reruns do not fail on the unique index. Adopt the whole table, not a subset, so there is one rule to verify.

**Allocator.** Create the `site` allocator row with `next_internal_id = max(site_id) + 1` if it does not exist. If it exists, raise it only when it is at or below the highest adopted ID; never lower it.

**Verification.** After the run, report:

- SEAD `site_id` values with no `site` identity (must be none);
- `site` identities with no SEAD row (investigate; not deleted automatically);
- identities not in `materialized` state;
- allocator value not above the highest `site_id`.

**Execution.** The backfill reads consumer data, so it belongs on the consumer side, not inside SIMS code. Run it as a SEAD change request if both schemas are in one database; otherwise as a one-time, reviewed script run by an operator against both databases. Either form must be a single transaction and must print the verification report.

**Ownership.** The Authority Service owns the identity-side rules and the verification report. Applying the change request to staging and production follows the SEAD change-control process. Owner names and dates are TBD.

## Alternatives Considered

- **Adopt lazily, on first binding of each ID:** Rejected. It makes SIMS read SEAD at request time, which the contract rules out, and leaves the allocator uninitialized.
- **Adopt only reconciled sites:** Rejected. It needs a selection rule, leaves most rows untracked, and still requires allocator initialization.
- **Mint new aggregate IDs and map them to `site_id`:** Rejected. The contract's `aggregate_id` is the value consumers store; a second ID would force a lookup table for no benefit.

## Risks And Tradeoffs

- **Competing writers:** A site created in SEAD outside SIMS after the backfill has no identity, and a SIMS allocation could collide with an ID SEAD already used. The rerunnable backfill and the verification report detect drift. Preventing it requires cutover, which is out of scope.
- **Orphan identities:** An identity with no SEAD row would pass SIMS checks for a row that does not exist. The reconciliation candidate check (SEAD row existence) is the guard; the verification report lists these for review.
- **`content_hash`:** Adopted identities have no content hash. The effect on change detection for existing rows is not assessed here.
- **Irreversibility:** Adopted identities are normal SIMS records. Rollback means invalidating or deleting them, and a deliberate allocator reset. State this in the change request.

## Testing And Validation

Run the backfill against a disposable database holding SEAD `site` rows and SIMS tables:

- first run, rerun with no change, and rerun after adding a site;
- an existing partial set of identities;
- an existing allocator row below, equal to, and above the highest `site_id`;
- an identity with no SEAD row, reported but not removed.

After adoption, resolve an approved existing `site` ID through `POST /identity/resolve` and confirm it binds. Allocate a new `site` and confirm its ID is above every existing `site_id`.

## Acceptance Criteria

- `P-AC-1` After the backfill, every `tbl_sites.site_id` has exactly one `site` tracked identity with `aggregate_id` equal to that ID and state `materialized`.
- `P-AC-2` Rerunning the backfill changes nothing when no new sites exist, adopts only the new sites otherwise, and never fails on existing identities.
- `P-AC-3` The `site` allocator exists and its next ID is above the highest `site_id`; it is never lowered.
- `P-AC-4` The verification report lists missing identities, orphan identities, non-`materialized` identities, and allocator violations; orphan identities are not deleted automatically.
- `P-AC-5` In a disposable database, an approved existing `site` binds through `POST /identity/resolve`, and a newly allocated `site` ID does not collide with an existing one.

## Planning Handoff

**Confirmed decisions**

- `site` only; whole table; `aggregate_id` equals `site_id`; state `materialized`.
- One-time, idempotent, outside SIMS runtime code; SIMS never reads SEAD at request time.
- Cutover and competing-writer coordination stay out of scope.

**Preserve**

- SIMS-owned allocation and uniqueness; the contract that SIMS does not depend on consumer tables.

**Validation**

- Run the disposable-database checks above before any shared environment.

## Open Questions

- **Owner and schedule:** Who owns and runs this work, and by when? Needed before the Shape Shifter end-to-end validation phase.
- **Database layout:** Are `sead_identity` and `tbl_sites` in one database? This decides between a change request and a script. Needed before the first phase.
- **Existing state:** Do any `site` identities or an allocator row already exist in staging or production? Needed before the first phase.
- **SEAD `site_id` generation:** Does SEAD still create `site_id` values itself? This sets the collision risk window until cutover.

## Final Recommendation

Adopt all existing `site` rows into SIMS in one reviewed, rerunnable operation that also initializes the allocator, and verify the result in both directions. Assign an owner before the reconciliation MVP's end-to-end validation.
