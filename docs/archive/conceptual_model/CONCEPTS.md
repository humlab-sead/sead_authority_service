# Concepts

## Tracked Identity

A Tracked Identity represents a persistent, allocated SEAD-side identity for a domain entity that SEAD manages or intends to manage. It is the identity anchor for that entity within the identity system, whether or not the entity has yet been materialized in SEAD. A tracked identity may exist independently of any source identity, for example for entities created or curated directly within SEAD. It refers to a domain entity, which may be an aggregate, while its children are typically treated as value objects without their own identity. If a related change request is never accepted and the entity is never materialized, the tracked identity and any allocated SEAD-side identifiers may be invalidated; in that case they are no longer valid for active use, but are retained for audit, history, and traceability, and must not be reused.

### Core properties:

* **Persistent allocated identity**: it is a SEAD-assigned identity, not just a temporary ingestion handle
* **SEAD-side identity anchor**: it is the target to which source identities may bind
* **Represents a domain entity**: the referent is a DDD-style entity, possibly an aggregate
* **Children are value objects**: subordinate parts normally do not get separate tracked identities
* **May exist before materialization**: the actual entity record may not yet exist in SEAD
* **May exist without source linkage**: SEAD can create and manage tracked identities internally
* **Bound to one intended entity only**: it should not later be reassigned to a different entity
* **Lifecycle-sensitive**: it may be pending, active, materialized, or invalidated depending on curation and change-request outcome
* **Retained after invalidation**: invalidated tracked identities remain in the repository for history and audit
* **Non-reusable**: once invalidated, the identity and its allocated identifiers must never be reused
* **Supports curation as well as ingestion**: it may arise from import workflows or from internal repository maintenance

## Source Identity

A Source Identity represents a persistent identity for a domain entity as expressed within an external source context. It is the source-side identity anchor used to distinguish that entity within a defined source scope, independent of whether the entity has yet been bound to a tracked identity in SEAD. The source scope may include the source system and one or more subordinate namespaces, such as provider, dataset, authority, collection, module, or local identifier domain. A source identity may persist across multiple submissions within the same scope, may carry one or more identifiers or business keys, and may exist without any current binding to a tracked identity in SEAD.

### Core properties:

* **Persistent source-side identity**: it represents how a source context identifies a domain entity over time
* **Scoped identity anchor**: its meaning is valid only within a defined source scope
* **Supports subscoping**: scope may include source system plus provider, dataset, collection, authority, or other namespace levels
* **Represents a domain entity**: the referent is a source-side entity, possibly an aggregate
* **May persist across submissions**: repeated deliveries can refer to the same source identity within the same scope
* **May exist without binding**: a source identity can be known before any match to SEAD is established
* **Carries source identification signals**: such as local ID, authority ID, business key, natural key, or alternative identifiers
* **Provenance-aware**: it remains traceable to the source scope in which it was defined and observed
* **Children are usually value objects**: subordinate parts normally do not receive separate source identities unless the source treats them as entities
* **Lifecycle-sensitive**: it may be observed, resolved, bound, ambiguous, superseded, or retired

## Source Scope
A Source Scope defines the external namespace within which a source identity is unique, valid, and interpretable. It provides the contextual boundary needed to understand and resolve a source identity by specifying the source system and, where needed, one or more subordinate scoping levels such as provider, dataset, collection, authority, module, project, or local identifier domain. A source scope does not itself identify a domain entity; rather, it defines the context in which a source identity does so. The same local identifier may therefore represent different entities in different source scopes, while a source identity must be unique within its own source scope.

### Core properties:

* **Namespace definition**: it defines the context in which a source identity is meaningful
* **Uniqueness boundary**: source identities are unique only within a given source scope
* **May be hierarchical**: a scope may be composed of multiple levels, such as system → provider → dataset
* **Context for interpretation**: it determines how source identifiers, business keys, and authority references are understood
* **Independent of entity identity**: it is not itself an entity, but a contextual container for identities
* **Supports provenance**: it helps preserve where and under what conditions a source identity originated
* **Stable enough for reuse**: the same source scope may apply across multiple submissions
* **Allows identifier reuse across contexts**: identical local IDs may occur in different scopes without collision
* **Supports resolution logic**: matching and binding decisions should take source scope into account

