# SIMS Conceptual Model

## Overview

The SEAD Identity Management System (SIMS) separates externally expressed identity from SEAD-managed identity and makes the correspondence between them explicit, governed, and historically traceable. Source data is received through **Submissions**, interpreted within a **Source Scope**, and represented through **Source Identities**. These are resolved against SEAD-managed **Tracked Identities** through the **Identity Resolution** process. The result is recorded as historical **Bindings**. Once identities have been resolved, proposed domain changes may be bundled into a **Change Request** for review, quality assurance, and possible ingestion into SEAD.

The model aligns with domain-driven design principles, as defined in the next section.

---

## Domain Modeling Foundations

This conceptual model uses the following domain-driven design (DDD) distinctions as its modeling vocabulary. These definitions are authoritative for all SIMS documentation.

**Entity**: a domain object that has stable identity persisting across state changes, submissions, and system boundaries. An entity can be uniquely identified independent of its current attribute values, has a meaningful lifecycle (creation, update, deprecation), and must be reconciled when the same thing may arrive from multiple sources.

**Value object**: a domain object defined entirely by its attributes, interchangeable with any other value object carrying the same values, with no independent lifecycle or stable identity. A value object belongs to an owning entity as part of that entity's aggregate state and is replaced rather than independently updated or reconciled.

**Aggregate**: a cluster of entities and value objects with a single entity serving as the aggregate root. External references target only the root; internal parts are accessed through it. Aggregates define consistency and identity boundaries.

Within SIMS, tracked entities are entities or aggregate roots that receive SEAD-managed identity. Subordinate parts within an aggregate are generally treated as value objects without separate identity.

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

A **Source Identity** is a persistent identity for a domain entity as expressed within a given Source Scope. It is the source-side identity anchor used to distinguish that entity within its scope, independent of whether the entity has yet been bound to a Tracked Identity in SEAD.

- May persist across submissions within the same scope
- May exist without any binding to a tracked identity
- Carries source identification signals: local ID, authority ID, business key, natural key, or alternative identifiers

### Tracked Identity

A **Tracked Identity** is a persistent, allocated SEAD-side identity for a domain entity that SEAD manages or intends to manage. It is the SEAD-side identity anchor, whether or not the corresponding entity has yet been materialized in SEAD. A Tracked Identity may exist independently of any Source Identity, for example for entities created or curated directly within SEAD.

- May exist before materialization (the entity record may not yet exist in SEAD)
- May exist without any source linkage
- Lifecycle-sensitive: may be allocated, pending materialization, materialized, or invalidated (see Tracked Identity Lifecycle)
- Invalidated tracked identities are retained for audit but must not be reused

### Binding

A **Binding** is an explicit, managed assertion that a given Source Identity corresponds to a given Tracked Identity. It records the outcome of identity resolution and is retained as a first-class historical object with provenance and lifecycle state. A Binding is not merely a technical pointer; it is the decision object that states two identities are considered the same entity for SEAD purposes.

- Provenance-bearing: records how, when, and by whom the binding was established
- Lifecycle-sensitive: may be proposed, confirmed, rejected, superseded, or invalidated (see Binding Lifecycle)
- May exist before the tracked entity is materialized in SEAD
- Subject to governance: may require validation or review before becoming authoritative

### Identity Resolution

**Identity Resolution** is the process by which SEAD determines whether a Source Identity corresponds to an existing Tracked Identity, requires a new Tracked Identity to be allocated, or cannot yet be resolved. It operates within the context of a Source Scope and evaluates identity signals such as local identifiers, authority identifiers, business keys, alternative identifiers, and other matching evidence. Its outcomes are expressed through Bindings and unresolved cases.

- May be performed by rules, matching logic, or manual review
- Does not require materialization: resolution may succeed before the entity exists in SEAD

### Change Request

A **Change Request** is a governed package of proposed domain-level changes to SEAD, created after identity resolution has determined how relevant source identities correspond to tracked identities. It is the unit of review, quality assurance, approval, rejection, or deferral before ingestion into the SEAD data model. A Change Request does not define identity correspondence; it consumes correspondence already established through Identity Resolution and Binding.

The Change Request is part of the SEAD Change Control System.

- May be accepted, rejected, blocked, or deferred by QA
- May include creates (materializing new entities) and updates
- A rejected or deferred Change Request does not invalidate prior identity resolution history

---

## Relations and Cardinalities

| # | Relation | Cardinality |
|---|---|---|
| 1 | Source Scope — Submission | 1:N (a Submission belongs to exactly one Source Scope) |
| 2 | Source Scope — Source Identity | 1:N (a Source Identity belongs to exactly one Source Scope; unique within that scope) |
| 3 | Submission — Source Identity | M:N (a Submission carries many Source Identities; a Source Identity may appear in many Submissions) |
| 4 | Source Identity — Binding | 1:N (many historical Bindings; normally at most one current confirmed Binding) |
| 5 | Tracked Identity — Binding | 1:N (many Source Identities from different scopes may bind to the same Tracked Identity) |
| 6 | Tracked Identity — SEAD entity | 1:0..1 (a Tracked Identity may correspond to zero or one materialized SEAD entity) |
| 7 | Identity Resolution — Binding | 1:N (resolution may create zero or more Proposed Bindings) |
| 8 | Identity Resolution — Tracked Identity | Resolution may reuse an existing, allocate a new, or select no Tracked Identity |
| 9 | Change Request — Tracked Identity | M:N (a Change Request may refer to multiple Tracked Identities and vice versa) |
| 10 | Change Request — Binding | M:N (a Change Request consumes confirmed Bindings; a Binding may support multiple Change Requests) |
| 11 | Submission — Change Request | M:N (a Submission may give rise to many Change Requests and vice versa) |

