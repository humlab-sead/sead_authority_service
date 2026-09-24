# Provider-Supplied Shared Metadata Entries

## Status

- Proposed feature / change request
- Scope: SIMS shared-metadata policy, requirements, and service (Phase 3+)
- Goal: Let providers propose genuinely new shared metadata entries whose identity is minted by SIMS, subject to human confirmation

## Summary

`REQUIREMENTS.md` FR-20 defines only one outcome for an unmatched classifier or lookup: reject with diagnostics. But `TRACKED_ENTITIES.md` already claims providers *may propose new entries* in the Provider-Extensible shared-metadata group. This proposal adds the missing workflow: unmatched provider-extensible entry → SIMS mints a UUID and holds the identity as pending → a SEAD curator confirms (materializes the entry) or rejects. It applies only to Provider-Extensible metadata; SEAD-Administered vocabularies keep the reject path.

## Problem

Providers must be able to introduce genuinely new shared entries — a new site, project, location, or method — into SEAD. Today they cannot through SIMS:

- Shared metadata is configured `allow_allocation: false`, so SIMS never mints an identity for an unmatched entry.
- FR-20 forces the submission to be rejected with diagnostics instead.
- `TRACKED_ENTITIES.md` says "providers may propose new entries", but no requirement or code path supports that claim.

The only workarounds are out-of-band (email/issue a SEAD admin to pre-create the entry) or abusing the provider-owned path, which would let providers create shared vocabulary without review. Both are wrong.

## Scope

- A proposal workflow for the Provider-Extensible shared-metadata group.
- SIMS mints the UUID at proposal time; the Binding Set stays `PROPOSED`; the identity starts in `Pending Materialization`.
- Curator review: confirm (materialize into the SEAD table) or reject (return FR-20-style diagnostics, create nothing).
- A policy mode for allocation-without-auto-confirmation on this group.
- A new functional requirement (FR-28) and a scoping note on FR-20.

## Non-Goals

- SEAD-Administered vocabularies (`lookup-only`) — providers reference these only; no proposal path.
- Fuzzy-matching or duplicate-detection quality improvements.
- Building the curator review user interface.

## Current Behavior

- `config/identity_policy.yml`: shared metadata is `accept_uuid: true`, `allow_allocation: false`, `auto_confirm: false`.
- FR-20: unmatched shared metadata or classifier → reject with diagnostics.
- Existing lifecycle supports the workflow's states: Binding Sets are `PROPOSED → CONFIRMED | REJECTED`, and TrackedIdentity has `Pending Materialization → Materialized` (allocation is the event that creates the identity, not a separate state).

## Proposed Design

### Policy

Add a third allocation mode to shared metadata: allocation is allowed but never auto-confirmed, and an allocated identity is not authoritative until its Binding Set is confirmed.

Provider-Extensible entities: `allow_allocation: true`, `auto_confirm: false`, allocated identities start in `Pending Materialization`.
SEAD-Administered entities: unchanged (`allow_allocation: false`).

### Flow

1. **Submit** — provider submits a classifier or lookup with key evidence (business key, optionally provider key).
2. **Resolve** — SIMS searches for a business-key match.
   - Match → bind to the existing entry; Binding Set `PROPOSED` → curator confirms. Existing behavior.
   - No match, Provider-Extensible → **proposal path**.
   - No match, SEAD-Administered → FR-20 reject with diagnostics. Unchanged.
3. **Propose** — SIMS mints the UUID, creates a TrackedIdentity in `Pending Materialization`, records the Binding Set as `PROPOSED`. No SEAD table row is created.
4. **Review** — a curator lists pending proposals and either:
   - **confirms** → Binding Set `CONFIRMED`, the entry materializes into the SEAD table, identity becomes `Materialized`; or
   - **rejects** → Binding Set `REJECTED`, provider receives diagnostics, nothing is created.
5. **Reuse** — after confirmation, later submissions carrying the same business key resolve to the confirmed entry (FR-12/13).

### API

- Add a review-queue read: list pending proposals (proposed Binding Sets for provider-extensible shared metadata).
- Confirmation already exists: `POST /identity/binding-sets/{uuid}/confirm`.

### Requirements

- Add FR-28: *The system shall support provider-proposed new shared metadata entries whose identity is minted by SIMS and made authoritative only after human confirmation.*
- Scope FR-20 to SEAD-Administered vocabularies, with a note that Provider-Extensible entries use the proposal path instead.

## Alternatives Considered

- **Keep reject-only (FR-20 as written)** — forces the out-of-band admin workflow and contradicts "providers may propose new entries". Rejected.
- **Auto-create like provider-owned** (`allow_allocation: true` + `auto_confirm: true`) — lets providers write shared vocabulary without review; risks duplicates and vocabulary pollution. Rejected.
- **Proposal workflow (chosen)** — reuses the existing Binding Set and identity lifecycles and preserves the human gate.

## Risks And Tradeoffs

- **Review backlog** — a growing queue of pending proposals needs a curator workflow to keep it tractable.
- **New policy semantics** — allocation-without-auto-confirm is a third mode; the two current booleans alone do not express it. Expect a policy-model change (new flag or state).
- **Concurrent duplicates** — two providers proposing the same new term produce two proposals; deduplication happens at review, not automatically.
- **Minting vs materializing** — the proposal path must keep identity allocation separate from SEAD row creation, or an unconfirmed entry can leak into SEAD.

## Testing And Validation

- Unit tests: policy resolution for the new mode; service flow for propose → confirm → materialize and propose → reject.
- Integration tests (DB-backed): a provider-extensible entity; verify no SEAD row exists until confirm; verify reject returns diagnostics and creates no row; verify a post-confirmation submission resolves to the confirmed entry.
- Update existing tests that assert FR-20 reject behavior for Provider-Extensible entities.

## Acceptance Criteria

- FR-28 exists in `REQUIREMENTS.md`; FR-20 is scoped to SEAD-Administered vocabularies.
- Policy supports allocation-without-auto-confirm for Provider-Extensible shared metadata.
- Propose → confirm produces a materialized SEAD row and a `Materialized` identity.
- Propose → reject produces diagnostics, no SEAD row, and a `REJECTED` Binding Set.
- Post-confirmation submissions resolve to the same entry (idempotent).

## Recommended Delivery Order

1. Requirements: add FR-28, scope FR-20 (docs only).
2. Policy model: allocation-pending mode for Provider-Extensible metadata.
3. Service: proposal path in resolve/bind; pending-proposals review endpoint.
4. Tests for the full flow, then update affected existing tests.

## Open Questions

- Must a proposal carry at least one business key? (Likely yes — matching depends on it.)
- Who may approve proposals — SEAD admins only, or trusted providers with an elevated role?
- Should concurrent identical proposals auto-merge, or stay separate for manual dedup?
- Is provider notification on confirm/reject in scope? (Proposed: no — API result only.)

## Final Recommendation

Implement the proposal workflow for Provider-Extensible shared metadata. SIMS mints the identity at proposal time and holds it pending; a curator confirms or rejects. Keep SEAD-Administered vocabularies on the FR-20 reject path. Add FR-28 and scope FR-20 to match.
