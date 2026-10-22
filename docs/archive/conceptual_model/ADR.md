# ADR: Identity model for source and tracked identities in SEAD

## Status
Accepted (draft baseline for further refinement)

## Date
2026-04-04

## Context
SEAD ingests external data from multiple providers and source contexts. The same real-world domain entity may be identified differently across external systems, datasets, authorities, or local identifier domains. SEAD also needs to manage entities that originate internally and may exist in curated repositories before they are materialized in the main SEAD domain model.

A dedicated identity model is therefore needed to:

- separate externally expressed identity from SEAD-managed identity
- make identity correspondence explicit and historically traceable
- resolve identities before domain changes are bundled for ingestion
- support review, quality assurance, and deferred or rejected ingestion
- preserve auditability when identity decisions or downstream change requests are later rejected or corrected

The model should align with domain-driven design principles where tracked entities are domain entities or aggregates, while subordinate parts are generally treated as value objects without separate identity.

## Decision
SEAD shall use an identity model based on the concepts **Source Scope**, **Submission**, **Source Identity**, **Tracked Identity**, **Binding**, **Identity Resolution**, and **Change Request**.

The model makes a strict distinction between:

- **Source Identity**: how an external source context identifies a domain entity
- **Tracked Identity**: how SEAD identifies a domain entity
- **Binding**: the explicit managed assertion that a given Source Identity corresponds to a given Tracked Identity

Identity resolution shall occur before a submission is bundled into a change request. Each submission shall belong to exactly one source scope and shall result in exactly one change request.

Bindings shall be first-class historical objects with lifecycle states. Tracked identities may exist before the corresponding entity is materialized in SEAD and may also exist without any source identity, for example for internally curated entities.

Invalidated tracked identities and invalidated bindings shall be retained for audit, history, and traceability, and shall never be reused.

## Definitions

### Source Scope
A Source Scope defines the external namespace within which a Source Identity is unique, valid, and interpretable. It provides the contextual boundary needed to understand source identifiers by specifying the source system and, where needed, subordinate scoping levels such as provider, dataset, collection, authority, module, project, or local identifier domain.

### Submission
A Submission is a delivered batch, message, or ingest event originating within exactly one Source Scope. It provides temporal and procedural provenance for source data entering the identity resolution process.

### Source Identity
A Source Identity is a persistent source-side identity for a domain entity as expressed within a given Source Scope. It may persist across multiple submissions in the same source scope and may exist without any current binding to SEAD.

### Tracked Identity
A Tracked Identity is a persistent, allocated SEAD-side identity for a domain entity that SEAD manages or intends to manage. It is the SEAD-side identity anchor whether or not the corresponding entity has yet been materialized in SEAD. A Tracked Identity may exist independently of any Source Identity.

### Binding
A Binding is an explicit, managed, historical assertion that a Source Identity corresponds to a Tracked Identity. It records the outcome of identity resolution and carries provenance and lifecycle state.

### Identity Resolution
Identity Resolution is the process by which SEAD determines whether a Source Identity corresponds to an existing Tracked Identity, requires a new Tracked Identity to be allocated, or cannot yet be resolved.

### Change Request
A Change Request is a governed package of proposed domain-level changes to SEAD, created after identity resolution has determined how relevant source identities correspond to tracked identities. It is the unit of review, quality assurance, approval, rejection, or deferral before ingestion.

## Model rules

### Identity rules
- A Source Identity is unique only within its Source Scope.
- A Tracked Identity is unique within SEAD’s identity system.
- A Tracked Identity refers to one intended domain entity only and shall not later be reassigned.
- A Tracked Identity may exist before materialization.
- A Tracked Identity may exist without any Source Identity.
- Invalidated Tracked Identities shall not be reused.

### Submission and scope rules
- Each Submission belongs to exactly one Source Scope.
- All Source Identities observed through a Submission shall be interpreted within that Source Scope.
- Each Submission results in exactly one Change Request.
- A Submission observes or carries Source Identities; it does not define them.

### Binding rules
- A Binding links exactly one Source Identity to exactly one Tracked Identity.
- A Source Identity may have many historical Bindings.
- A Source Identity should normally have at most one current confirmed Binding at a given time.
- A Binding is a first-class historical object and shall not be treated as a mere technical pointer.
- Superseded, Rejected, and Invalidated Bindings remain historically visible.
- A historical Binding shall not be reactivated; any renewed correspondence decision creates a new Binding.

### Process rules
- Identity Resolution precedes Change Request creation.
- No source-derived domain change shall enter a Change Request until identity has been resolved to the degree required by policy.
- Change Requests govern domain changes, not identity correspondence.

## Binding lifecycle

### States
- Proposed
- Confirmed
- Rejected
- Superseded
- Invalidated

### Allowed transitions
- Proposed -> Confirmed
- Proposed -> Rejected
- Confirmed -> Superseded
- Confirmed -> Invalidated

