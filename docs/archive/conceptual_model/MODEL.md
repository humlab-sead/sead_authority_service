

# Conceptual model

## Overview

The identity system separates **external identity** from **SEAD identity** and makes the correspondence between them explicit, governed, and historically traceable. Source data is received through **Submissions**, interpreted within a **Source Scope**, and represented through **Source Identities**. These are resolved against SEAD-managed **Tracked Identities** through the **Identity Resolution** process. The result is recorded as historical **Bindings**. Once identities have been resolved, proposed domain changes may be bundled into a **Change Request** for review, quality assurance, and possible ingestion into SEAD.

---

## Core concepts

### Source Scope

A **Source Scope** defines the external namespace within which a source identity is unique, valid, and interpretable. It provides the contextual boundary needed to understand source identifiers by specifying the source system and, where needed, subordinate scoping levels such as provider, dataset, collection, authority, module, project, or local identifier domain.

### Submission

A **Submission** is a delivered batch, message, or ingest event originating within a single Source Scope. It provides the temporal and procedural provenance for the source identities observed in that context.

### Source Identity

A **Source Identity** represents a persistent identity for a domain entity as expressed within an external source context. It is the source-side identity anchor used to distinguish that entity within a defined Source Scope, independent of whether the entity has yet been bound to a Tracked Identity in SEAD.

### Tracked Identity

A **Tracked Identity** represents a persistent, allocated SEAD-side identity for a domain entity that SEAD manages or intends to manage. It is the SEAD-side identity anchor, whether or not the entity has yet been materialized in SEAD. A tracked identity may exist independently of any source identity, for example for entities created or curated directly within SEAD.

### Binding

A **Binding** is an explicit, managed assertion that a given Source Identity corresponds to a given Tracked Identity. It represents the outcome of identity resolution and is retained as a first-class historical object with provenance and lifecycle state.

### Identity Resolution

**Identity Resolution** is the process by which SEAD determines whether a Source Identity corresponds to an existing Tracked Identity, requires a new Tracked Identity to be allocated, or cannot yet be resolved. Its outcomes are expressed through Bindings and unresolved cases.

### Change Request

A **Change Request** is a governed package of proposed domain-level changes to SEAD, created after identity resolution has determined how relevant source identities correspond to tracked identities. It is the unit of review, quality assurance, approval, rejection, or deferral before ingestion into the SEAD data model.

---

## Relations and cardinalities

### 1. Source Scope and Submission

* A **Source Scope** may have many **Submissions**
* A **Submission** belongs to exactly one **Source Scope**

#### Semantics

A submission does not define its own identity context. It inherits that context from its source scope. All source identities observed in a submission must be interpretable within that scope.

---

### 2. Source Scope and Source Identity

* A **Source Scope** may contain many **Source Identities**
* A **Source Identity** belongs to exactly one **Source Scope**

#### Semantics

A source identity is only unique and meaningful within its source scope. The same local identifier may occur in different scopes without collision.

#### Constraint

A Source Identity must be unique within its Source Scope, but need not be globally unique across all Source Scopes.

---

### 3. Submission and Source Identity

* A **Submission** may contain many observed **Source Identities**
* A **Source Identity** may appear in many **Submissions** over time

#### Semantics

A submission is an observation event. It carries instances of source identities already known or newly observed within the source scope.

#### Note

Later you may want to add an explicit concept such as **Source Identity Observation** if you need to model per-submission observations more precisely.

---

### 4. Source Identity and Binding

* A **Source Identity** may have many historical **Bindings**
* A **Source Identity** should normally have at most one current active confirmed Binding at a given time

#### Semantics

A source identity may be matched, corrected, invalidated, or rebound over time, but only one correspondence should normally be authoritative at once.

---

### 5. Tracked Identity and Binding

* A **Tracked Identity** may have many **Bindings**
* A **Binding** links exactly one **Tracked Identity** to exactly one **Source Identity**

#### Semantics

Many source identities from different scopes or providers may correspond to the same tracked identity in SEAD.

---

### 6. Tracked Identity and SEAD materialization

* A **Tracked Identity** may correspond to zero or one materialized SEAD entity
* A materialized SEAD entity corresponds to one Tracked Identity

#### Semantics

A tracked identity may exist before materialization, may remain unmaterialized indefinitely, or may later be invalidated if no accepted change request ever materializes it.

#### Constraint

A tracked identity is allocated for one intended domain entity only and must not later be reassigned to another.

---

### 7. Identity Resolution and Binding

* **Identity Resolution** may create zero or more **Proposed Bindings**
* A **Binding** is the historical decision object produced by identity resolution

