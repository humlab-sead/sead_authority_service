# SIMS Conceptual Model

## Overview

The SEAD Identity Management System (SIMS) separates externally expressed identity from SEAD-managed identity and makes the correspondence between them explicit, governed, and historically traceable. Source data is received through **Submissions**, interpreted within a **Source Scope**, and represented through **Source Identities**. These are resolved against SEAD-managed **Tracked Identities** through the **Identity Resolution** process. The result is recorded as historical **Bindings**. Once identities have been resolved, proposed domain changes may be bundled into a **Change Request** for review, quality assurance, and possible ingestion into SEAD.

The model aligns with domain-driven design principles, as defined in the next section.

---

## Domain Modeling Foundations

This conceptual model uses the following domain-driven design (DDD) distinctions as its modeling vocabulary. These definitions are authoritative for all SIMS documentation; other documents (including [REQUIREMENTS.md](./REQUIREMENTS.md)) reference these definitions rather than restating them.

**Entity**: a domain object that has stable identity persisting across state changes, submissions, and system boundaries. An entity can be uniquely identified independent of its current attribute values, has a meaningful lifecycle (creation, update, deprecation), and must be reconciled when the same thing may arrive from multiple sources.

**Value object**: a domain object defined entirely by its attributes, interchangeable with any other value object carrying the same values, with no independent lifecycle or stable identity. A value object belongs to an owning entity as part of that entity's aggregate state and is replaced rather than independently updated or reconciled.

**Aggregate**: a cluster of entities and value objects with a single entity serving as the aggregate root. External references target only the root; internal parts are accessed through it. Aggregates define consistency and identity boundaries.

Within SIMS, tracked entities are entities or aggregate roots that receive SEAD-managed identity. Subordinate parts within an aggregate are generally treated as value objects without separate identity.

---

## Core Concepts

### Source Scope

A **Source Scope** defines the external namespace within which a Source Identity is unique, valid, and interpretable. It provides the contextual boundary needed to understand source identifiers by specifying the source system and, where needed, subordinate scoping levels such as provider, dataset, collection, authority, module, project, or local identifier domain. A Source Scope does not itself identify a domain entity; it defines the context in which a Source Identity does so.

**Core properties:**

- **Namespace definition**: defines the context in which a source identity is meaningful
- **Uniqueness boundary**: source identities are unique only within a given source scope
- **May be hierarchical**: may be composed of multiple levels (e.g. system → provider → dataset)
- **Context for interpretation**: determines how source identifiers, business keys, and authority references are understood
- **Independent of entity identity**: it is a contextual container for identities, not an identity itself
- **Stable enough for reuse**: the same source scope may apply across multiple submissions
- **Allows identifier reuse across contexts**: identical local IDs may occur in different scopes without collision

### Submission

A **Submission** is a delivered batch, message, or ingest event originating within a single Source Scope. It provides temporal and procedural provenance for source data entering the identity resolution process. A Submission does not define its own identity context; it inherits that context from its Source Scope.

**Core properties:**

- **Delivery event**: represents a specific import or ingest occurrence, not a persistent identity
- **Scoped to one Source Scope**: all source identities observed in a submission are interpreted within that scope
- **Provenance carrier**: records when and how source data entered the system
- **Observation container**: carries instances of source identities already known or newly observed
- **Does not define identity**: uses the identity context defined by its source scope

### Source Identity

A **Source Identity** is a persistent identity for a domain entity as expressed within a given Source Scope. It is the source-side identity anchor used to distinguish that entity within its scope, independent of whether the entity has yet been bound to a Tracked Identity in SEAD.

**Core properties:**

- **Persistent source-side identity**: represents how a source context identifies a domain entity over time
- **Scoped identity anchor**: its meaning is valid only within a defined source scope
- **Represents a domain entity**: the referent is a source-side entity, possibly an aggregate
- **May persist across submissions**: repeated deliveries can refer to the same source identity within the same scope
- **May exist without binding**: a source identity can be known before any match to SEAD is established
- **Carries source identification signals**: such as local ID, authority ID, business key, natural key, or alternative identifiers
- **Provenance-aware**: remains traceable to the source scope in which it was defined and observed
- **Children are usually value objects**: subordinate parts normally do not receive separate source identities unless the source treats them as entities

### Tracked Identity