A compact paired formulation would then be:

* **Source Scope** = where a source identity is valid
* **Source Identity** = how an entity is identified within that scope
* **Tracked Identity** = how SEAD identifies the corresponding entity
* **Binding** = the explicit assertion linking a source identity to a tracked identity

A useful constraint to state explicitly could be:

> A source identity must be unique within a source scope, but need not be globally unique across all source scopes.

You may also want a very short version for diagrams:

**Source Scope**
The namespace or contextual boundary within which a source identity is unique and meaningful.

## Submission

Yes. This relation should be defined explicitly, because it affects both provenance and identity resolution.

My recommendation is:

**A Submission is made within one Source Scope, while a Source Scope may have many Submissions over time.**

That gives you a clean and practical rule:

* **Source Scope → Submission** = one-to-many
* **Submission → Source Scope** = many-to-one

### Suggested definition

**Relation between Source Scope and Submission**
A Submission is a delivery, import package, or ingest event that occurs within a defined Source Scope. The Source Scope provides the namespace and contextual boundary in which the source identities contained in the submission must be interpreted. A submission therefore inherits its identity context from exactly one source scope, while a source scope may be associated with many submissions over time. This allows repeated deliveries from the same provider, dataset, or identifier domain to reuse the same source scope and the same source identities consistently across submissions.

### Why this is a good default

This makes several things easier:

* identity resolution becomes deterministic, because every identity in a submission is interpreted in one known namespace
* provenance stays clear, because each submission has one contextual origin
* repeated deliveries from the same provider or dataset can reuse the same source identities
* local identifiers can safely recur in different scopes without collision

### Core semantics

* A **Source Scope** defines the namespace for source identities
* A **Submission** is an event or package delivered within that namespace
* A submission does **not** define identity context by itself; it **uses** the identity context defined by its source scope
* Source identities observed in a submission are interpreted relative to the submission’s source scope

### Recommended cardinality

* **One Source Scope** may have **many Submissions**
* **One Submission** belongs to **exactly one Source Scope**

### Constraint to state explicitly

> All source identities contained in a submission must be interpretable within the submission’s source scope.

That is probably the most important rule.

### One possible exception

If you expect one submission file or batch to include data from multiple datasets, authorities, or identifier domains, then you may need one of these alternatives:

1. **Submission has one Source Scope**
   Simpler and cleaner. Best if each submission is normalized before ingestion.

2. **Submission contains scoped parts**
   A submission may include multiple internal sections, each with its own source scope.

Unless you already know you need mixed-scope submissions, I strongly recommend the first model. It is much easier to reason about.

### Compact diagram wording

You could express it like this:

**Submission**
A delivery or ingest event occurring within a single Source Scope.

**Relation**
A Submission belongs to one Source Scope.
A Source Scope may be associated with many Submissions over time.

### My recommendation for the final wording

**Submission**
A Submission is a delivered batch, message, or ingest event originating within a single Source Scope. It records the transfer of source data into the identity resolution process and provides temporal and procedural provenance for the source identities observed in that context.

**Relation to Source Scope**
Each Submission belongs to exactly one Source Scope, which defines the namespace in which the submission’s source identities are valid and interpretable. A Source Scope may be reused by many Submissions over time.

Good. 

## Binding
A Binding is an explicit assertion that a given Source Identity corresponds to a given Tracked Identity. It records the outcome of identity resolution between an externally scoped identity and a SEAD-managed identity, and provides the semantic link by which ingested source data can be associated with the correct domain entity in SEAD. A binding is not merely a technical reference; it is a managed relation with provenance, lifecycle, and status. It may be created through automated matching, manual curation, or repository maintenance, and it may exist in different states such as proposed, confirmed, rejected, superseded, or invalidated.

**Binding** is probably the central relation in the whole model, so it should be defined as more than just a link. It should be an explicit, governed assertion.

### Why this definition works

This makes Binding:

* not just a foreign-key style connection
* but the **decision object** that says “these two identities are considered the same entity for SEAD purposes”
* and the place where you can attach governance, audit, confidence, and lifecycle

That fits very well with the rest of your model:

* **Source Scope** defines where a source identity is valid
* **Source Identity** identifies an entity externally
* **Tracked Identity** identifies an entity in SEAD
* **Binding** states that they correspond

### Core properties

* **Explicit correspondence**: it states that one source identity corresponds to one tracked identity
* **Cross-context relation**: it bridges an external identity context and the SEAD identity context
* **Outcome of resolution**: it represents the result of matching, allocation, or curation
* **Provenance-bearing**: it should record how, when, and by whom the binding was established
* **Lifecycle-sensitive**: it may be proposed, confirmed, rejected, superseded, or invalidated
* **Non-identity-bearing**: it does not create either identity, but relates two existing identities
* **Supports audit and traceability**: it preserves the history of resolution decisions
* **May exist before materialization**: a source identity may be bound to a tracked identity even if the tracked entity is not yet materialized in SEAD
* **Supports internal and external workflows**: it may arise from ingestion, curation, or repository maintenance
* **Subject to governance**: it may require validation or review before becoming authoritative

### Suggested cardinality

I recommend this as your default rule:

* A **Binding** links exactly **one Source Identity** to exactly **one Tracked Identity**
* A **Tracked Identity** may have **many Bindings** from different source identities
* A **Source Identity** should normally have at most **one current active Binding**

That last part is important. It allows history, but avoids concurrent contradictory truth.

So more precisely:

* one source identity → zero or one **current** binding
* one tracked identity → zero to many current bindings
* one source identity → many historical bindings over time, but only one should normally be current

### Suggested attributes:

binding ID
source entity reference
tracked identity
status
method
confidence
evidence
asserted by
asserted at
valid from / valid to
current flag
review note

### Constraint worth stating explicitly

> A Source Identity should normally have at most one active Binding at a given time.

That gives you room for:

* correction
* supersession
* invalidation
* audit history

without allowing unresolved duplication in the steady state.

### Binding lifecycle suggestion

A small lifecycle is probably enough.

Possible states:

* **Proposed**: a candidate correspondence has been identified
* **Confirmed**: the binding is accepted as valid
* **Rejected**: a proposed binding was assessed and refused
* **Superseded**: an earlier confirmed binding has been replaced by a later one
* **Invalidated**: the binding is no longer valid for active use, but retained for audit/history

You could also include:

* **Pending Review** if human QA is important in your workflow

A lean version would be:

* proposed
* confirmed
* rejected
* superseded
* invalidated

### Recommended semantics of invalidated for Binding

To stay aligned with your Tracked Identity definition:

**Invalidated Binding**
A binding that is no longer valid for active use, but is retained for history, audit, and traceability. An invalidated binding must not be reactivated implicitly and must not be treated as a current correspondence.

That is distinct from **superseded**:

* **superseded** = replaced by another binding
* **invalidated** = no longer valid, without necessarily being replaced

That distinction may be very useful.

### Relation to Change Request

Given your earlier description, I would suggest this:

* identity resolution happens **before** bundling into a Change Request
* therefore a binding should usually be established, or explicitly unresolved, before CR creation
* a CR may depend on a confirmed binding, but does not itself define the binding

So Binding belongs primarily to the **identity resolution layer**, not the change-request layer.

A useful statement might be:

> Bindings are established during identity resolution and may be prerequisites for creating a change request that materializes or updates the corresponding tracked entity in SEAD.

### Compact version for diagrams

**Binding**
An explicit, governed assertion that a Source Identity corresponds to a Tracked Identity.

### Slightly more formal version

**Binding**
A Binding is a managed relation that asserts correspondence between one Source Identity and one Tracked Identity. It represents the result of identity resolution and enables source data to be associated with the appropriate SEAD domain entity. A binding carries provenance and lifecycle state, may be created by automated or manual processes, and is retained historically even when no longer current.

### One design question to settle next

The most important remaining question for Binding is probably:

**Should Binding be versioned as a first-class historical object, or should you only keep status changes on a single persistent binding record?**

My recommendation is:

* keep **Binding** as a first-class historical object
* and use status plus timestamps to indicate currentness

That is usually cleaner than mutating one timeless link.

The next useful step would be to define either:

* **binding states** as a small state machine, or
* **identity resolution** as the process that creates bindings.



