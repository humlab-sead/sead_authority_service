# SIMS Conceptual Model and Systems Design

> **Status:** Reflects the implementation as of Phases 1–2 (complete). Generic configurable aggregate-identity allocation is the target design and is not yet implemented. Existing-data migration, production adoption, and cutover are outside the current development task. See [OPERATIONS.md](./OPERATIONS.md) for deployment and [src/identity/README.md](../../src/identity/README.md) for the module entry point.

## Overview

The SEAD Identity Management System (SIMS) owns tracked aggregate identities and the source identities associated with them. Source data is received through **Submissions**, interpreted within a **Source Scope**, and represented through **Source Identities**. These are resolved against SIMS-owned **Tracked Identities** through the **Identity Resolution** process. The results are grouped into **Binding Sets** — atomic batches of **Bindings** that are confirmed or rejected together. Once identities have been resolved, a Binding Set may be associated with a **Change Request** managed by a consuming system.

The model aligns with domain-driven design principles, as defined in the next section.

**An identity is not the same thing as an identifier.** A Source Identity or Tracked Identity is a persistent identity record; identifiers such as UUIDs, local IDs, business keys, and authority IDs are values carried by or associated with those records, used as evidence during Identity Resolution. "Identity" throughout this document refers to the record, not the value.

---

## Identity Roles

Each tracked aggregate has three distinct identity roles:

- **Aggregate identity value**: an opaque, entity-scoped value minted and stored by SIMS.
- **Tracked UUID**: the stable UUID minted and stored by SIMS for its Tracked Identity.
- **Source identity keys**: UUIDs, business, provider, and authority identifiers scoped to their source. They identify a source's representation of an aggregate; they are not SIMS-minted aggregate identities.

SIMS stores the entity type, aggregate identity value, tracked UUID, and source identity associations. It guarantees uniqueness within its own identity store. SIMS does not inspect SEAD, map identity values to SEAD tables or columns, or enforce SEAD database integrity. SEAD consumes SIMS-issued values under the SIMS–SEAD trust contract.

SIMS is the sole minter of tracked aggregate identity values. Its generic allocation mechanism uses validated configuration, not entity-specific allocator code. Every tracked entity represented in SEAD must have a corresponding SIMS Tracked Identity. Establishing this condition for existing production data is separate operational work and outside the current development task. The current site allocator is a prototype, not the generic allocation design.

## Design Intent