#### Semantics

Identity resolution evaluates evidence and creates candidate or authoritative correspondences. Binding is the durable recorded result.

---

### 8. Identity Resolution and Tracked Identity

* **Identity Resolution** may reuse an existing **Tracked Identity**
* **Identity Resolution** may allocate a new **Tracked Identity**
* **Identity Resolution** may also end without any tracked identity being selected

#### Semantics

Resolution may result in reuse, allocation, or unresolved outcome.

---

### 9. Change Request and Tracked Identity

* A **Change Request** may refer to one or more **Tracked Identities**
* A **Tracked Identity** may participate in zero or more **Change Requests** over time

#### Semantics

A change request proposes creates or updates against already-resolved SEAD-side identities.

---

### 10. Change Request and Binding

* A **Change Request** may depend on one or more confirmed **Bindings**
* A **Binding** may support one or more **Change Requests** over time

#### Semantics

The change request does not establish identity correspondence; it consumes correspondence already resolved.

---

### 11. Submission and Change Request

* A **Submission** may give rise to zero, one, or many **Change Requests**
* A **Change Request** may depend on one or more **Submissions**, depending on process design

#### Semantics

A submission provides source data and provenance. After identity resolution, resulting domain changes may be grouped into change requests. This relation is process-dependent and may remain flexible for now.

---

## Process semantics

### Identity-centered flow

1. A **Submission** is received.
2. The submission is interpreted within a **Source Scope**.
3. **Source Identities** are recognized or created within that scope.
4. **Identity Resolution** evaluates each source identity.
5. Resolution:

   * finds an existing **Tracked Identity**
   * allocates a new **Tracked Identity**
   * or leaves the case unresolved
6. Where a correspondence exists, a **Proposed Binding** is created.
7. The binding is reviewed and may become **Confirmed**, **Rejected**, or remain unresolved at the process level.
8. Once relevant identities are resolved, proposed domain changes are bundled into a **Change Request**.
9. The change request is reviewed, accepted, rejected, or deferred.
10. If accepted, the corresponding tracked entity may be materialized or updated in SEAD.

---

## Binding state machine

### States

* **Proposed**
* **Confirmed**
* **Rejected**
* **Superseded**
* **Invalidated**

### Meaning

* **Proposed**: a candidate correspondence exists but is not yet authoritative
* **Confirmed**: the binding is the current authoritative correspondence
* **Rejected**: the proposed correspondence was assessed and refused
* **Superseded**: the binding was once authoritative but has been replaced by another
* **Invalidated**: the binding is no longer valid for active use, but is retained for history and audit

### Allowed transitions

* Proposed -> Confirmed
* Proposed -> Rejected
* Confirmed -> Superseded
* Confirmed -> Invalidated

### Rules

* Rejected, Superseded, and Invalidated are terminal historical states
* A binding record is not reactivated after leaving the active path
* Any renewed resolution creates a new Proposed Binding
* A Source Identity should normally have at most one current Confirmed Binding at a time

---

## Tracked Identity lifecycle semantics

A tracked identity may be in one of these conceptual conditions:

* **Allocated**: identity exists in SEAD’s identity system
* **Pending Materialization**: allocated but not yet represented as an accepted SEAD entity
* **Materialized**: represented by a SEAD entity in the domain model
* **Invalidated**: no longer valid for active use, but retained for history, audit, and traceability

### Rules

* Invalidated tracked identities must not be reused
* If a related change request is never accepted and the tracked entity is never materialized, the tracked identity may be invalidated
* A tracked identity remains tied to one intended domain entity only

---

## Key constraints

### Identity constraints

* A Source Identity is unique only within its Source Scope
* A Tracked Identity is unique within SEAD
* A Tracked Identity must not be reassigned to a different intended entity
* Invalidated tracked identities must not be reused

### Binding constraints

* A Binding links exactly one Source Identity to exactly one Tracked Identity
* A Source Identity may have many historical bindings but normally at most one current confirmed binding
* Superseded, Rejected, and Invalidated bindings remain historically visible
* A new binding must be created rather than reactivating an old one

### Process constraints

* Identity resolution precedes bundling into a Change Request
* No source-derived domain change should enter a Change Request until its identity has been resolved sufficiently for policy purposes
* A Change Request governs domain changes, not identity correspondence

---

## Compact summary of the model

* **Source Scope** defines where a source identity is valid
* **Submission** delivers source data within a source scope
* **Source Identity** expresses how an external source identifies an entity
* **Tracked Identity** expresses how SEAD identifies that entity
* **Identity Resolution** determines whether and how the two correspond
* **Binding** records that correspondence as a historical governed assertion
* **Change Request** bundles the resulting domain changes for review and ingestion