---

## Constraints

### Identity constraints

- A Source Identity is unique only within its Source Scope.
- A Tracked Identity is unique within SEAD's identity system.
- A Tracked Identity refers to one intended domain entity only and must not later be reassigned.
- A Tracked Identity may exist before materialization.
- A Tracked Identity may exist without any Source Identity.
- Invalidated Tracked Identities must not be reused.

### Binding constraints

- A Binding links exactly one Source Identity to exactly one Tracked Identity.
- A Source Identity may have many historical Bindings but normally at most one current confirmed Binding.
- Superseded, Rejected, and Invalidated Bindings remain historically visible.
- A historical Binding must not be reactivated; any renewed correspondence creates a new Binding.

### Process constraints

- Identity Resolution precedes Change Request creation.
- No source-derived domain change should enter a Change Request until its identity has been resolved to the degree required by policy.
- Change Requests govern domain changes, not identity correspondence.

---

## Binding Lifecycle

| State | Meaning |
|---|---|
| **Proposed** | A candidate correspondence exists but is not yet authoritative. |
| **Confirmed** | The binding is the current authoritative correspondence. |
| **Rejected** | The proposed correspondence was assessed and refused. |
| **Superseded** | The binding was once authoritative but has been replaced by another. |
| **Invalidated** | The binding is no longer valid for active use, but is retained for history and audit. |

**Allowed transitions:**

```
Proposed    → Confirmed
Proposed    → Rejected
Confirmed   → Superseded
Confirmed   → Invalidated
```

Rejected, Superseded, and Invalidated are terminal states. A Binding is current only when Confirmed and not subsequently superseded or invalidated.

---

## Tracked Identity Lifecycle

| Condition | Meaning |
|---|---|
| **Allocated** | The identity exists in SEAD's identity system. |
| **Pending Materialization** | Allocated but not yet represented as an accepted SEAD entity. |
| **Materialized** | Represented by a SEAD entity in the domain model. |
| **Invalidated** | No longer valid for active use, but retained for history, audit, and traceability. |

If a related Change Request is never accepted and the tracked entity is never materialized, the Tracked Identity may be invalidated.

---

## Canonical Use Cases

Each use case follows the general flow: Submission → Source Scope → Source Identity → Identity Resolution → Binding → Change Request → (optional) Materialization. Identity Resolution and Change Request are distinct stages: the first establishes identity correspondence, the second governs whether domain changes are accepted into SEAD.

### 1. Existing source identity bound to existing tracked identity

A Submission contains a Source Identity already known within its Source Scope. Identity Resolution finds an existing confirmed Binding to a Tracked Identity. The Submission is bundled into a Change Request using that Tracked Identity as the SEAD-side anchor.

### 2. New source identity matched to existing tracked identity

A Submission contains a previously unseen Source Identity. Identity Resolution determines that it corresponds to an existing Tracked Identity. A Proposed Binding is created and later Confirmed. The Submission results in a Change Request referring to that Tracked Identity.

### 3. New source identity requiring a new tracked identity

A Submission contains a Source Identity for which no suitable Tracked Identity exists. Identity Resolution allocates a new Tracked Identity and creates a Proposed Binding. If accepted, the resulting Change Request may later materialize the entity in SEAD.

### 4. Confirmed binding later corrected

A Binding was previously Confirmed but is later found to be wrong. A new Proposed Binding is created to the correct Tracked Identity and Confirmed. The old Binding transitions to Superseded. Historical traceability is preserved.

### 5. Change request rejected before materialization

A Tracked Identity has been allocated and bound, but the Change Request arising from the Submission is rejected or indefinitely blocked. The Tracked Identity may later be invalidated. The identity and its historical relations remain recorded, but neither the identity nor any allocated identifiers may be reused.

---

## Deferred Issues

1. **Source Identity Observation**: an explicit per-submission observation concept may be needed if per-delivery state tracking becomes important.
2. **Unresolved case handling**: formal treatment of unresolved outcomes and associated review or work items.
3. **Merge and split semantics**: two Source Identities later found to be the same entity, or one later split into two.
4. **Binding evidence model**: detailed structure for recording the basis of binding decisions.
5. **Change Request lifecycle**: formal states and transitions for Change Requests.
6. **Materialized SEAD entity modeling**: the relationship between a Tracked Identity and the actual SEAD domain entity.
7. **Detailed policy for binding review**: governance rules for when and how Proposed Bindings are reviewed and Confirmed.

---

## Compact Summary

| Concept | Role |
|---|---|
| **Source Scope** | Defines where a source identity is valid. |
| **Submission** | Delivers source data within a source scope. |
| **Source Identity** | Expresses how an external source identifies an entity. |
| **Tracked Identity** | Expresses how SEAD identifies that entity. |
| **Identity Resolution** | Determines whether and how the two correspond. |
| **Binding** | Records that correspondence as a historical governed assertion. |
| **Change Request** | Bundles the resulting domain changes for review and ingestion. |
