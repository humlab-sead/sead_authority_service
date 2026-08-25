The conceptual model is strong: the separation between external identity, SEAD identity, identity resolution, and later domain-data mutation is clear and consistently motivated. The main opportunity is not to simplify the model, but to **reduce the cognitive load required to enter it**. At present, readers encounter several abstract terms before they have a concrete mental picture of what the subsystem actually does. 

I would make changes in four areas: terminology, ordering, a few conceptual inconsistencies, and the distinction between introductory versus authoritative material.

## 1. The most important terminology issue: “identity” is overloaded

You currently have:

* Source Identity
* Tracked Identity
* Identity Resolution
* identity signals
* canonical SEAD identity
* provider identifiers
* SEAD universal identity
* SEAD UUID

They are individually meaningful, but a junior developer can easily lose track of whether **identity means an entity, an identity record, or an identifier value**.

For example:

> “A Source Identity is a persistent identity for a domain entity…”

and:

> “Carries source identification signals: local ID, authority ID, business key…”



This makes `Source Identity` sound partly like an identifier and partly like an object containing identifiers.

I would retain the formal terms, but establish this distinction very early:

| Term                 | Plain-language interpretation                                              |
| -------------------- | -------------------------------------------------------------------------- |
| **Entity**           | The real/domain thing we are trying to identify                            |
| **Identifier**       | A value used to refer to that thing, e.g. UUID, local ID, authority ID     |
| **Source Identity**  | SEAD's persistent record of how a source identifies that thing             |
| **Tracked Identity** | SEAD's persistent identity record for that thing                           |
| **Binding**          | The recorded claim that those two identity records refer to the same thing |

That would make the rest substantially easier to understand.

I would particularly add an explicit sentence such as:

> **An Identity is not the same thing as an identifier.** A Source Identity or Tracked Identity is a persistent identity record; identifiers such as UUIDs, local IDs, and authority IDs are values associated with or used to resolve those identities.

That clarification preserves your model rather than simplifying it.

---

## 2. “Tracked Identity” is probably the hardest core term

`Source Identity` is reasonably intuitive. `Tracked Identity` is less so.

The definition itself is precise:

> “a persistent, allocated SEAD-side identity for a domain entity that SEAD manages or intends to manage”



But “tracked” does not naturally tell the reader **what side of the boundary it belongs to**. A newcomer may reasonably ask:

> Isn't the Source Identity also tracked?

Possible alternatives would be:

* **SEAD Identity**
* **Managed Identity**
* **SEAD Managed Identity**
* **Canonical Identity**

I think **SEAD Identity** would be the easiest to understand, but it risks confusion with the actual SEAD entity PK/UUID.

So I would probably **keep `Tracked Identity` as the formal model term**, but introduce it as:

> **Tracked Identity (SEAD-side identity)**

and use “SEAD-side identity” liberally in explanatory prose.

This is a good example of where adding a plain-language label is preferable to changing a carefully chosen domain term.

---

## 3. “Binding” is good; “Binding Set” needs immediate explanation

`Binding` works well. It communicates correspondence without implying that the identifiers themselves are identical.

`Binding Set`, however, sounds like a technical collection type until the governance semantics are understood.

Its real significance is:

> “the atomic unit of identity resolution output”

and that its bindings are confirmed or rejected together. 

That should be the first thing a reader learns about it.

I'd define it more directly:

> A **Binding Set** is a group of proposed identity correspondences that must be accepted or rejected as one unit.

Then give the more formal statement:

> It is the atomic unit of identity-resolution output and owns the shared lifecycle, audit history, and Change Request association for its Bindings.

That is considerably easier to enter without losing anything.

I would **not** rename it to `Resolution Batch`. “Batch” sounds transient, whereas your Binding Set has a persistent lifecycle and audit history.

---

# 4. Put DDD terminology later

The document currently goes:

1. Overview
2. Design Intent
3. Domain Modeling Foundations
4. Core Concepts

The DDD section asks the reader to understand Entity, Value Object, Aggregate, and Aggregate Root before they have learned what SIMS actually contains. 

For an architect, that's fine. For a junior developer or domain expert, it is a barrier.

I would reorder to something like:

1. **What SIMS does**
2. **The identity problem**
3. **Core concepts**
4. **How the concepts work together**
5. **Key rules**
6. **Lifecycle**
7. **Relations/cardinalities**
8. **Domain modeling foundations**
9. **Detailed design rules**
10. **Deferred issues**

DDD then becomes an explanation of *why* certain things are modeled as they are, rather than prerequisite vocabulary.

The definitions should remain authoritative.

---

# 5. Add one concrete example before the formal model

This is probably the single biggest improvement you could make for non-technical readers.

Something like:

> A provider submits a record for archaeological site `ABC-123`.
>
> Within that provider's namespace, `ABC-123` identifies a particular site. SIMS represents this as a **Source Identity**.
>
> SEAD may already know the same site under its own **Tracked Identity**. **Identity Resolution** determines whether they refer to the same site.
>
> If they do, SIMS records a **Binding** between them. Related Bindings are placed in a **Binding Set** and confirmed together.
>
> Only after identity has been resolved can the submitted data be included in a **Change Request** that may update SEAD.