---

## A few open questions worth deciding next

There are still a few places where the model could be sharpened:

1. Do you want an explicit concept for **Source Identity Observation** per submission?
2. Should unresolved cases be represented only as a process outcome, or also as an explicit review/work item?
3. Do you want a separate concept for the materialized SEAD entity, or is that outside this conceptual model?
4. Should Change Request cardinality to Submission remain flexible, or do you want a stricter rule?

The cleanest next step is probably to turn this into a more formal specification with:

* concept table
* relation table
* state tables
* 3 to 5 canonical use cases

I can draft that next.

## Formal specification

Below is a formal specification draft based on the decisions made so far.

## Formal specification for the identity model

### 1. Purpose

This specification defines the conceptual model for SEAD’s identity system. The purpose of the identity system is to manage the relationship between externally expressed identities in ingested source data and SEAD-managed identities used to govern domain entities within SEAD. The model separates source-side identity from SEAD-side identity, makes correspondence explicit through managed bindings, and ensures that identity resolution is completed before a submission is bundled into a change request.

### 2. Scope

This specification covers:

* source-side identity context
* source-side identities
* SEAD-side tracked identities
* binding semantics and binding history
* identity resolution
* submission and change request relations

This specification does not cover:

* the detailed internal structure of materialized SEAD domain entities
* value objects internal to aggregates
* unresolved-case workflow beyond noting that it may be deferred for later specification

### 3. Normative principles

1. Source-side identity and SEAD-side identity shall be modeled as distinct concepts.
2. A correspondence between a source identity and a tracked identity shall be expressed explicitly through a binding.
3. Bindings shall be first-class historical objects.
4. Identity resolution shall precede bundling into a change request.
5. Each submission shall belong to exactly one source scope.
6. Each submission shall result in exactly one change request.
7. A tracked identity may exist before the corresponding entity is materialized in SEAD.
8. Invalidated tracked identities and invalidated bindings shall be retained for audit, history, and traceability, and shall not be reused.

---

## 4. Concept definitions

### 4.1 Source Scope

#### Definition

A **Source Scope** defines the external namespace within which a source identity is unique, valid, and interpretable.

#### Semantics

A source scope provides the contextual boundary required to understand source identities. It may include the source system and subordinate scoping levels such as provider, dataset, collection, authority, module, project, or local identifier domain.

#### Notes

A source scope is not itself a domain entity and does not identify anything on its own. It defines the context within which a source identity does so.

---

### 4.2 Submission

#### Definition

A **Submission** is a delivered batch, message, or ingest event originating within exactly one source scope.

#### Semantics

A submission provides temporal and procedural provenance for source data entering the identity resolution process. All source identities observed through the submission shall be interpreted within the submission’s source scope.

---

### 4.3 Source Identity

#### Definition

A **Source Identity** represents a persistent identity for a domain entity as expressed within an external source context.

#### Semantics

A source identity is the source-side identity anchor used to distinguish a domain entity within a defined source scope. It may persist across multiple submissions belonging to the same source scope. It may exist without any current binding to a tracked identity.

#### Notes

A source identity refers to a domain entity or aggregate as understood by the source. Children are typically treated as value objects unless the source treats them as distinct entities.

---

### 4.4 Tracked Identity

#### Definition

A **Tracked Identity** represents a persistent, allocated SEAD-side identity for a domain entity that SEAD manages or intends to manage.

#### Semantics

A tracked identity is the SEAD-side identity anchor for a domain entity. It may exist whether or not the corresponding entity has yet been materialized in SEAD. It may exist independently of any source identity, for example where entities are created or curated directly within SEAD.

#### Notes

A tracked identity refers to a domain entity, which may be an aggregate. Children are normally treated as value objects and do not receive separate tracked identities.

---

### 4.5 Binding

#### Definition

A **Binding** is an explicit, managed assertion that a given source identity corresponds to a given tracked identity.

#### Semantics

A binding records the outcome of identity resolution. It is a first-class historical object and carries lifecycle state and provenance. A binding is not merely a technical pointer; it is the authoritative record of a correspondence decision.

---

### 4.6 Identity Resolution

#### Definition

**Identity Resolution** is the process by which SEAD determines whether a source identity corresponds to an existing tracked identity, requires a new tracked identity to be allocated, or cannot yet be resolved.

#### Semantics

