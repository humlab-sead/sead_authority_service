# Systems Design

## Purpose

This document gives the system design view of the SEAD Identity System.

It explains:

- the design intent and architectural boundaries,
- the design rules that constrain implementation choices,
- and the decision flow that ties the system's responsibilities together.

Domain concepts (entity and value object definitions, identity types, entity subtypes, relationship types) are defined in [REQUIREMENTS.md](./REQUIREMENTS.md) and are not restated here. Implementation mechanics belong in [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md).

---

## Design Intent

The SEAD Identity System is designed as an identity layer between external provider workflows and the SEAD relational model.

Its role is to make identity stable across submissions and across system boundaries while preserving SEAD's existing relational primary keys.

At a design level, the system exists to do four things:

1. give tracked entities a stable external identity,
2. preserve the link between that external identity and SEAD internal identity,
3. distinguish provider identity from SEAD identity,
4. support reconciliation where shared metadata or classifiers are involved.

These operate within the following architectural boundaries:

- SEAD integer or bigint primary keys remain the internal relational backbone. The identity layer sits above them, not instead of them.
- A provider identifier may be accepted, mapped, reconciled, or rejected according to an administrable identity policy. It is never assumed to be identical to SEAD identity.
- The identity system decides *what entity* is being referred to. It does not define *how entity state* is inserted, replaced, or updated. Identity management and business-data mutation are separate concerns.

---

## Design Rules

These rules constrain design and implementation choices beyond what the functional requirements already state. Each guards against a specific mistake.

### 1. Value objects are aggregate state, not identity targets

A common mistake is to assign stable identity to every row or child structure. The identity system must only anchor identity at the entity level. Owned child structures (value objects) are part of entity aggregate state and must not receive independent identity, independent reconciliation, or independent lifecycle management.

### 2. Canonical SEAD identity must remain distinct from aliasing identifiers

Provider keys, business keys, and authority keys are identity *evidence*. They may contribute to resolution, but they must never replace or become the canonical SEAD universal identity. A resolved SEAD UUID is always the authoritative reference; external keys are mappings attached to it. Conflating these leads to unstable identity when providers change their own key schemes.

---

## Architectural View

The system has three conceptual responsibilities that execute in a defined order.

### Decision flow

When the system receives identity evidence for a tracked entity, it follows this sequence:

1. **Resolve** — Determine whether the incoming evidence (UUID, business key, provider key, or authority key) matches an existing tracked entity. For shared metadata entities, this step includes reconciliation against SEAD's canonical reference data.
2. **Allocate** — If resolution produces no match, mint a new SEAD UUID. For shared metadata entities, allocation may be blocked: unresolved state is surfaced rather than silently creating a new identity (see FR-20).
3. **Map and trace** — Record the association between the resolved or minted SEAD identity, every piece of incoming evidence, and the submission context. This mapping is permanent and supports idempotency, auditing, and later change detection.

### Policy boundary

Identity policy is applied at the boundary between steps 1 and 2. The policy governs:

- whether a provider-supplied UUID is accepted as the SEAD universal identity or recorded only as a provider key (FR-11),
- whether an unmatched shared metadata entity triggers allocation or is held as unresolved.

Policy is administrable and may vary by entity type.

### Logical position

The system sits between:

- **upstream**: provider submissions carrying identity evidence,
- **policy layer**: administrable rules governing acceptance, reconciliation, and allocation,
- **downstream**: SEAD's relational persistence model, which consumes resolved SEAD internal identifiers.

---

## What This Document Deliberately Leaves Out

This design view does not define:

- endpoint shapes or request/response contracts,
- storage schema for allocation records,
- natural-key construction or hashing rules,
- performance, operational, or non-functional requirements.

Those details belong in [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md).

---

## Relationship To Other Documents

- [REQUIREMENTS.md](./REQUIREMENTS.md) defines what the system must do.
- [ASSESSMENT.md](./ASSESSMENT.md) captures design strengths, weaknesses, and unresolved issues.
- [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md) — implementation structures, storage design, and rollout strategy.