A **Tracked Identity** is a persistent, allocated SEAD-side identity for a domain entity that SEAD manages or intends to manage. It is the SEAD-side identity anchor, whether or not the corresponding entity has yet been materialized in SEAD. A Tracked Identity may exist independently of any Source Identity, for example for entities created or curated directly within SEAD.

**Core properties:**

- **Persistent allocated identity**: a SEAD-assigned identity, not a temporary ingestion handle
- **SEAD-side identity anchor**: the target to which source identities may bind
- **Represents a domain entity**: the referent is a DDD-style entity, possibly an aggregate
- **Children are value objects**: subordinate parts normally do not get separate tracked identities
- **May exist before materialization**: the actual entity record may not yet exist in SEAD
- **May exist without source linkage**: SEAD can create and manage tracked identities internally
- **Bound to one intended entity only**: see identity constraints
- **Lifecycle-sensitive**: may be allocated, pending materialization, materialized, or invalidated (see Tracked Identity Lifecycle)
- **Retained after invalidation**: invalidated tracked identities remain in the repository for history and audit
- **Non-reusable after invalidation**: see identity constraints
- **Supports curation as well as ingestion**: may arise from import workflows or from internal repository maintenance

### Binding

A **Binding** is an explicit, managed assertion that a given Source Identity corresponds to a given Tracked Identity. It records the outcome of identity resolution and is retained as a first-class historical object with provenance and lifecycle state. A Binding is not merely a technical pointer; it is the decision object that states two identities are considered the same entity for SEAD purposes.

**Core properties:**

- **Explicit correspondence**: states that one source identity corresponds to one tracked identity
- **Cross-context relation**: bridges an external identity context and the SEAD identity context
- **Outcome of resolution**: represents the result of matching, allocation, or curation
- **Provenance-bearing**: records how, when, and by whom the binding was established
- **Lifecycle-sensitive**: may be proposed, confirmed, rejected, superseded, or invalidated
- **Non-identity-bearing**: does not create either identity, but relates two existing identities
- **Supports audit and traceability**: preserves the history of resolution decisions
- **May exist before materialization**: a source identity may be bound to a tracked identity even if the tracked entity is not yet materialized in SEAD
- **Subject to governance**: may require validation or review before becoming authoritative

### Identity Resolution

**Identity Resolution** is the process by which SEAD determines whether a Source Identity corresponds to an existing Tracked Identity, requires a new Tracked Identity to be allocated, or cannot yet be resolved. It operates within the context of a Source Scope and evaluates identity signals such as local identifiers, authority identifiers, business keys, alternative identifiers, and other matching evidence. Its outcomes are expressed through Bindings and unresolved cases.

**Core properties:**

- **Resolution process**: determines how a Source Identity should relate to SEAD's Tracked Identities
- **Scope-aware**: interprets source identities within a defined source scope
- **Evidence-based**: uses identifiers, keys, provenance, and other matching signals as resolution evidence
- **Binding-producing**: creates Proposed Bindings as explicit candidate correspondences
- **May allocate tracked identities**: when no suitable existing Tracked Identity is found, may result in allocation of a new one
- **Supports multiple outcomes**: match existing identity, allocate new identity, or remain unresolved
- **Precedes change request bundling**: see process constraints
- **Supports automation and curation**: may be performed by rules, matching logic, or manual review
- **Does not require materialization**: resolution may succeed even if the tracked entity is not yet materialized in SEAD

### Change Request

A **Change Request** is a governed package of proposed domain-level changes to SEAD, created after identity resolution has determined how relevant source identities correspond to tracked identities. It is the unit of review, quality assurance, approval, rejection, or deferral before ingestion into the SEAD data model. A Change Request does not define identity correspondence; it consumes correspondence already established through Identity Resolution and Binding.

The Change Request is part of the SEAD Change Control System.

**Core properties:**

- **Governed change package**: bundles proposed domain-level changes for review and approval
- **Post-resolution artifact**: see process constraints
- **Depends on identity decisions**: uses tracked identities and confirmed bindings as prerequisites
- **Supports ingestion control**: may be accepted, rejected, blocked, or deferred by QA
- **May include creates and updates**: can propose materializing new entities or changing existing ones
- **Independent of binding semantics**: does not itself decide whether a source identity corresponds to a tracked identity
- **Traceability-bearing**: preserves links to submissions, source identities, tracked identities, and bindings
- **May never be ingested**: a rejected or deferred Change Request does not invalidate the prior history of identity resolution

---

## Relations and Cardinalities

