# Systems Design

> **Status: Frozen (2026-04-06).** Implementation complete. This document is preserved as design rationale. See [OPERATIONS.md](./OPERATIONS.md) for deployment and [src/identity/README.md](../../src/identity/README.md) for the module entry point.

## Purpose

This document gives the system design view of the SEAD Identity System: architectural boundaries, design rules, and the decision flow that ties the system's responsibilities together.

Domain concepts are defined in [REQUIREMENTS.md](./REQUIREMENTS.md) and the conceptual model in [CONCEPTUAL_MODEL.md](./CONCEPTUAL_MODEL.md). Implementation mechanics belong in [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md).

---

## Design Intent

The SEAD Identity System is designed as an identity layer between external provider workflows and the SEAD relational model. Its goals are stated in [REQUIREMENTS.md § Goals](./REQUIREMENTS.md#goals). At the design level, the following architectural boundaries apply:

- SEAD integer or bigint primary keys remain the internal relational backbone. The identity layer sits above them, not instead of them.
- A provider identifier may be accepted, mapped, reconciled, or rejected according to an administrable identity policy. It is never assumed to be identical to SEAD identity.
- The identity system decides *what entity* is being referred to. It does not define *how entity state* is inserted, replaced, or updated. Identity management and business-data mutation are separate concerns (see also [CM § Constraints: Process constraints](./CONCEPTUAL_MODEL.md#process-constraints)).

---

## Design Rules

These rules constrain implementation choices beyond what the functional requirements state.

### 1. Value objects are aggregate state, not identity targets

The identity system anchors identity at the entity level only. Owned child structures (value objects, as defined in [CM § Domain Modeling Foundations](./CONCEPTUAL_MODEL.md#domain-modeling-foundations)) must not receive independent identity, reconciliation, or lifecycle management.

### 2. Canonical SEAD identity must remain distinct from aliasing identifiers

Provider keys, business keys, and authority keys are identity *signals* (see [CM § Source Identity](./CONCEPTUAL_MODEL.md#source-identity)). They contribute to resolution but must never replace the canonical SEAD universal identity. A resolved SEAD UUID is the authoritative reference; external keys are mappings attached to it.

### 3. A Change Request must not be applied until all referenced identities are resolved

A Change Request must not be applied to SEAD until every entity it references has a resolved identity expressed through a confirmed Binding Set. This applies regardless of whether the entities originate from an external provider submission or from internal SEAD administration. The manual curation of internally administered entities is out of scope for SIMS — it is the responsibility of the submitting system (Shape Shifter internal workflow, a dedicated admin tool, or another client). SIMS provides the identity resolution API; the tooling that prepares and submits internal entities is a separate concern.

---

## Architectural View

The system sits between provider submissions (upstream) carrying identity signals and SEAD's relational persistence model (downstream) which consumes resolved identifiers. An administrable policy layer governs acceptance, reconciliation, and allocation decisions.

### Decision flow

The decision flow maps to the conceptual model's core concepts (see [CM § Core Concepts](./CONCEPTUAL_MODEL.md#core-concepts)):

1. **Identity Resolution** — Determine whether the incoming identity signals (within a **Source Scope**) match an existing **Tracked Identity**. For shared metadata entities, this includes reconciliation against SEAD's existing definitions. Resolution evaluates **Source Identity** signals: local IDs, business keys, provider keys, authority keys.

2. **Binding** — If resolution finds a match, create a **Proposed Binding** linking the Source Identity to the Tracked Identity. If no match exists, allocate a new Tracked Identity and bind to it. For shared metadata entities, allocation is blocked: the submission is rejected with diagnostic information rather than silently creating a new identity (FR-20). The Bindings produced by a resolution batch are grouped into a **Binding Set** — the atomic unit that is confirmed or rejected together (FR-26). Binding Set lifecycle is defined in [CM § Binding Set Lifecycle](./CONCEPTUAL_MODEL.md#binding-set-lifecycle).

3. **Change Request** — Once identity correspondence is established through a confirmed Binding Set, the Binding Set is associated with a **Change Request** — an external object owned by the SEAD Change Control System (Sqitch), referenced by unique name. The Change Request governs business-data mutation; it does not alter identity correspondence. SIMS records the association but does not manage the Change Request lifecycle. This separation ensures identity allocation remains independent of data mutation (FR-25) and supports aggregate-level change detection (FR-24).

### Policy boundary

Identity policy is applied between steps 1 and 2. The policy governs:

- whether a provider-supplied UUID is accepted as the SEAD universal identity or recorded only as a provider key (FR-11),
- whether an unmatched shared metadata entity triggers allocation or causes the submission to be rejected with diagnostics.

Policy is administrable and may vary by entity type.

---

Implementation details (storage schema, endpoint contracts, hashing rules, NFRs) belong in [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md).