This is a promising start. The draft already shows the core problem clearly: you need a stable layer that can connect identifiers from incoming source data to entities in SEAD, while keeping provenance, change history, and the possibility that the target entity does not yet exist.

My main impression is that the model currently mixes three things that should probably be separated more explicitly:

1. **Reference data from the source**
2. **The identity/binding decision**
3. **The actual target entity or schema object in SEAD**

That separation will make the conceptual model much easier to describe, implement, and reason about.

## What already looks good

The strongest ideas in the draft are:

* **Source Entity Reference** as a first-class object. That is exactly the right direction. The external record should not be treated as “the same thing as” a SEAD entity.
* **Tracked Entity Reference** as a distinct target-side concept. This suggests you are not binding directly to arbitrary tables/rows, but to a controlled identity layer.
* **Binding** as an explicit relation rather than an implicit assumption.
* Inclusion of **fingerprints**, **business key**, **alternative IDs**, **authority IDs**, and **provider system ID**. These are all important matching signals.
* The hint that a binding may point to an **existing or future entity in SEAD**. That is very important and worth keeping.

## Main issues I see

### 1. “Tracked Entity Reference” is still a bit unclear

It is not yet obvious whether this means:

* a reference to a concrete row in SEAD,
* a durable identity object above SEAD rows,
* a polymorphic pointer to different table types,
* or a future placeholder for an entity not yet materialized.

This concept is central, so it needs a crisp definition.

### 2. “Binding” needs more semantics

Right now Binding appears as a simple association. It probably needs to carry more meaning, such as:

* match status
* confidence
* asserted by whom/what
* when created
* whether it is current
* basis/evidence for the decision
* whether it caused create/update/no-op

Without that, the important logic ends up scattered elsewhere.

### 3. “Source Entity Reference” mixes identity and event data

Some properties shown around Source Entity Reference look like stable identity descriptors, while others look like submission-specific or processing-specific facts.

For example:

* provider system ID, alternative IDs, authority ID, business key: likely part of the source identity profile
* operation create/update: probably submission or processing context
* fingerprint: maybe submission-version specific rather than identity-intrinsic

This is a sign you may need a distinction between:

* the **source identity reference**
* and the **observed version of that reference in a submission**

### 4. Submission / Data Provider / Change Request relationships are not fully resolved

The upper-left and upper-middle part suggests provenance and governance, but the semantics are still loose:

* Does a submission create source references?
* Does it only carry observations of them?
* Does a change request create bindings?
* Or does it approve schema-level changes needed to support new bindings?

Those are different roles.

### 5. “Allocation” and “Identity Repository” are not yet integrated

These appear as important concepts, but they are floating. I cannot yet tell whether:

* the identity repository stores tracked identities,
* allocation is the act of assigning a source to a target identity,
* allocation creates a new tracked identity,
* or allocation is just a special kind of binding.

## Questions I would want clarified

These are the most important questions before tightening the conceptual model.

### About the target side

1. Is a **Tracked Entity Reference** intended to represent:

   * a real SEAD entity instance,
   * a durable identity independent of storage,
   * or a pointer to any SEAD object including schema objects like table/column?

2. Are you trying to support only **domain entities** in SEAD, or also **schema-level objects** such as table and column, as your right-hand side suggests?

3. Can one tracked identity survive changes in the underlying SEAD representation?
   For example, if an entity is moved, split, merged, or re-keyed in SEAD, does the tracked identity remain stable?

### About matching and cardinality

4. Can one **Source Entity Reference** bind to more than one tracked identity?

   * never
   * temporarily during ambiguity
   * yes, for one-to-many mappings

5. Can several source references bind to the same tracked identity?
   I assume yes, but it should be explicit.

6. Are bindings intended to be:

   * single current binding plus history
   * or multiple concurrent bindings with roles/statuses?

### About ingestion and time

7. Is a source reference something stable across deliveries, or is it recreated per submission?

8. Do you need to distinguish:

   * the external entity as known from a provider
   * versus each observed state of that entity in a specific delivery?

9. Can bindings change over time?
   Example: initially unmatched, then matched to one identity, later corrected to another.

### About governance

10. Who or what creates bindings?

* automated match process
* human curator
* import workflow
* manual correction

11. Do you need to record evidence for a binding decision?
    For example: exact identifier match, fingerprint similarity, human review.

12. What is the role of **Change Request**?
    Is it:

* a request to alter schema,
* a request to alter identity mappings,
* or a generalized workflow object for both?

### About lifecycle

13. What should happen when source data refers to something that does not yet exist in SEAD?

* create placeholder tracked identity
* create a pending binding
* raise a review task
* reject import

14. Do you need merge/split semantics?
    Example:

* two source identities later found to be same target
* one source identity later split into two target entities

These are usually where identity systems become tricky.

---

# Suggested conceptual restructuring