### 1. Source Scope — Submission

- A **Source Scope** may have many **Submissions**.
- A **Submission** belongs to exactly one **Source Scope**.

A Submission inherits its identity context from its Source Scope. All source identities observed in a submission must be interpretable within that scope.

### 2. Source Scope — Source Identity

- A **Source Scope** may contain many **Source Identities**.
- A **Source Identity** belongs to exactly one **Source Scope**.

A Source Identity is only unique and meaningful within its Source Scope. The same local identifier may occur in different scopes without collision.

**Constraint:** A Source Identity must be unique within its Source Scope, but need not be globally unique across all Source Scopes.

### 3. Submission — Source Identity

- A **Submission** may carry many observed **Source Identities**.
- A **Source Identity** may appear in many **Submissions** over time.

A Submission is an observation event. It carries instances of source identities already known or newly observed within the source scope.

### 4. Source Identity — Binding

- A **Source Identity** may have many historical **Bindings**.
- A **Source Identity** should normally have at most one current confirmed Binding at a given time.

A source identity may be matched, corrected, invalidated, or rebound over time (see binding constraints).

### 5. Tracked Identity — Binding

- A **Tracked Identity** may have many **Bindings**.
- A **Binding** links exactly one **Source Identity** to exactly one **Tracked Identity**.

Many source identities from different scopes or providers may correspond to the same tracked identity in SEAD.

### 6. Tracked Identity — SEAD Materialization

- A **Tracked Identity** may correspond to zero or one materialized SEAD entity.
- A materialized SEAD entity corresponds to one **Tracked Identity**.

A tracked identity may exist before materialization, may remain unmaterialized indefinitely, or may later be invalidated if no accepted Change Request ever materializes it (see identity constraints and Tracked Identity Lifecycle).

### 7. Identity Resolution — Binding

- **Identity Resolution** may create zero or more **Proposed Bindings**.
- A **Binding** is the historical decision object produced by Identity Resolution.

Identity Resolution evaluates evidence and creates candidate or authoritative correspondences. Binding is the durable recorded result.

### 8. Identity Resolution — Tracked Identity

- **Identity Resolution** may reuse an existing **Tracked Identity**.
- **Identity Resolution** may allocate a new **Tracked Identity**.
- **Identity Resolution** may end without any Tracked Identity being selected.

Resolution may result in reuse, allocation, or an unresolved outcome.

### 9. Change Request — Tracked Identity

- A **Change Request** may refer to one or more **Tracked Identities**.
- A **Tracked Identity** may participate in zero or more **Change Requests** over time.

A Change Request proposes creates or updates against already-resolved SEAD-side identities.

### 10. Change Request — Binding

- A **Change Request** may depend on one or more confirmed **Bindings**.
- A **Binding** may support one or more **Change Requests** over time.

The Change Request does not establish identity correspondence; it consumes correspondence already resolved.

### 11. Submission — Change Request

- A **Submission** may give rise to zero, one, or many **Change Requests**.
- A **Change Request** may depend on one or more **Submissions**.

A Submission provides source data and provenance. After identity resolution, resulting domain changes may be grouped into Change Requests. This relation is process-dependent and may be refined as governance needs become clearer.

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

### States

| State | Meaning |
|---|---|
| **Proposed** | A candidate correspondence exists but is not yet authoritative. |
| **Confirmed** | The binding is the current authoritative correspondence. |
| **Rejected** | The proposed correspondence was assessed and refused. |
| **Superseded** | The binding was once authoritative but has been replaced by another. |
| **Invalidated** | The binding is no longer valid for active use, but is retained for history and audit. |

### Allowed transitions

```
Proposed    → Confirmed
Proposed    → Rejected
Confirmed   → Superseded
Confirmed   → Invalidated
```

### Rules

- Rejected, Superseded, and Invalidated are terminal historical states.
- A Binding is current only when it is Confirmed and has not subsequently been superseded or invalidated.
- See binding constraints for the full set of rules governing Bindings.

---

## Tracked Identity Lifecycle

A Tracked Identity may be in one of these conceptual conditions:

| Condition | Meaning |
|---|---|
| **Allocated** | The identity exists in SEAD's identity system. |
| **Pending Materialization** | Allocated but not yet represented as an accepted SEAD entity. |
| **Materialized** | Represented by a SEAD entity in the domain model. |
| **Invalidated** | No longer valid for active use, but retained for history, audit, and traceability. |