### State meanings
- **Proposed**: a candidate correspondence exists but is not yet authoritative
- **Confirmed**: the binding is the current authoritative correspondence
- **Rejected**: the proposed correspondence was assessed and refused
- **Superseded**: the binding was once authoritative but has been replaced by another binding
- **Invalidated**: the binding is no longer valid for active use but is retained for history, audit, and traceability

### Lifecycle constraints
- Rejected, Superseded, and Invalidated are terminal historical states.
- A Binding is current only when it is Confirmed and has not subsequently been superseded or invalidated.
- Renewed correspondence creates a new Binding rather than reactivating an old one.

## Tracked identity lifecycle conditions
- **Allocated**: the identity exists in SEAD’s identity system
- **Pending Materialization**: allocated but not yet represented as an accepted SEAD entity
- **Materialized**: represented by an accepted and materialized SEAD domain entity
- **Invalidated**: no longer valid for active use, but retained for audit, history, and traceability

## Relation summary
- One Source Scope may have many Submissions.
- One Source Scope may define many Source Identities.
- One Submission belongs to exactly one Source Scope.
- One Submission results in exactly one Change Request.
- One Submission may carry many Source Identities.
- One Source Identity may appear in many Submissions over time.
- One Binding links exactly one Source Identity to exactly one Tracked Identity.
- One Source Identity may have many historical Bindings.
- One Tracked Identity may have many Bindings.
- One Change Request may refer to one or more Tracked Identities.
- One Change Request may depend on one or more confirmed Bindings.

## Rationale
This model was chosen because it:

- separates source-side and SEAD-side identity cleanly
- supports subscoped external identifiers through Source Scope
- supports historical auditability by treating Binding as a first-class object
- allows SEAD to allocate identities before materialization
- supports internally managed entities without requiring an external source identity
- keeps identity correspondence separate from downstream change governance
- fits a DDD-oriented view in which aggregates are identity-bearing while children are usually value objects

## Consequences

### Positive
- Identity correspondence becomes explicit and traceable.
- External identifier reuse across datasets or namespaces can be handled safely.
- Identity decisions remain auditable even when change requests are rejected.
- The model supports both ingest-driven and curator-driven identity allocation.
- The model is stable enough to support later formalization in diagrams, state models, and implementation design.

### Negative
- The model introduces additional conceptual and implementation complexity.
- Binding lifecycle and identity resolution policy will require governance and operational discipline.
- Some unresolved-case behavior remains deferred for later specification.

## Canonical use cases

### Existing source identity bound to existing tracked identity
A submission contains a source identity already known within its source scope. Identity resolution finds an existing confirmed binding to a tracked identity. The submission is bundled into one change request using that tracked identity as the SEAD-side anchor.

### New source identity matched to existing tracked identity
A submission contains a previously unseen source identity. Identity resolution determines that it corresponds to an existing tracked identity. A proposed binding is created and later confirmed. The submission results in one change request referring to that tracked identity.

### New source identity requiring a new tracked identity
A submission contains a source identity for which no suitable tracked identity exists. Identity resolution allocates a new tracked identity and creates a proposed binding. If accepted, the resulting change request may later materialize the entity in SEAD.

### Confirmed binding later corrected
A binding was previously confirmed but is later found to be wrong. A new proposed binding is created and confirmed. The old binding transitions to Superseded. Historical traceability is preserved.

### Change request rejected before materialization
A tracked identity has been allocated and bound, but the change request arising from the submission is rejected or indefinitely blocked. The tracked identity may later be invalidated. The identity and its historical relations remain recorded, but neither the identity nor any allocated identifiers may be reused.

## Alternatives considered

### Treat source and tracked identity as the same concept
Rejected because it would collapse source-side provenance and SEAD-side governance into one concept and make correction, auditing, and internal curation harder.

### Treat Binding as a simple technical link
Rejected because identity correspondence needs provenance, lifecycle, correction history, and auditability.

### Let Change Request define identity correspondence
Rejected because identity correspondence must be resolved before downstream domain changes are packaged for review and ingestion.

### Allow a submission to span multiple source scopes
Rejected for the baseline model because it weakens contextual clarity and complicates deterministic identity interpretation. The baseline rule is one submission, one source scope.

## Deferred issues
- Formal treatment of unresolved outcomes and unresolved work items
- Detailed policy for review and confirmation of proposed bindings
- Materialized SEAD entity modeling outside this conceptual model
- Implementation details for persistence, APIs, and workflow orchestration

## Summary
SEAD adopts an identity model in which externally expressed Source Identities are interpreted within a Source Scope, resolved against SEAD-managed Tracked Identities through Identity Resolution, and linked by historical Bindings. Each Submission belongs to one Source Scope and results in exactly one Change Request. Change Requests govern domain changes, while identity correspondence is handled separately and explicitly in the identity layer.