I suggest keeping it simple and policy-oriented rather than overly technical.

## Binding state machine

If **Binding** is a first-class historical object, then a small state machine is the right next step.

A **Binding** begins when a possible correspondence between a **Source Identity** and a **Tracked Identity** has been established, either automatically or manually. It then moves through review and resolution states until it becomes authoritative, is rejected, or is retired from active use.

### Suggested states

**Proposed**
A candidate binding has been created, but is not yet authoritative. It may have been produced by automated matching, manual curation, or allocation logic.

**Confirmed**
The binding has been accepted as valid and is the active authoritative correspondence between the Source Identity and the Tracked Identity.

**Rejected**
The proposed binding has been assessed and found to be incorrect or unacceptable. It is retained historically, but is not valid for active use.

**Superseded**
The binding was previously confirmed, but has been replaced by another binding that is now authoritative. It is retained historically for audit and traceability.

**Invalidated**
The binding is no longer valid for active use, but has not necessarily been replaced by another binding. It is retained for history, audit, and traceability and must not be treated as current.

### Allowed transitions

I would suggest these transitions:

* **Proposed → Confirmed**
  when the candidate correspondence is accepted

* **Proposed → Rejected**
  when the candidate correspondence is reviewed and refused

* **Confirmed → Superseded**
  when a different binding becomes the authoritative one

* **Confirmed → Invalidated**
  when the binding is withdrawn without replacement

* **Rejected → Proposed**
  optionally allowed, but only by creating a **new binding**, not by reactivating the old one

* **Invalidated → Proposed**
  also only through creation of a **new binding**, not by reviving the invalidated one

* **Superseded** and **Rejected** should normally be terminal states

* **Invalidated** should also normally be terminal

That last point is important if you want clean history.

### Recommended rule

> A binding record should not be reactivated once it has left the active path. Any renewed resolution should create a new Binding record.

This fits your wish to keep Binding as a historical object.

### State meanings in one line

* **Proposed** = candidate
* **Confirmed** = active and authoritative
* **Rejected** = assessed and refused
* **Superseded** = replaced by a newer authoritative binding
* **Invalidated** = no longer valid, without implying replacement

### Recommended constraint

> A Source Identity may have many historical bindings, but normally at most one current Confirmed binding at a given time.

You may also want the mirror rule:

> A binding in state Confirmed is considered current unless and until it is Superseded or Invalidated.

### Compact state machine

In compact form:

```text
Proposed -> Confirmed
Proposed -> Rejected
Confirmed -> Superseded
Confirmed -> Invalidated
```

With the rule:

```text
Rejected, Superseded, and Invalidated are terminal historical states.
Any renewed matching creates a new Proposed binding.
```

### A more formal textual definition

**Binding State Machine**
A Binding is created in the **Proposed** state when a candidate correspondence between a Source Identity and a Tracked Identity is identified. If accepted, it transitions to **Confirmed**, where it becomes the active authoritative binding. If refused, it transitions to **Rejected**. A confirmed binding may later transition to **Superseded** if replaced by another confirmed binding, or to **Invalidated** if it is withdrawn without replacement. Rejected, superseded, and invalidated bindings remain in the repository as historical records and are not reactivated; any later resolution must create a new binding record.

### One small modeling suggestion

You may want to define **currentness** as derived, not stored:

* a binding is **current** if state = Confirmed and it has not been ended by supersession or invalidation

That keeps the model cleaner.


Yes. Here is a definition that fits the model you now have.

## Identity Resolution

Identity Resolution is the process by which SEAD determines whether a Source Identity corresponds to an existing Tracked Identity, requires a new Tracked Identity to be allocated, or cannot yet be resolved. It operates within the context of a Source Scope and evaluates the identity signals associated with a Source Identity, such as local identifiers, authority identifiers, business keys, alternative identifiers, and other matching evidence. The outcome of identity resolution is expressed through Binding records: when a plausible correspondence is found, a Proposed Binding is created; that proposal may then become Confirmed, be Rejected, or remain unresolved pending further evidence or review. Identity Resolution therefore serves as the decision process that connects externally expressed identities to SEAD-managed identities before change requests are bundled and ingestion proceeds.

### Core properties:

* **Resolution process**: it determines how a Source Identity should relate to SEAD’s Tracked Identities
* **Scope-aware**: it interprets Source Identities within a defined Source Scope
* **Evidence-based**: it uses identifiers, keys, provenance, and other matching signals as resolution evidence
* **Binding-producing**: it creates Proposed Bindings as explicit candidate correspondences
* **May allocate tracked identities**: when no suitable existing Tracked Identity is found, it may result in allocation of a new one
* **Supports multiple outcomes**: a proposal may become Confirmed, Rejected, or remain unresolved
* **Precedes change request bundling**: identity resolution should complete before data is packaged into a Change Request
* **Supports automation and curation**: it may be performed by rules, matching logic, or manual review
* **Preserves traceability**: its outcomes are retained through Binding history and related provenance
* **Does not require materialization**: resolution may succeed even if the tracked entity is not yet materialized in SEAD

### Suggested outcomes

I think it helps to make the outcomes explicit:

#### 1. Match existing tracked identity

A suitable existing Tracked Identity is found.

Outcome:

* create Proposed Binding
* later Confirm or Reject it

#### 2. Allocate new tracked identity

No suitable Tracked Identity exists, but resolution determines that a new SEAD identity should be created.

Outcome:

* allocate new Tracked Identity
* create Proposed Binding to it
* later Confirm or Reject it

#### 3. Unresolved

Resolution cannot determine a reliable correspondence.

Outcome:

* no Confirmed Binding
* optionally no Binding at all, or a still-open Proposed Binding depending on your workflow
* the Source Identity remains unresolved pending review or more evidence

### Recommended formal wording for unresolved

You asked for “Confirmed, Rejected, or unresolved outcomes.”
I suggest treating **unresolved** as a process outcome, not necessarily a Binding state.

That gives you a clean separation:

* **Binding states**: Proposed, Confirmed, Rejected, Superseded, Invalidated
* **Resolution outcomes**: confirmed, rejected, unresolved

This is cleaner because unresolved may mean:

* no candidate found
* too many candidates found
* insufficient evidence
* deferred by QA or curation

So I would define it like this:

**Unresolved**
An identity resolution outcome in which no authoritative correspondence between a Source Identity and a Tracked Identity can yet be established. An unresolved outcome may arise because no candidate exists, multiple candidates remain possible, or available evidence is insufficient for confirmation.

### Suggested process description

A compact process flow could be:

```text id="3b5lz0"
Source Identity observed
-> identity signals evaluated within Source Scope
-> candidate Tracked Identity found, or new Tracked Identity allocated, or no reliable match found
-> Proposed Binding created where applicable
-> proposal reviewed or validated
-> outcome: Confirmed, Rejected, or Unresolved
```

### Slightly more formal process definition

**Identity Resolution Process**
Identity Resolution begins when a Source Identity is observed in a Submission and interpreted within its Source Scope. The process evaluates available identity evidence to determine whether the Source Identity corresponds to an existing Tracked Identity, requires a new Tracked Identity, or cannot yet be matched reliably. Where a candidate correspondence exists, a Proposed Binding is created as an explicit historical assertion. That proposal may subsequently be Confirmed or Rejected through automated or manual review. If no authoritative correspondence can be established, the Source Identity remains unresolved until additional evidence, curation, or policy decisions allow resolution.

### One modeling recommendation

I recommend you explicitly distinguish these two things:

* **Identity Resolution** = the process
* **Binding** = the historical decision object produced by the process

That makes the model much easier to explain.

A neat one-line summary of the whole system is now:

> Identity Resolution interprets a Source Identity within a Source Scope and determines whether it should bind to an existing or newly allocated Tracked Identity, with the outcome recorded through Binding history.


## Change Request

A Change Request is a governed package of proposed changes to SEAD domain data, created after identity resolution has established how the incoming data relates to SEAD’s tracked identities. It serves as the unit of review, quality assurance, approval, and eventual ingestion into the SEAD data model. A Change Request does not define source identities, tracked identities, or bindings; rather, it depends on them. Its role is to bundle proposed creations, updates, and other domain-level changes for entities whose identities have already been resolved, so that those changes can be assessed and either accepted, rejected, or deferred.