Identity resolution operates within the context of a source scope and evaluates identity signals associated with a source identity. Where a candidate correspondence is identified, a proposed binding is created. That proposal may later become confirmed or rejected. Unresolved outcomes are outside the current scope of formalization.

---

### 4.7 Change Request

#### Definition

A **Change Request** is a governed package of proposed domain-level changes to SEAD, created after identity resolution has determined how relevant source identities correspond to tracked identities.

#### Semantics

A change request is the unit of review, quality assurance, approval, rejection, or deferral before ingestion into SEAD. It depends on prior identity resolution and binding, but does not itself define identity correspondence.

---

## 5. Relations and cardinalities

### 5.1 Source Scope to Submission

* One **Source Scope** may have many **Submissions**
* One **Submission** shall belong to exactly one **Source Scope**

#### Constraint

All source identities observed in a submission shall be interpretable within the submission’s source scope.

---

### 5.2 Source Scope to Source Identity

* One **Source Scope** may contain many **Source Identities**
* One **Source Identity** shall belong to exactly one **Source Scope**

#### Constraint

A source identity shall be unique within its source scope.

---

### 5.3 Submission to Source Identity

* One **Submission** may contain many **Source Identities**
* One **Source Identity** may appear in many **Submissions** over time

#### Semantics

A submission is an observation context in which source identities are encountered, reused, or first recognized.

---

### 5.4 Source Identity to Binding

* One **Source Identity** may have many historical **Bindings**
* One **Source Identity** should normally have at most one current confirmed **Binding** at a given time

#### Constraint

Historical bindings may exist for correction, supersession, or invalidation, but only one binding should normally be authoritative at once.

---

### 5.5 Tracked Identity to Binding

* One **Tracked Identity** may have many **Bindings**
* One **Binding** shall link exactly one **Source Identity** to exactly one **Tracked Identity**

#### Semantics

Many source identities may correspond to the same tracked identity.

---

### 5.6 Submission to Change Request

* One **Submission** shall result in exactly one **Change Request**
* One **Change Request** shall belong to exactly one **Submission**

#### Semantics

A change request is the governed downstream artifact produced for a submission once relevant identities have been resolved.

---

### 5.7 Change Request to Tracked Identity

* One **Change Request** may refer to one or more **Tracked Identities**
* One **Tracked Identity** may participate in zero or more **Change Requests** over time

#### Semantics

A change request proposes creations or updates against already-resolved tracked identities.

---

### 5.8 Change Request to Binding

* One **Change Request** may depend on one or more confirmed **Bindings**
* One **Binding** may support zero or more **Change Requests** over time

#### Semantics

The change request consumes identity correspondence already established by binding.

---

### 5.9 Identity Resolution to Binding

* Identity Resolution may create zero or more **Proposed Bindings**
* One **Binding** shall originate as the result of identity resolution

---

### 5.10 Identity Resolution to Tracked Identity

Identity Resolution may:

* reuse an existing tracked identity
* allocate a new tracked identity
* produce no tracked identity where no reliable match can yet be established

---

## 6. State specifications

### 6.1 Binding states

#### States

* **Proposed**
* **Confirmed**
* **Rejected**
* **Superseded**
* **Invalidated**

#### State definitions

##### Proposed

A candidate correspondence between a source identity and a tracked identity has been created, but is not yet authoritative.

##### Confirmed

The binding has been accepted as valid and is the current authoritative correspondence.

##### Rejected

The proposed binding has been assessed and found incorrect or unacceptable. It is retained historically but is not valid for active use.

##### Superseded

The binding was previously confirmed but has been replaced by another binding that is now authoritative.

##### Invalidated

The binding is no longer valid for active use and is retained for history, audit, and traceability. It has not necessarily been replaced by another binding.

#### Allowed transitions

* Proposed -> Confirmed
* Proposed -> Rejected
* Confirmed -> Superseded
* Confirmed -> Invalidated

#### Transition rules

1. Rejected, Superseded, and Invalidated shall be treated as terminal historical states.
2. A binding record shall not be reactivated after leaving the active path.
3. Any renewed correspondence decision shall create a new Binding record in Proposed state.

#### Currentness rule

A binding shall be considered current only if it is in state Confirmed and has not subsequently been superseded or invalidated.

---

### 6.2 Tracked Identity lifecycle conditions

#### Conditions

* **Allocated**
* **Pending Materialization**
* **Materialized**
* **Invalidated**

#### Definitions

##### Allocated

A tracked identity exists in SEAD’s identity system.

##### Pending Materialization

A tracked identity has been allocated but the corresponding domain entity has not yet been materialized in SEAD.

##### Materialized