Then immediately show the abstract pattern:

```text
External source                    SIMS                         SEAD
───────────────                    ────                         ────

ABC-123
   │
Source Scope
   │
Source Identity ──resolution──> Tracked Identity ───────────> SEAD entity
                         │
                      Binding
                         │
                    Binding Set
                         │
                    Change Request
```

That example would make most of the subsequent formal definitions self-explanatory.

---

# 6. The Overview is accurate but too noun-dense

This paragraph asks the reader to absorb essentially the entire vocabulary at once:

> “Source data is received through Submissions, interpreted within a Source Scope, and represented through Source Identities. These are resolved against SEAD-managed Tracked Identities through the Identity Resolution process…”



It's accurate, but almost every noun is a defined concept.

I'd make the first paragraph conceptual rather than terminological:

> SIMS answers one central question: **when an external source refers to something, which SEAD entity does it mean?**
>
> It records both the identity expressed by the source and the corresponding identity managed by SEAD. The relationship between them is resolved explicitly, governed by policy, and retained historically.

Then introduce the terminology in a second paragraph.

That gives the reader somewhere to stand.

---

# 7. I would change the canonical flow

You currently have:

> Submission → Source Scope → Source Identity → Identity Resolution → Binding Set → Change Request → Materialization



But conceptually the Submission is **within** a Source Scope:

> “A Submission … originating within a single Source Scope”



So the arrow makes it look as though a Submission produces or leads to a Source Scope.

I would represent this as either:

```text
Source Scope
    └── Submission
          └── Source Identity observation
                 ↓
          Identity Resolution
                 ↓
             Binding Set
                 ↓
           Change Request
                 ↓
          Materialization
```

or, more compactly:

```text
Submission [within Source Scope]
    ↓
Source Identities
    ↓
Identity Resolution
    ↓
Binding Set
    ↓
Change Request
    ↓
optional materialization
```

This is more faithful to your cardinalities.

---

# 8. There appears to be an actual contradiction around Change Requests

This should be resolved, rather than merely reworded.

The cardinality table says:

> Change Request — Binding Set: **M:N**
> “a Change Request consumes confirmed Binding Sets; a Binding Set may support multiple Change Requests”



But the constraints say:

> “A Binding Set may be associated with zero or **one** Change Request.”



Those describe different models.

Other prose also tends toward singular ownership/reference:

> “The Binding Set owns … the Change Request reference”



So I suspect the intended model may actually be:

```text
Change Request 1 ─── N Binding Sets
```

with:

* each Binding Set associated with 0..1 Change Request;
* one Change Request consuming many Binding Sets.

If so, relation #10 should probably be:

> **Change Request — Binding Set: 1:N**

If M:N really is required, then the Binding Set constraints and wording about “the Change Request reference” need changing.

This is the most substantive inconsistency I found.

---

# 9. “Identity Resolution — Binding Set = 1:1” deserves clarification

You state:

> Identity Resolution — Binding Set: 1:1 (resolution produces one Binding Set)



But `Identity Resolution` is elsewhere defined primarily as a **process**, not obviously as a persistent domain object. 

A reader may therefore ask:

> What exactly is one instance of Identity Resolution?

Is it:

* one invocation?
* one Submission?
* one resolution run?
* one transaction?
* one Source Identity?
* one batch?

I would either introduce **Identity Resolution Run** as the thing participating in cardinalities, or avoid giving the process itself an ER-style cardinality.

For example:

> **Resolution Run** — one execution of Identity Resolution over a defined input set. Each Resolution Run produces exactly one Binding Set.

That makes the 1:1 relationship concrete.

---

# 10. The Tracked Identity “lifecycle” is not quite a lifecycle yet

The table contains:

* Allocated
* Pending Materialization
* Materialized
* Invalidated



But `Allocated` and `Pending Materialization` appear to overlap.

If an identity is:

> “Allocated but not yet represented as an accepted SEAD entity”

then presumably it is *both allocated and pending materialization*.

Contrast this with the Binding Set lifecycle, where the states are mutually exclusive and transitions are explicit. 

I'd make this one similarly explicit, perhaps:

```text
Pending Materialization → Materialized
Pending Materialization → Invalidated
Materialized            → Invalidated   [if allowed]
```

with allocation described as the **event that creates a Pending Materialization identity**, rather than as a separate lifecycle state.

For example:

| State                       | Meaning                                                              |
| --------------------------- | -------------------------------------------------------------------- |
| **Pending Materialization** | Identity has been allocated, but no accepted SEAD entity exists yet. |
| **Materialized**            | Identity corresponds to an accepted SEAD entity.                     |
| **Invalidated**             | Identity may no longer be used, but remains permanently recorded.    |

This is both simpler and more precise.

---

# 11. Be careful with “persistent”

Both Source Identity and Tracked Identity are called “persistent identity.”

That's defensible, but `persistent` is developer-oriented language and can imply database persistence rather than domain continuity.