### Why this fits your model

This definition keeps the layers clean:

* **Identity Resolution** decides *what entity this is*
* **Binding** records that decision
* **Tracked Identity** provides the SEAD-side identity anchor
* **Change Request** proposes *what should happen to the SEAD data because of that decision*

So the CR is about **domain change governance**, not identity formation.

### Core properties

* **Governed change package**: it bundles proposed domain-level changes for review and approval
* **Post-resolution artifact**: it is created only after relevant source identities have been resolved
* **Depends on identity decisions**: it uses tracked identities and bindings as prerequisites
* **Supports ingestion control**: it is the unit that may be accepted, rejected, blocked, or deferred by QA
* **May include creates and updates**: it can propose materializing new entities or changing existing ones
* **Independent of binding semantics**: it does not itself decide whether a source identity corresponds to a tracked identity
* **Traceability-bearing**: it should preserve links to submissions, source identities, tracked identities, and bindings
* **May never be ingested**: a rejected or indefinitely blocked CR does not invalidate the prior history of identity resolution, though related tracked identities or pending allocations may later be invalidated according to policy
* **Supports curation as well as ingestion**: it may arise from external ingest workflows or internal repository maintenance

### Relation to Identity Resolution

I would define the relation like this:

**Relation between Identity Resolution and Change Request**
Identity Resolution precedes Change Request creation. Before source-derived changes can be bundled into a Change Request, the relevant Source Identities must be resolved to Tracked Identities, and any required Bindings must have been created. A Change Request therefore operates on already-resolved identities and expresses proposed domain changes against those identities.

That gives you a strong rule:

> No source-derived entity change should enter a Change Request until its identity has been resolved.

This seems fully aligned with what you said earlier.

### Relation to Tracked Identity

This is also important:

**Relation between Tracked Identity and Change Request**
A Change Request may refer to one or more Tracked Identities as the SEAD-side identity anchors of the entities it proposes to create, update, or otherwise affect. A Tracked Identity may already correspond to a materialized entity in SEAD, or it may represent an entity that would only become materialized if the Change Request is accepted.

That is a nice way to express the “pre-materialization” case.

### Relation to Binding

**Relation between Binding and Change Request**
A Change Request may rely on confirmed Bindings to establish which Tracked Identities source-derived changes apply to. The Change Request does not create the semantic correspondence itself; it consumes the correspondence already recorded through Binding.

### Relation to Submission

You may also want this:

**Relation between Submission and Change Request**
A Submission provides the source data and provenance from which Source Identities are observed and resolved. After identity resolution, the resulting domain changes may be grouped into one or more Change Requests for review and ingestion.

That leaves you room for:

* one submission → one CR
* one submission → several CRs
* several submissions → one CR, if needed later

So I would avoid making that cardinality too strict yet.

### Lifecycle role of Change Request

A small lifecycle statement may help:

A Change Request can be:

* **Prepared**
* **Under Review**
* **Accepted**
* **Rejected**
* **Deferred / Blocked**

You do not need to formalize that fully yet, but it is helpful to note that this lifecycle is distinct from Binding lifecycle.

### Important distinction to preserve

This is probably the key sentence:

> Identity Resolution establishes identity correspondence; Change Request governs whether the resulting domain changes are accepted into SEAD.

That separates semantic identity from governance and ingestion.

### Compact diagram wording

**Change Request**
A governed package of proposed SEAD domain changes based on already-resolved identities.

### Slightly more formal final wording

**Change Request**
A Change Request is a governed package of proposed domain-level changes to SEAD, created after identity resolution has determined how relevant source identities correspond to tracked identities. It is the unit through which proposed creations, updates, and related data changes are reviewed, quality-assured, approved, rejected, or deferred before ingestion into the SEAD data model. A Change Request depends on prior identity resolution and binding, but does not itself define identity correspondence.

At this point, you have the core conceptual chain:

* **Source Scope**
* **Submission**
* **Source Identity**
* **Tracked Identity**
* **Binding**
* **Identity Resolution**
* **Change Request**

The next useful step would be to write these as one consolidated conceptual model with relations and cardinalities.
Here is a consolidated conceptual model draft that brings the concepts together in one place.

------------------------------------------------------------