The tracked identity corresponds to an accepted and materialized SEAD domain entity.

##### Invalidated

The tracked identity is no longer valid for active use but is retained for audit, history, and traceability.

#### Lifecycle rules

1. A tracked identity may exist without materialization.
2. A tracked identity may be invalidated if the related change request is never accepted and no materialization occurs.
3. An invalidated tracked identity shall not be reused.
4. A tracked identity shall remain tied to one intended domain entity only and shall not later be reassigned.

---

## 7. Process specification

### 7.1 Identity resolution process

#### Description

Identity resolution begins when source data is received through a submission. Source identities are interpreted within the submission’s source scope and evaluated against existing tracked identities using available identity signals. The process may identify an existing tracked identity, allocate a new tracked identity, or defer resolution. Where a candidate correspondence exists, a proposed binding is created.

#### Process steps

1. A submission is received.
2. The submission is associated with exactly one source scope.
3. Source identities are identified within that source scope.
4. Identity signals are evaluated for each source identity.
5. Identity resolution:

   * reuses an existing tracked identity, or
   * allocates a new tracked identity, or
   * produces no authoritative result
6. Where a candidate correspondence exists, a proposed binding is created.
7. The proposed binding may be:

   * confirmed
   * rejected
   * left outside the current formalized outcome space where unresolved handling is deferred
8. After relevant identities are resolved sufficiently for policy purposes, the submission is bundled into exactly one change request.

#### Rule

No source-derived domain change shall enter a change request until its identity has been resolved to the degree required by policy.

---

### 7.2 Change request process role

#### Description

A change request is created after identity resolution and uses the resulting tracked identities and confirmed bindings as the identity foundation for proposed domain changes.

#### Rule

A change request shall govern domain changes, not identity correspondence.

---

## 8. Constraints

### 8.1 Identity constraints

1. A source identity shall be unique within a source scope.
2. A tracked identity shall be unique within SEAD’s identity system.
3. A tracked identity shall refer to one intended domain entity only.
4. Invalidated tracked identities shall not be reused.

### 8.2 Binding constraints

1. A binding shall link exactly one source identity to exactly one tracked identity.
2. A source identity may have many historical bindings.
3. A source identity should normally have at most one current confirmed binding at a time.
4. Historical bindings shall remain visible for audit and traceability.
5. A superseded, rejected, or invalidated binding shall not be reactivated.

### 8.3 Submission and change request constraints

1. Each submission shall belong to exactly one source scope.
2. Each submission shall result in exactly one change request.
3. Each change request shall belong to exactly one submission.

### 8.4 Process constraints

1. Identity resolution shall precede change request creation.
2. Binding creation shall belong to the identity resolution process.
3. Change requests shall depend on prior identity resolution and binding.

---

## 9. Canonical use cases

### 9.1 Existing source identity bound to existing tracked identity

A submission contains a source identity already known within its source scope. The identity resolution process finds an existing confirmed binding to a tracked identity. The submission is then bundled into one change request using that tracked identity as the SEAD-side anchor.

### 9.2 New source identity matched to existing tracked identity

A submission contains a previously unseen source identity. Identity resolution determines that it corresponds to an existing tracked identity. A proposed binding is created and later confirmed. The submission results in one change request referring to that tracked identity.

### 9.3 New source identity requiring a new tracked identity

A submission contains a source identity for which no suitable tracked identity exists. Identity resolution allocates a new tracked identity and creates a proposed binding. If accepted, the submission results in one change request that may later materialize the entity in SEAD.

### 9.4 Confirmed binding later corrected

A binding was previously confirmed but is later found to be wrong. A new proposed binding is created and confirmed. The old binding transitions to Superseded. Historical traceability is preserved.

### 9.5 Change request rejected before materialization

A tracked identity has been allocated and bound, but the change request arising from the submission is rejected or indefinitely blocked. The tracked identity may later be invalidated. The identity and its historical relations remain recorded, but neither the identity nor any allocated identifiers may be reused.

---

## 10. Compact summary

* **Source Scope** defines where a source identity is valid.
* **Submission** delivers source data within one source scope.
* **Source Identity** expresses how an external context identifies a domain entity.
* **Tracked Identity** expresses how SEAD identifies a domain entity.
* **Identity Resolution** determines whether and how source and tracked identities correspond.
* **Binding** records that correspondence as a historical governed assertion.
* **Change Request** bundles the resulting domain changes for review and possible ingestion.
* Each **Submission** results in exactly one **Change Request**.

Two things I would recommend next are a glossary with preferred terms and a compact UML-style relation summary.