### Rules

- If a related Change Request is never accepted and the tracked entity is never materialized, the Tracked Identity may be invalidated.
- See identity constraints for the full set of rules governing Tracked Identities.

---

## Process Flow

The identity-centered flow proceeds as follows:

1. A **Submission** is received.
2. The Submission is interpreted within its **Source Scope**.
3. **Source Identities** are recognized or created within that scope.
4. **Identity Resolution** evaluates each Source Identity.
5. Resolution determines one of three outcomes:
   - finds an existing **Tracked Identity**
   - allocates a new **Tracked Identity**
   - leaves the case unresolved
6. Where a correspondence exists, a **Proposed Binding** is created.
7. The Binding is reviewed and may become **Confirmed** or **Rejected**, or remain unresolved at the process level.
8. Once relevant identities are resolved, proposed domain changes are bundled into a **Change Request**.
9. The Change Request is reviewed, accepted, rejected, or deferred.
10. If accepted, the corresponding tracked entity may be materialized or updated in SEAD.

### Key separation

- **Identity Resolution** establishes identity correspondence.
- **Change Request** governs whether the resulting domain changes are accepted into SEAD.

These are distinct concerns and are handled in separate stages.

---

## Canonical Use Cases

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

## Identifier Type Vocabulary

[REQUIREMENTS.md](./REQUIREMENTS.md) defines five identifier types used across SEAD. The table below maps each to the CM concept that carries or manages it.

| Identifier type (REQ) | Definition | CM concept |
|---|---|---|
| **SEAD internal identity** | Integer primary key inside SEAD's relational schema (`{entity}_id`) | Property of a materialized SEAD entity; linked to a **Tracked Identity** after materialization. |
| **SEAD universal identity** | Stable UUID for a tracked entity (`{entity}_uuid`) | The identity value assigned to a **Tracked Identity**. |
| **Business key** | Natural key or key set that uniquely identifies an entity in practice | An identity signal carried by a **Source Identity** and used during **Identity Resolution**. |
| **Provider key** | Identifier used by a remote data provider | An identity signal carried by a **Source Identity**, retained in the identity system even when not promoted into SEAD tables. |
| **Authority key** | Identifier from an external reference system (e.g. Wikidata, GeoNames) | An identity signal carried by a **Source Identity**, useful for reconciliation and de-duplication of shared metadata. |

> **DRY note**: REQUIREMENTS.md defines these identifier types fully. This table bridges them to CM concepts without restating those definitions.

---

## Entity Subtypes and Identity Policy

[REQUIREMENTS.md](./REQUIREMENTS.md) distinguishes three identity patterns among tracked entities, which affect how Identity Resolution proceeds:

- **Provider-owned entities**: identity is allocated based on incoming evidence; reconciliation against shared SEAD structures is not the primary concern.
- **Shared metadata entities**: must be reconciled against existing SEAD definitions rather than simply allocated new identity; insertion without reconciliation risks duplication.
- **Relationship entities**: bridge records that may qualify as tracked entities when they carry their own attributes or independent lifetime.

REQUIREMENTS.md also specifies an **identity policy** (FR-11) that governs whether a provider-supplied UUID is accepted as the SEAD universal identity or treated only as a provider key. This policy determines how Identity Resolution handles incoming identifiers and is administrable per entity type.

> **DRY note**: Entity subtype and policy definitions are owned by REQUIREMENTS.md. This section provides conceptual-model-level context for those distinctions.

---

## Deferred Issues

The following topics are recognized but deferred for later specification:

1. **Source Identity Observation**: an explicit concept for per-submission observations of Source Identities may be needed if per-delivery state tracking becomes important. For now, the Submission–Source Identity relation (many-to-many) is sufficient.
2. **Unresolved case handling**: formal treatment of unresolved outcomes and associated review or work items.
3. **Merge and split semantics**: two Source Identities later found to be the same entity, or one Source Identity later split into two entities. These scenarios usually introduce significant complexity and will be addressed when needed.
4. **Binding evidence model**: detailed structure for recording the basis of binding decisions (exact identifier match, fingerprint similarity, human review, confidence scores).
5. **Change Request lifecycle**: formal states and transitions for Change Requests (prepared, under review, accepted, rejected, deferred).
6. **Materialized SEAD entity modeling**: the relationship between a Tracked Identity and the actual SEAD domain entity is outside this conceptual model and deferred to implementation design.
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