I'd distinguish:

> **stable identity record**

or:

> **long-lived identity record**

in introductory prose, while retaining “persistent” in formal definitions if desired.

---

# 12. “Materialization” deserves a plain-language definition

This term is used extensively but isn't included in Core Concepts.

You explain it indirectly:

> “the entity record may not yet exist in SEAD”



For non-technical readers, I would explicitly define:

> **Materialization** means creating or establishing the actual SEAD domain entity represented by an already allocated Tracked Identity.

This is important because one of the model's more unusual and important requirements is precisely that:

```text
identity can exist before entity data exists
```

That deserves highlighting rather than leaving readers to infer it.

---

# 13. “Shared metadata entity” needs to become a defined term

It carries an important behavioral rule:

> when reconciliation fails, the submission is rejected instead of allocating a new identity.



But the reader isn't told here what qualifies as a **shared metadata entity**.

Because this distinction changes system behavior, I would either:

* define `Shared Metadata Entity` in Core Concepts, or
* explicitly reference where it is defined.

Otherwise one of your strongest requirements depends upon an undefined classification.

---

# 14. Separate “what exists” from “what happens”

The Core Concepts currently mix:

### Things

* Source Scope
* Submission
* Source Identity
* Tracked Identity
* Binding
* Binding Set
* Change Request

with:

### Process

* Identity Resolution

For junior developers, I'd visually separate these:

### Domain concepts

`Source Scope`, `Submission`, `Source Identity`, `Tracked Identity`, `Binding`, `Binding Set`

### Processes

`Identity Resolution`

### External concepts referenced by SIMS

`Change Request`

That last category is especially useful because you repeatedly and correctly emphasize:

> Change Request is owned by the Change Control System, not SIMS.



Making that distinction structural would reinforce the bounded-context boundary.

---

# 15. Your Compact Summary is excellent — move something like it near the top

The table at the end is arguably the most accessible part of the document. 

I would move a slightly expanded version immediately after the Overview and call it something like:

## Concepts at a glance

I'd also add a column for **“Think of it as…”**:

| Concept          | Formal role                              | Think of it as                   |
| ---------------- | ---------------------------------------- | -------------------------------- |
| Source Scope     | Defines where a source identity is valid | Namespace                        |
| Submission       | Delivers source data                     | Delivery/import                  |
| Source Identity  | Represents source-side identity          | Source's record of “who this is” |
| Tracked Identity | Represents SEAD-side identity            | SEAD's stable identity anchor    |
| Binding          | Records correspondence                   | “These refer to the same thing”  |
| Binding Set      | Atomic governed collection               | One resolution decision batch    |
| Change Request   | Governs data changes                     | Proposed SEAD update             |

That doesn't weaken the formal definitions; it provides an entry point to them.

---

# 16. Some terminology I would explicitly keep

I would **not** simplify these away:

**Source Scope** — good term. “Namespace” alone would be narrower than your actual concept because you also include provider/dataset/project context and policy context.

**Binding** — good and precise.

**Binding Set** — keep, but explain better.

**Identity Resolution** — standard and intuitive enough.

**Change Request** — especially important to retain because it belongs to another subsystem.

**Materialization** — keep as a technical domain term, but define it.

The objective should be **dual vocabulary**, not replacement vocabulary:

> Binding Set — *a batch of identity correspondences governed as one unit*

rather than replacing `Binding Set` with something less exact.

---

# 17. One important rule deserves much greater prominence

To me, the conceptual heart of SIMS is this distinction:

> “The identity system decides *what entity* is being referred to. It does not define *how entity state* is inserted, replaced, or updated.”



That's excellent.

I would elevate it into a boxed/key principle near the beginning:

> **SIMS determines identity, not data changes.**
>
> SIMS answers *“What SEAD entity does this source entity correspond to?”*
> The Change Control System answers *“What changes should be made to that entity?”*

That single distinction gives readers a conceptual map for almost everything else in the document.

---

## Recommended overall structure

Without removing any requirement, I'd restructure the document approximately as:

1. **Purpose**

   * What problem SIMS solves
   * “SIMS determines identity, not entity state”

2. **A simple example**

   * provider ID → Source Identity → Tracked Identity

3. **Concepts at a glance**

   * short table

4. **Core Concepts**

   * authoritative definitions
   * grouped into SIMS objects / processes / external objects

5. **How Identity Resolution Works**

   * current Decision Flow

6. **Identity and Identifier Rules**

   * canonical identity versus identity signals

7. **Binding Set Lifecycle**

8. **Tracked Identity Lifecycle**

9. **Relations and Cardinalities**

10. **Constraints**

11. **Domain Modeling Foundations**

* Entity / Value Object / Aggregate

12. **Detailed Design Rules**

13. **Canonical Use Cases**

14. **Deferred Issues**

That would make it **progressively formal**: a non-technical reader can understand sections 1–5; a junior developer can continue through the lifecycle and constraints; an implementer gets the complete formal model.

The underlying model doesn't need to become less sophisticated. The key is to introduce **one distinction at a time**, and only then expose the reader to the complete terminology.
