# Provider-Supplied Shared Metadata Entries

## Status

- Proposed feature; revise before implementation to follow the generic SIMS identity contract
- Scope: generic configured allocation requiring confirmation, with consuming-workflow coordination outside SIMS
- Goal: Allow a caller to request a new tracked identity under validated SIMS configuration without making SIMS responsible for SEAD reconciliation or data materialization

**Architecture constraint:** SIMS owns and mints tracked aggregate identities and guarantees uniqueness only within its own store. SIMS does not classify entities using SEAD-specific policy, inspect SEAD data, or create or update SEAD rows. A consuming workflow owns reconciliation, curator interaction, and materialization under the SIMS–SEAD trust contract.

## Summary

Some consuming workflows need a reviewed path for allocating a new identity when reconciliation finds no existing domain entity. The target model may label such an entity as shared metadata, but SIMS must not encode SEAD-specific entity groups or perform that reconciliation. This proposal covers only the generic SIMS allocation and binding state needed by a caller that has made an approved request.

## Problem

The generic SIMS service must be able to represent a configured request for a new tracked identity that requires confirmation. Today:

- Allocation behavior is not yet driven by the target generic configuration contract.
- SIMS must not infer a no-match from SEAD data or decide whether a candidate matches a SEAD row.
- A pending SIMS identity must not be described as a SEAD row or as proof that SEAD data has been materialized.

The consuming workflow remains responsible for reviewing the proposed domain data and submitting an approved allocation request or binding decision.

## Scope

- Generic validated configuration for allocation that requires confirmation.
- SIMS stores the newly minted aggregate identity and a proposed Binding Set using shared service logic.
- A caller-owned review and materialization workflow that confirms or rejects the proposed identity association; SIMS does not write SEAD data.
- A functional requirement for configured pending allocation and confirmation behavior.

## Non-Goals

- Fuzzy-matching or duplicate-detection quality improvements.
- Building the consuming workflow's curator review user interface.
- Reconciliation against SEAD data, SEAD table/column mapping, and SEAD row creation or update.

## Current Behavior

- The current identity policy contains legacy categories such as shared metadata and per-category allocation flags. These do not define the target generic configuration contract.
- The requirements now place target-system reconciliation with the consuming workflow; SIMS does not infer an unmatched SEAD entity.
- Binding Sets already support `PROPOSED → CONFIRMED | REJECTED`. Any consumer-side materialization occurs outside SIMS.

## Proposed Design

### Policy

Define generic, validated configuration for an allocation operation that requires confirmation. Use shared SIMS service logic for every configured entity type; do not add entity-group-specific branches.

SIMS persists the aggregate identity value, tracked UUID, and proposed Binding Set. Confirmation changes SIMS binding state only; it does not assert that a consumer has written a row. Rejection also changes SIMS binding state and preserves the identity audit record.

### Flow

1. **Reconcile** — the consuming workflow evaluates the incoming domain data and approves an existing match, a new identity request, or rejection.
2. **Request** — the caller sends the approved existing identity or a configured allocation request to SIMS with scoped source identity values.
3. **Allocate** — SIMS uses the generic configured allocator, stores the aggregate identity value and tracked UUID, and creates a proposed Binding Set when confirmation is required.
4. **Review** — the consuming workflow's curator confirms or rejects the Binding Set. SIMS records the binding decision; the consuming workflow separately applies any domain-data change.
5. **Reuse** — later requests with the same scoped source identity resolve to the same SIMS Tracked Identity (FR-12/13).

### API

- Add a review-queue read for proposed Binding Sets only if the agreed confirmation workflow requires one.
- Use `POST /identity/binding-sets/{uuid}/confirm` for SIMS binding confirmation; do not treat it as a SEAD materialization operation.

### Requirements

- Add FR-28: *For a configured allocation operation that requires confirmation, the system shall persist the SIMS identity and proposed Binding Set until the caller confirms or rejects the Binding Set.*
- Keep reconciliation and reject-on-no-match decisions with the consuming workflow; do not name SEAD-specific entity groups in SIMS requirements.

## Alternatives Considered

- **Disallow allocation in configuration** — appropriate where the consuming workflow requires an existing identity; not suitable for workflows that approve new identity requests.
- **Auto-confirm every allocation** — removes a required review step and may be unsuitable for workflows with a human approval gate.
- **Configured allocation with pending confirmation (recommended)** — uses generic SIMS allocation and Binding Set state while leaving domain review and materialization to the consuming workflow.

## Risks And Tradeoffs

- **Review backlog** — a growing queue of pending proposals needs a curator workflow to keep it tractable.
- **Configuration semantics** — configuration must express whether an operation allocates and whether confirmation is required, without entity-specific allocator code.
- **Concurrent duplicates** — two providers proposing the same new term produce two proposals; deduplication happens at review, not automatically.
- **Minting vs materializing** — SIMS identity allocation must remain separate from consumer data writes; only the consuming workflow applies domain changes.

## Testing And Validation

- Unit tests: generic configuration validation and service flows for allocate → confirm and allocate → reject.
- SIMS database tests: verify identity uniqueness, pending Binding Set state, confirmation/rejection, and source-identity retry behavior without connecting to or writing a consumer database.
- Consuming-workflow tests: verify review outcomes and domain writes occur outside SIMS and use SIMS-issued identity values.

## Acceptance Criteria

- FR-28 describes generic configured allocation requiring confirmation; SIMS requirements do not name SEAD-specific entity groups.
- The same allocator code serves configured entity types, with uniqueness enforced only within the SIMS identity store.
- Allocate → confirm and allocate → reject update SIMS Binding Set state without writing consumer data.
- The consuming workflow applies any approved domain change using the SIMS-issued identity value under the trust contract.
- Retries for the same scoped source identity resolve to the same SIMS Tracked Identity.

## Recommended Delivery Order

1. Requirements: add FR-28, scope FR-20 (docs only).
2. Configuration model: generic allocation that requires Binding Set confirmation.
3. Service: proposal path in resolve/bind; pending-proposals review endpoint.
4. Tests for the full flow, then update affected existing tests.

## Open Questions

- Must a proposal carry at least one business key? (Likely yes — matching depends on it.)
- Which caller roles may confirm a proposed Binding Set?
- Should concurrent identical proposals auto-merge, or stay separate for manual dedup?
- Is provider notification on confirm/reject in scope? (Proposed: no — API result only.)

## Final Recommendation

Implement generic configured allocation with optional confirmation state in SIMS. Keep reconciliation, curator decisions about domain data, and consumer materialization outside SIMS. Finalize requirements only after the consuming workflow and confirmation responsibility are agreed.