I would strongly consider organizing the model around these core concepts.

## 1. Source System

The external system or provider namespace from which identifiers originate.

Examples:

* data provider
* source dataset
* authority registry
* internal provider database

This gives context to source identifiers.

## 2. Submission

A specific delivery or import event from a source provider.

This is an event/container concept, not an identity concept.

It should capture:

* provider
* date/time
* version
* batch
* delivery metadata

## 3. Source Entity Reference

A durable representation of “how the external world identifies this thing.”

This should represent the source-side identity, not the observed state in one file.

Possible attributes:

* source system
* source entity type
* provider system ID
* business key
* alternative IDs
* authority ID
* natural key serialization
* canonical label/value if useful

This is probably the thing that should persist across multiple submissions.

## 4. Source Entity Observation

This may be the missing concept in your draft.

It represents the appearance of a Source Entity Reference in a particular submission.

Possible attributes:

* submission
* observed payload
* fingerprint of observed source data
* operation type from submission: create/update/delete/upsert
* observed at
* raw key values as submitted

Why this helps:

* It separates stable source identity from batch-specific change events.
* It lets you compare “same external thing across deliveries.”

## 5. Tracked Identity

I would consider renaming **Tracked Entity Reference** to something like:

* Tracked Identity
* Identity Record
* Managed Identity
* Target Identity

This concept should be the durable identity object in your identity layer.

It is not necessarily the SEAD row itself. Instead, it is the thing to which source references bind.

Possible attributes:

* tracked identity ID
* SEAD UUID if materialized
* SEAD ID if relevant
* target entity type
* target locator/pointer
* lifecycle state
* fingerprint of target-side representation

This is the anchor of the identity repository.

## 6. Target Representation

If needed, separate the identity from the actual SEAD object.

For example:

* Tracked Identity → represents the concept in the identity layer
* SEAD Entity Link → points to the current materialization in SEAD

This is especially useful if target storage can change or if some identities are only placeholders.

## 7. Binding

This should become a rich association object.

A Binding is the claim that a given Source Entity Reference corresponds to a given Tracked Identity.

Suggested attributes:

* binding ID
* source entity reference
* tracked identity
* status
* method
* confidence
* evidence
* asserted by
* asserted at
* valid from / valid to
* current flag
* review note

Possible statuses:

* proposed
* confirmed
* rejected
* superseded
* ambiguous
* pending creation

This would make Binding the heart of the decision logic.

## 8. Identity Repository

This is the store containing:

* tracked identities
* source entity references
* bindings
* possibly matching evidence/history

This should not be a floating box. It should be the bounded context that manages the identity layer.

---

# Relations I would suggest

A cleaner relation set could look like this:

* **Data Provider** submits many **Submissions**
* **Submission** contains many **Source Entity Observations**
* **Source Entity Observation** refers to one **Source Entity Reference**
* **Source Entity Reference** originates from one **Source System / Provider Namespace**
* **Source Entity Reference** may have zero, one, or many historical **Bindings**
* One current **Binding** links a **Source Entity Reference** to one **Tracked Identity**
* **Tracked Identity** may be linked to zero or one current **SEAD Entity**
* Many **Source Entity References** may bind to the same **Tracked Identity**
* **Tracked Identity** is managed by the **Identity Repository**

That structure gives you clean provenance and history.

## Cardinality assumptions to decide explicitly

I recommend deciding and documenting:

* Many source refs → one tracked identity: **yes**
* One source ref → many tracked identities: usually **no**, except temporary ambiguity states
* One tracked identity → many SEAD materializations: probably **no**, unless versioning or polymorphism requires it
* One submission → many observations: **yes**
* One source reference → many observations over time: **yes**

---

# State model suggestion

A small state machine would help a lot.

## For Source Entity Reference / Binding lifecycle

You could model the identity resolution lifecycle as:

**Observed**
The source entity appears in a submission.

**Registered**
A stable source reference has been recognized/created in the identity repository.

**Matched (Proposed)**
A candidate tracked identity has been found automatically or manually proposed.

**Bound (Confirmed)**
The source reference is confirmed to correspond to a tracked identity.

**Materialized**
The tracked identity is linked to an actual SEAD entity.

**Rebound / Superseded**
The earlier binding was replaced by a later authoritative correction.

**Retired**
The source reference is obsolete or no longer used.

A simpler version:

* new
* candidate
* confirmed
* ambiguous
* rejected
* superseded
* retired

## For Tracked Identity lifecycle

A tracked identity may have its own lifecycle:

* placeholder
* active
* merged
* split
* deprecated
* retired

That is useful if you ever need identity maintenance independent of source submissions.

---

# Core use cases to model semantically

These use cases are probably enough for a first conceptual model.

## 1. Exact match to existing identity

A submission contains a source entity whose authoritative ID or stable source key matches an already-known source reference, which is already bound to a tracked identity.

Outcome:

* register observation
* reuse existing source reference
* follow current binding
* update or confirm target linkage

## 2. New source reference, existing target identity

A new source reference is encountered, but matching logic determines it is the same real-world entity as an existing tracked identity.

Outcome:

* create source reference
* create proposed/confirmed binding to existing tracked identity

## 3. New source reference, new target identity

A source reference does not match anything known and should create a new managed identity.

Outcome:

* create source reference
* create tracked identity placeholder
* create binding
* later materialize in SEAD

## 4. Ambiguous match

The source reference could correspond to multiple tracked identities.

Outcome:

* create source reference or observation
* create candidate matches
* set status ambiguous / needs review
* do not materialize until resolved

## 5. Correction of an earlier binding

A previous mapping was wrong.

Outcome:

* old binding superseded
* new binding becomes current
* keep full history

## 6. Merge / split

Two tracked identities are merged, or one is split.

Outcome:

* source bindings may be migrated or branched
* preserve lineage and audit trail

These use cases will help you describe interaction rules very clearly.

---

# Naming suggestions

A few names may be worth revisiting.

## “Source Entity Reference”

This is pretty good. Alternatives:

* External Entity Reference
* Source Identity
* External Identity Reference

## “Tracked Entity Reference”

This is the least clear term in the diagram.

I would consider:

* Tracked Identity
* Managed Identity
* Target Identity
* Identity Record

If this object is really the anchor in the identity repository, “Tracked Identity” is probably clearer.

## “Binding”

Good term, but define it carefully:

> A binding is an explicit, versioned assertion that a source entity reference corresponds to a tracked identity.

## “Allocation”

Unclear at the moment. It sounds like one of:

* creation of a new tracked identity
* assignment of a source to a tracked identity
* reservation of a target ID

I would either define it sharply or remove it from the first conceptual version.

## “Fingerprint”

Also important to define precisely:

* Is it a hash of source payload?
* Is it a similarity signature?
* Is it deterministic?
* Is it stable across harmless formatting changes?

You may want two terms:

* **source fingerprint**
* **target fingerprint**
  and be explicit about what they are for.

---

# What I would improve in the diagram itself

## Separate object types more rigorously

Right now the colors suggest different categories, which is good, but the semantics could be more systematic.

For example:

* yellow = actors/events
* green = identity-layer entities
* blue diamond = relationship/process object
* grey = attributes
* pale blue = notes/definitions
* dark blue = external system / bounded context

That would make the visual language easier to follow.

## Distinguish entities from attributes from notes

Some surrounding bubbles look like attributes, some like explanatory comments, some like real entities. They should look different.

For example:

* “A fingerprint of source data” is a note, not an entity
* “Created At” is an attribute
* “Submission” is an entity/event
* “Operation” may be event metadata, not an attribute of source identity

## Add cardinalities

Even a conceptual model benefits from explicit multiplicities:

* one-to-many
* many-to-one
* optional vs mandatory

## Add temporal/history semantics

Show whether Binding is:

* current only
* or historical/versioned

A simple “current binding” marker plus “binding history” concept may be enough.

## Show whether Tracked Identity can exist before SEAD entity creation

This seems likely central to your design. If so, make it explicit:

* Tracked Identity may exist without a concrete SEAD instance.

That is a very useful concept.

---

# A possible concise conceptual definition set

Here is a draft vocabulary you could refine.

**Data Provider**
An organization or system that delivers source data to SEAD.

**Submission**
A specific delivered batch or transaction of source data from a data provider.

**Source Entity Reference**
The durable representation of an entity identity as expressed by an external source system.

**Source Entity Observation**
The occurrence and observed state of a source entity reference in a specific submission.

**Tracked Identity**
The durable identity object managed by the identity repository, representing the target-side referent independently of current SEAD storage details.

**Binding**
A versioned assertion linking a source entity reference to a tracked identity, with status, provenance, and evidence.

**SEAD Entity Link**
The link from a tracked identity to the current concrete representation in SEAD.

**Identity Repository**
The subsystem that manages source references, tracked identities, bindings, and their histories.

---

# My strongest recommendation

Before refining the diagram further, I would pick one of these two architectural stances:

## Option A: Lightweight mapping registry

You only need:

* source reference
* target reference
* binding
* submission provenance

This is simpler, but weaker for lifecycle/history.

## Option B: Full identity layer

You manage:

* source reference
* source observation
* tracked identity
* binding history
* target materialization
* review/match workflow

Your draft already leans strongly toward **Option B**, and I think that is the better long-term design for SEAD.

---

# Suggested next step

I would recommend that we next turn this into a compact **textual conceptual model** with:

* concept definitions
* relation definitions with cardinalities
* 4–6 core use cases
* one small lifecycle/state machine for binding resolution

That would give you a stable foundation before redrawing the diagram. If you want, I can draft that conceptual model in a more formal style next.