The system is designed as an identity service for tracked aggregates and their source identities. Its goals are stated in [REQUIREMENTS.md § Goals](./REQUIREMENTS.md#goals). At the design level, the following architectural boundaries apply:

- SIMS owns and uniquely stores tracked aggregate identities and their configured identity values.
- SIMS does not know how a consuming system stores identity values in tables or columns and does not enforce that system's database constraints.
- SEAD consumes SIMS-issued values under the trust contract and has no tracked aggregate identities that are absent from SIMS.
- A provider identifier may be accepted, mapped, reconciled, or rejected according to validated SIMS entity configuration. It is never assumed to be the SIMS aggregate identity.
- The identity system decides *which aggregate* is being referred to. It does not define *how domain state* is inserted, replaced, or updated. Identity management and business-data mutation are separate concerns (see [Process constraints](#process-constraints)).

---

## Domain Modeling Foundations

This conceptual model uses the following domain-driven design (DDD) distinctions as its modeling vocabulary. These definitions are authoritative for all SIMS documentation.

**Entity**: a domain object that has stable identity persisting across state changes, submissions, and system boundaries. An entity can be uniquely identified independent of its current attribute values, has a meaningful lifecycle (creation, update, deprecation), and must be reconciled when the same thing may arrive from multiple sources.

**Value object**: a domain object defined entirely by its attributes, interchangeable with any other value object carrying the same values, with no independent lifecycle or stable identity. A value object belongs to an owning entity as part of that entity's aggregate state and is replaced rather than independently updated or reconciled.

**Aggregate**: a cluster of entities and value objects with a single entity serving as the aggregate root. External references target only the root; internal parts are accessed through it. Aggregates define consistency and identity boundaries.

Within SIMS, tracked entities are entities or aggregate roots whose identities SIMS manages. Subordinate parts within an aggregate are generally treated as value objects without separate SIMS identity; the consuming domain system owns any storage identifiers for those values.

---

## Core Concepts

### Source Scope

A **Source Scope** defines the external namespace within which a Source Identity is unique, valid, and interpretable. It provides the contextual boundary needed to understand source identifiers by specifying the source system and, where needed, subordinate scoping levels such as provider, dataset, collection, authority, module, project, or local identifier domain. A Source Scope does not itself identify a domain entity; it defines the context in which a Source Identity does so.

- May be hierarchical (e.g. system → provider → dataset)
- Stable enough for reuse across multiple submissions
- Identical local IDs may occur in different scopes without collision

### Submission

A **Submission** is a delivered batch, message, or ingest event originating within a single Source Scope. It provides temporal and procedural provenance for source data entering the identity resolution process. A Submission does not define its own identity context; it inherits that context from its Source Scope.

- Represents a specific import or ingest occurrence, not a persistent identity
- Carries instances of source identities already known or newly observed

### Source Identity

A **Source Identity** is a persistent identity for a domain entity as expressed within a given Source Scope. It is the source-side identity anchor used to distinguish that entity within its scope, independent of whether the entity has yet been bound to a SIMS Tracked Identity.

- May persist across submissions within the same scope
- May exist without any binding to a tracked identity
- Carries source identification signals: local ID, authority ID, business key, natural key, or alternative identifiers

### Tracked Identity

A **Tracked Identity** is a persistent SIMS identity for a tracked aggregate. It exists independently of how or where a consuming system materializes the aggregate. A Tracked Identity may exist before any Source Identity is associated with it.

- May exist before a consumer materializes the aggregate
- May exist without any source linkage
- Lifecycle-sensitive: may be allocated, pending materialization, materialized, or invalidated (see Tracked Identity Lifecycle)
- SIMS mints and persists its configured aggregate identity value and tracked UUID together before returning a successful allocation result.
- Invalidated tracked identities are retained for audit but must not be reused

### Binding

A **Binding** is an explicit assertion that a given Source Identity corresponds to a given Tracked Identity. It records the outcome of identity resolution for one Source Identity and is retained as a historical object with provenance. A Binding always belongs to exactly one Binding Set.

- Provenance-bearing: records how the binding was established (method, evidence)
- May exist before the consuming system materializes the aggregate
- Lifecycle is governed by the owning Binding Set (see Binding Set Lifecycle)

### Binding Set

A **Binding Set** is the atomic unit of identity resolution output. It groups one or more Bindings that are confirmed or rejected together as a single governed batch. The Binding Set owns the lifecycle state, audit trail, and Change Request reference for its constituent Bindings.

- Lifecycle-sensitive: may be proposed, confirmed, rejected, or invalidated (see Binding Set Lifecycle)
- Owns the association with a Change Request (if any)
- Subject to governance: may require validation or review before becoming authoritative
- A Binding Set may contain Bindings for multiple entity types within the same Submission

### Identity Resolution

**Identity Resolution** is the SIMS process for determining whether a Source Identity corresponds to an existing SIMS Tracked Identity or requires a new identity to be allocated. It operates within a Source Scope and uses source identity values and caller-approved outcomes. Its results are expressed through Bindings. Reconciliation against a consuming system's domain data is outside SIMS; the caller supplies an approved existing identity or requests a configured allocation operation.

- SIMS performs lookups within its own identity store; reconciliation and manual review against consumer data belong to the caller
- Does not require materialization: resolution may succeed before the consuming system creates its domain object

### Change Request

A **Change Request** is an optional external reference associated with identity work. The consuming workflow owns and manages the referenced change package. SIMS may retain the reference as opaque metadata; it does not manage or apply the change package, interpret its format, or map it to consumer storage.

- Owned by the consuming workflow, not by SIMS
- Referenced by an opaque value
- May be accepted, rejected, blocked, or deferred by QA
- May include creates (materializing new entities) and updates
- A rejected or deferred Change Request does not invalidate prior identity resolution history

### Materialization

**Materialization** is the consuming workflow's act of creating or establishing a domain object represented by an already allocated Tracked Identity. A Tracked Identity may exist before materialization. SIMS does not perform, verify, or guarantee consumer-side materialization.

- Not required for a Tracked Identity to exist or be bound
- Governed by Change Request acceptance, not by SIMS directly
- See [Tracked Identity Lifecycle](#tracked-identity-lifecycle) for the states before and after materialization

---

## Decision Flow

SIMS receives source identities and approved identity requests from consuming workflows, then returns SIMS-owned identity results. Validated SIMS configuration governs its supported identity operations; callers own reconciliation against their own domain data.

The decision flow maps to the core concepts above:

1. **Identity Resolution** — Determine whether the incoming **Source Identity** (within a **Source Scope**) is already bound to a **Tracked Identity**, or whether the caller has supplied an approved existing identity or requested a configured allocation operation. Reconciliation against the consuming system's domain data belongs to that caller. SIMS evaluates source identity values such as local IDs, business keys, provider keys, and authority keys.

2. **Binding** — If the caller supplies an approved existing SIMS identity, create a **Proposed Binding** linking the Source Identity to that Tracked Identity. If the caller requests a new identity and validated configuration permits allocation, allocate a Tracked Identity and bind to it. Reject unsupported or disallowed operations with diagnostics (FR-20). Group the Bindings from a resolution batch into a **Binding Set** — the atomic unit confirmed or rejected together (FR-26). Binding Set lifecycle is defined in [Binding Set Lifecycle](#binding-set-lifecycle).

3. **External change workflow** — A consuming workflow may associate a confirmed Binding Set with an opaque external change reference. The workflow owns any domain-data mutation. SIMS does not interpret or apply the change request. Identity allocation remains independent of data mutation (FR-25) and supports aggregate-level change detection (FR-24).

### Policy boundary

Identity policy is applied between steps 1 and 2. The policy governs:

- whether a provider-supplied UUID is accepted as a source-key type or rejected by validated SIMS configuration (FR-11),
- whether the requested identity operation is configured, permitted, and subject to confirmation.

Configuration may vary by entity type, but behavior is implemented by shared generic service code.

---

## Relations and Cardinalities

| #  | Relation                               | Cardinality                                                                                                |
|----|----------------------------------------|------------------------------------------------------------------------------------------------------------|
| 1  | Source Scope — Submission              | 1:N (a Submission belongs to exactly one Source Scope)                                                     |
| 2  | Source Scope — Source Identity         | 1:N (a Source Identity belongs to exactly one Source Scope; unique within that scope)                      |
| 3  | Submission — Source Identity           | M:N (a Submission carries many Source Identities; a Source Identity may appear in many Submissions)        |
| 4  | Source Identity — Binding              | 1:N (many historical Bindings; normally at most one current confirmed Binding)                             |
| 5  | Tracked Identity — Binding             | 1:N (many Source Identities from different scopes may bind to the same Tracked Identity)                   |
| 6  | Tracked Identity — consuming aggregate | 1:0..1 (a Tracked Identity may exist before a consumer materializes its aggregate)                         |
| 7  | Binding Set — Binding                  | 1:N (a Binding Set contains one or more Bindings; a Binding belongs to exactly one Binding Set)            |
| 8  | Identity Resolution — Binding Set      | 1:1 (resolution produces one Binding Set)                                                                  |
| 9  | Identity Resolution — Tracked Identity | Resolution may reuse an existing, allocate a new, or select no Tracked Identity                            |
| 10 | Change Request — Binding Set           | 1:N (a Change Request may consume many confirmed Binding Sets; a Binding Set is associated with zero or one Change Request) |
| 11 | Submission — Change Request            | M:N (a Submission may give rise to many Change Requests and vice versa)                                    |

---

## Constraints

### Identity constraints

- A Source Identity is unique only within its Source Scope.
- A Tracked Identity is unique within the SIMS identity store.
- A Tracked Identity refers to one intended domain entity only and must not later be reassigned.
- A Tracked Identity may exist before materialization.
- A Tracked Identity may exist without any Source Identity.
- Invalidated Tracked Identities must not be reused.

### Binding constraints

- A Binding links exactly one Source Identity to exactly one Tracked Identity.
- A Binding belongs to exactly one Binding Set.
- A Source Identity may have many historical Bindings but normally at most one within a current confirmed Binding Set.
- Superseded, Rejected, and Invalidated Binding Sets (and their Bindings) remain historically visible.
- A historical Binding must not be reactivated; any renewed correspondence creates a new Binding in a new Binding Set.

### Binding Set constraints

- A Binding Set contains one or more Bindings.
- All Bindings in a Binding Set share the same lifecycle state (governed at the set level).
- A Binding Set may be associated with zero or one Change Request.
- Splitting a Binding out of a set (e.g. to reject one while confirming the rest) creates a new Binding Set.

### Process constraints

- Identity Resolution precedes Change Request association.
- No source-derived domain change should enter a Change Request until its identity has been resolved to the degree required by policy and the corresponding Binding Set is confirmed.
- Change Requests govern domain changes, not identity correspondence.

---

## Design Rules

These rules constrain implementation choices beyond what the functional requirements state.

### 1. Value objects are aggregate state, not identity targets

The identity system anchors identity at the entity level only. Owned child structures (value objects, as defined in [Domain Modeling Foundations](#domain-modeling-foundations)) must not receive independent identity, reconciliation, or lifecycle management.

### 2. SIMS aggregate identity must remain distinct from source identifiers

Provider keys, business keys, and authority keys are source identity values (see [Source Identity](#source-identity)). They contribute to resolution but do not replace the SIMS aggregate identity value or tracked UUID. SIMS stores each role separately and links source identities through Bindings.

### 3. Consumers apply domain changes only after identity checks

The consuming workflow must check that every entity it intends to change has an appropriate SIMS identity result before applying a domain change. The workflow also owns manual curation and internal data preparation. SIMS provides identity operations; it does not approve, apply, or validate consumer-side data changes.

---

## Binding Set Lifecycle

The lifecycle is managed at the Binding Set level. All Bindings within a set share the set's lifecycle state.

| State           | Meaning                                                                           |
|-----------------|-----------------------------------------------------------------------------------|
| **Proposed**    | The set's correspondences exist as candidates but are not yet authoritative.      |
| **Confirmed**   | The set's correspondences are the current authoritative identity mappings.        |
| **Rejected**    | The proposed set was assessed and refused as a whole.                             |
| **Superseded**  | The set was once authoritative but has been replaced by another.                  |
| **Invalidated** | The set is no longer valid for active use, but is retained for history and audit. |

**Allowed transitions:**

```
Proposed    → Confirmed
Proposed    → Rejected
Confirmed   → Superseded
Confirmed   → Invalidated
```

Rejected, Superseded, and Invalidated are terminal states. A Binding Set is current only when Confirmed and not subsequently superseded or invalidated.

---

## Tracked Identity Lifecycle

Allocation is the event that creates a Tracked Identity in the `Pending Materialization` state; it is not itself a separate lifecycle state.

| State                        | Meaning                                                                            |
|-------------------------------|------------------------------------------------------------------------------------|
| **Pending Materialization**   | The identity has been allocated; no consumer-side materialization has been reported. |
| **Materialized**              | A consumer has reported that the identity corresponds to a materialized domain object. SIMS does not verify this report. |
| **Invalidated**               | No longer valid for active use, but retained for history, audit, and traceability. |

**Allowed transitions:**

```
Pending Materialization → Materialized
Pending Materialization → Invalidated
Materialized            → Invalidated
```

Whether a Tracked Identity may be invalidated after a consumer rejects or abandons its change request requires a separate lifecycle decision.

---

## Canonical Use Cases

Each use case follows the general flow: Submission → Source Scope → Source Identity → Identity Resolution → Binding Set → optional external change workflow → optional consumer-side materialization. Identity Resolution establishes identity correspondence; the consuming workflow governs domain changes.

### 1. Reuse a confirmed binding for a known source identity

A Submission contains a Source Identity already known within its Source Scope. Identity Resolution finds an existing confirmed Binding to a Tracked Identity. The consuming workflow may use that identity when preparing a domain change.

### 2. Match a new source identity to an existing tracked identity

A Submission contains a previously unseen Source Identity. The caller supplies an approved existing Tracked Identity. SIMS creates a Proposed Binding within a Binding Set, which is later Confirmed. The consuming workflow may associate that set with its own change process.

### 3. Allocate a new tracked identity for an unmatched source identity

A Submission contains a Source Identity for which no suitable Tracked Identity exists. The caller requests a configured allocation; SIMS allocates a new Tracked Identity and creates a Proposed Binding within a Binding Set. If confirmed, the consuming workflow may later materialize its domain object using the SIMS-issued identity value.

### 4. Correct a confirmed binding

A Binding within a previously Confirmed Binding Set is later found to be wrong. A new Binding Set is created containing a Proposed Binding to the correct Tracked Identity. The new Binding Set is Confirmed; the old Binding Set transitions to Superseded. Historical traceability is preserved.

### 5. Invalidate a tracked identity after a rejected change request

A Tracked Identity has been allocated and bound within a Confirmed Binding Set, but the Change Request associated with the Binding Set is rejected or indefinitely blocked. The Tracked Identity may later be invalidated. The Binding Set and its historical relations remain recorded, but neither the identity nor any allocated identifiers may be reused.

---

## Deferred Issues

1. **Source Identity Observation**: an explicit per-submission observation concept may be needed if per-delivery state tracking becomes important.
2. **Unresolved case handling**: Determine whether generic allocation requiring confirmation needs a review queue; SIMS does not classify SEAD-specific metadata types.
3. **Merge and split semantics**: two Source Identities later found to be the same entity, or one later split into two.
4. **Binding evidence model**: detailed structure for recording the basis of binding decisions.
5. **Change Request integration**: detailed rules for how SIMS associates Binding Sets with externally managed Change Requests.
6. **Consumer-reported materialization**: whether the generic SIMS lifecycle should record a consumer-reported materialization state.
7. **Detailed policy for binding review**: governance rules for when and how Proposed Bindings are reviewed and Confirmed.

---

## Compact Summary

| Concept                 | Role                                                                                             |
|-------------------------|--------------------------------------------------------------------------------------------------|
| **Source Scope**        | Defines where a source identity is valid.                                                        |
| **Submission**          | Delivers source data within a source scope.                                                      |
| **Source Identity**     | Expresses how an external source identifies an entity.                                           |
| **Tracked Identity**    | Expresses the SIMS-owned identity of a tracked aggregate.                                        |
| **Identity Resolution** | Determines whether and how the two correspond.                                                   |
| **Binding**             | Records one source-to-tracked correspondence with provenance.                                    |
| **Binding Set**         | Groups Bindings into an atomic batch with shared lifecycle, audit, and Change Request reference. |
| **Change Request**      | Optional opaque reference to a consumer-owned domain-change process.                              |
