# Implementation View

## Purpose

This document is the implementation-level view of the SEAD Identity System.

It sits after [REQUIREMENTS.md](./REQUIREMENTS.md) (what the system must do), [CONCEPTUAL_MODEL.md](./CONCEPTUAL_MODEL.md) (core concepts, relations, lifecycles), and [DESIGN_VIEW.md](./DESIGN_VIEW.md) (design rules and decision flow). It maps those concepts and rules to concrete implementation structures.

Domain concepts, functional requirements, lifecycles, and design rules are not restated here.

---

## Technology Context

- **PostgreSQL 16+** with `uuid-ossp` or `pgcrypto` for UUID generation.
- **Sqitch** for database change control and migration sequencing.
- **Python REST API** (FastAPI) as the service layer, hosted in the `sead_authority_service` repository (`src/identity/`).

---

## Concept-to-Structure Mapping

The table below maps each CM concept to its implementation anchor. This is the primary alignment contract between the conceptual model and the storage design.

| CM Concept              | Implementation Structure   | Notes                                                                                                                     |
|-------------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **Source Scope**        | `source_scopes` table      | Hierarchical namespace; stable across submissions                                                                         |
| **Submission**          | `submissions` table        | Temporal provenance; belongs to one Source Scope                                                                          |
| **Source Identity**     | `source_identities` table  | Persistent per scope; carries identity signals                                                                            |
| **Tracked Identity**    | `tracked_identities` table | SEAD-side UUID anchor; lifecycle per [CM § Tracked Identity Lifecycle](./CONCEPTUAL_MODEL.md#tracked-identity-lifecycle)  |
| **Binding**             | `bindings` table           | Links Source Identity → Tracked Identity; belongs to one Binding Set                                                     |
| **Binding Set**         | `binding_sets` table       | Atomic batch of Bindings; owns lifecycle, audit, and Change Request reference (FR-26)                                     |
| **Identity Resolution** | Service operation          | Stateless process; outcomes expressed as a Binding Set containing Bindings and unresolved cases                           |
| **Change Request**      | External reference (by name) | Owned by SEAD Change Control System (Sqitch); SIMS records association between Bindings and Change Request name          |

### Key structural principles

- Each CM concept owned by SIMS maps to its own table. No composite "allocation" table conflating Source Identity, Tracked Identity, and Binding.
- Binding Sets are the atomic governance unit. Lifecycle state, audit trail, and Change Request references live on the Binding Set, not on individual Bindings.
- Change Requests are external objects (owned by the SEAD Change Control System); SIMS references them by name on the Binding Set record.
- Binding Set lifecycle is expressed as a state column with allowed transitions enforced by application logic (or CHECK constraints).
- Identity Resolution is a service-layer operation, not a stored object. Its outcomes are a Binding Set.

---

## Storage Design

### Source Scopes

Represents the external namespace within which Source Identities are unique.

| Column                             | Purpose                                            |
|------------------------------------|----------------------------------------------------|
| `scope_uuid` (PK)                  | Unique identifier                                  |
| `scope_name`                       | Human-readable label                               |
| `parent_scope_uuid` (FK, nullable) | Hierarchical nesting (system → provider → dataset) |
| `description`                      | Context for the scope                              |
| Audit columns                      | `created_at`, `created_by`                         |

### Submissions

Represents a delivered batch or ingest event within a single Source Scope.

| Column                 | Purpose                                           |
|------------------------|---------------------------------------------------|
| `submission_uuid` (PK) | Unique identifier                                 |
| `scope_uuid` (FK)      | The Source Scope this submission belongs to       |
| `submission_name`      | Human-readable label                              |
| `status`               | Lifecycle state: `pending`, `completed`, `failed` |
| Audit columns          | `created_at`, `created_by`, `completed_at`        |

### Source Identities

Represents a persistent identity for a domain entity as expressed within a Source Scope.

| Column                               | Purpose                                                                |
|--------------------------------------|------------------------------------------------------------------------|
| `source_identity_uuid` (PK)          | Unique identifier                                                      |
| `scope_uuid` (FK)                    | The Source Scope this identity belongs to                              |
| `entity_type`                        | Target SEAD entity type (e.g. `site`, `sample_group`)                  |
| `identity_type`                      | `uuid`, `business_key`, `provider_key`, `authority_key`                |
| `identity_value`                     | The serialized identifier value                                        |
| `identity_signals` (JSONB, nullable) | Additional identity evidence (authority keys, alternative identifiers) |
| Audit columns                        | `created_at`, `created_by`                                             |
| **Uniqueness**                       | `(scope_uuid, entity_type, identity_type, identity_value)`             |

A Source Identity may be observed in multiple Submissions. A junction table (`submission_source_identities`) records which Submission carried which Source Identities, reflecting the M:N relation from [CM § Relations](./CONCEPTUAL_MODEL.md#relations-and-cardinalities) (relation 3).

### Tracked Identities

Represents the SEAD-side identity anchor for a domain entity.

| Column | Purpose |
|---|---|
| `tracked_identity_uuid` (PK) | The SEAD universal identity (UUID) for this entity |
| `entity_type` | Target SEAD entity type |
| `sead_internal_id` (nullable) | The SEAD integer PK, once materialized |
| `lifecycle_state` | `allocated`, `pending_materialization`, `materialized`, `invalidated` |
| Audit columns | `created_at`, `created_by`, `materialized_at` |

The `tracked_identity_uuid` **is** the SEAD universal identity (FR-1). Where SEAD entity tables already have `{entity}_uuid` columns, those columns are reused directly — no new UUID columns are introduced (FR-3). The `sead_internal_id` maps to the relational PK (FR-2).

**Design decision:** Creating historical Binding records for UUIDs that predate SIMS deployment is out of scope. Pre-existing `{entity}_uuid` values are treated as authoritative Tracked Identities without provenance tracking.

### Binding Sets

Represents the atomic batch of identity resolution outcomes. Owns lifecycle, audit, and Change Request reference.

| Column                           | Purpose                                                                                           |
|----------------------------------|---------------------------------------------------------------------------------------------------|
| `binding_set_uuid` (PK)          | Unique identifier                                                                                 |
| `submission_uuid` (FK, nullable) | The Submission that triggered this resolution batch                                               |
| `lifecycle_state`                | `proposed`, `confirmed`, `rejected`, `superseded`, `invalidated`                                  |
| `change_request_name` (nullable) | Sqitch change name linking this Binding Set to a Change Request in the SEAD Change Control System |
| Audit columns                    | `created_at`, `created_by`, `confirmed_at`                                                        |

Lifecycle transitions follow [CM § Binding Set Lifecycle](./CONCEPTUAL_MODEL.md#binding-set-lifecycle). All Bindings within a set share the set’s lifecycle state.

### Bindings

Represents one source-to-tracked identity correspondence within a Binding Set.

| Column                         | Purpose                                                                                  |
|--------------------------------|------------------------------------------------------------------------------------------|
| `binding_uuid` (PK)            | Unique identifier                                                                        |
| `binding_set_uuid` (FK)        | The owning Binding Set                                                                   |
| `source_identity_uuid` (FK)    | The Source Identity                                                                      |
| `tracked_identity_uuid` (FK)   | The Tracked Identity                                                                     |
| `method`                       | How the binding was established (e.g. `exact_match`, `business_key`, `manual`, `policy`) |
| `provenance` (JSONB, nullable) | Supporting evidence, resolution context                                                  |

A Source Identity normally has at most one Binding within a current confirmed Binding Set at any time.

### Change Request References

Change Requests are owned by the SEAD Change Control System (Sqitch) and referenced by their unique Sqitch change name. SIMS does not store or manage Change Request state.

The `binding_sets` table carries an optional `change_request_name` column linking a confirmed Binding Set to the Change Request it supports. This is the sole integration point between SIMS and the Change Control System.

---

## Core Operations

These operations implement the decision flow defined in [DESIGN_VIEW.md § Decision flow](./DESIGN_VIEW.md#decision-flow). They map directly to the three-step sequence: Identity Resolution → Binding (within a Binding Set) → Change Request.

### 1. Resolve Identity

Implements step 1 of the decision flow: **Identity Resolution**.

**Input:** Source Identity (within a Source Scope), entity type, identity signals.

**Behavior:**

1. Look up the Source Identity within its scope. If it already has a confirmed Binding, return that Tracked Identity.
2. Evaluate incoming identity signals against existing Tracked Identities using matching rules appropriate to the entity type:
   - Provider-owned entities: match by provider key or business key.
   - Shared metadata entities: reconciliation against existing SEAD definitions (FR-17). Reconciliation procedure is owned by the SEAD Shape Shifter workflow, not SIMS (see design decision below).
   - If reconciliation fails for shared metadata, surface unresolved state rather than allocating (FR-20).
3. Return one of: `matched` (existing Tracked Identity found), `unresolved` (no match, allocation blocked by policy), or `new` (no match, allocation permitted).

**Design decision:** Specifying the procedure for reconciling shared metadata entities is out of scope for SIMS. Reconciliation is a concern of the SEAD Shape Shifter workflow, which performs semi-automatic reconciliation of incoming shared entities and generates a separate Change Request for them as part of the submission workflow. SIMS consumes the reconciliation outcome (matched or unresolved) but does not define matching rules.

**Idempotency:** The same identity signals within the same scope always produce the same resolution outcome (FR-12, FR-13).

### 2. Bind

Implements step 2 of the decision flow: **Binding**.

**Input:** Resolution outcomes from step 1 (one or more resolved Source Identities).

**Output:** A Proposed Binding Set containing individual Bindings.

**Behavior:**

- Create a new Binding Set in `proposed` state.
- For each resolved Source Identity:
  - If `matched`: create a Binding within the set linking the Source Identity to the existing Tracked Identity.
  - If `new`: allocate a new Tracked Identity (mint UUID; optionally reserve integer PK), then create a Binding within the set.
  - If `unresolved`: record the unresolved case for later review. No Binding is created for this Source Identity.

**Policy enforcement** (applied between Resolution and Binding per [DV § Policy boundary](./DESIGN_VIEW.md#policy-boundary)):

- Evaluate whether a provider-supplied UUID is accepted as the SEAD universal identity or retained only as a provider key (FR-11).
- Evaluate whether an unmatched shared metadata entity triggers allocation or is held as unresolved.

**Design decision:** Identity policy (FR-11) is stored as a configuration file for the initial release. This is sufficient given the small number of entity types and the low rate of policy changes. The representation may evolve to a database table or API-managed resource in future releases if runtime administration becomes necessary. Policy enforcement may also become a Shape Shifter responsibility as part of its quality-assurance workflow, in which case SIMS would consume policy decisions rather than evaluate them directly.

Proposed Binding Sets may be confirmed automatically (for provider-owned entities with high-confidence matches) or require review (for shared metadata entities or low-confidence matches).

### 3. Associate with Change Request

Implements step 3 of the decision flow: **Change Request** association.

**Input:** A confirmed Binding Set and an externally provided Change Request name (Sqitch change name).

**Behavior:**

- Record the association between the confirmed Binding Set and the named Change Request by setting `change_request_name` on the Binding Set.
- The Change Request itself is created and managed by the SEAD Change Control System, not by SIMS.
- SIMS does not alter identity correspondence when recording this association (FR-25).

**Design decision:** For the initial release, SIMS stores only a reference (the Sqitch change name) to the SEAD Change Control System. It does not query Change Request status or store additional Change Request metadata. Integration between the two systems is intentionally loose and may be tightened in future releases beyond the initial SIMS scope.

### 4. Detect Change (Update Foundation)

Supports FR-24 (aggregate-level change detection) and FR-25 (identity independent of mutation).

**Input:** A Tracked Identity and a content hash provided by the submitting system.

**Behavior:**

- The submitting system (typically Shape Shifter) computes a deterministic content hash over the aggregate payload — the root entity row plus all owned child rows as defined by the target model's `aggregate_parent` hierarchy.
- SIMS receives the content hash as an opaque fingerprint and compares it against the stored hash for the Tracked Identity.
- Returns: `insert` (no prior hash — new entity), `update` (hash differs — content changed), or `skip` (hash matches — content unchanged).

**Design decision:** Aggregate content hashing (field selection, child-row inclusion, normalization, ordering) is the responsibility of the submitting system, not SIMS. The target model's `aggregate_parent` field defines aggregate boundaries; Shape Shifter already uses this metadata for topological processing and is the natural place to own hash computation. Routing all aggregate data through SIMS solely for hashing would conflate identity management with data transformation. SIMS requires only that the hash is deterministic — the same aggregate content always produces the same hash — to support reliable change detection.

This operation feeds into Change Request association: detected changes become proposed updates associated with a Change Request.

---

## Identity Intake Rules

These rules make concrete the identity intake patterns from [REQUIREMENTS.md § Identifier intake requirements](./REQUIREMENTS.md#identifier-intake-requirements). Identity signals are carried by Source Identities and evaluated during Identity Resolution.

### UUID intake

When a provider supplies a UUID:

- Identity policy determines whether it is accepted as the SEAD universal identity or recorded only as a provider key (FR-11).
- If accepted, the UUID becomes the Tracked Identity UUID directly.
- If not accepted, the provider UUID is retained as a Source Identity signal (provider key) for traceability.

### Business-key intake

When a provider supplies a natural key or key set:

- The submitting system (typically Shape Shifter) constructs a deterministic serialized string from the provider's data, using the `identity_columns` defined in the target model (`sead_standard_model.yml`).
- SIMS receives the serialized string as an opaque token and stores it as the Source Identity's `identity_value` with `identity_type = 'business_key'`.
- SIMS does not interpret the internal structure of the business key. It uses the string solely for equality comparison and uniqueness enforcement.
- Used for resolution against existing Tracked Identities or existing SEAD data.

**Design decision:** Business-key serialization (field selection, ordering, normalization) is the responsibility of the submitting system, not SIMS. Different data providers have different schemas; only the submitting system (Shape Shifter) understands the column-level mapping from provider data to target model fields. SIMS requires only that the serialized string is deterministic within a Source Scope — the same entity with the same input always produces the same string — to guarantee idempotency (FR-12, FR-13).

### Authority-key intake

When an external authority identifier is available (e.g. GeoNames, Wikidata):

- It is recorded in the Source Identity's `identity_signals` alongside other evidence.
- It may contribute to reconciliation for shared metadata entities (FR-10).
- It is preserved distinctly from provider keys and SEAD universal identity.

---

## Entity Metadata

The identity system needs to know which SEAD tables are tracked entities, their subtypes, aggregate boundaries, and FK relationships. This metadata drives resolution strategy selection, allocation ordering, and change-detection scope.

### What the system needs per tracked entity

| Attribute                 | Purpose                                                                                      |
|---------------------------|----------------------------------------------------------------------------------------------|
| Entity type and PK column | Target for Tracked Identity allocation                                                       |
| Entity subtype            | Governs intake rules and resolution strategy (provider-owned, shared metadata, relationship) |
| Aggregate membership      | Defines aggregate boundaries (used by submitting system for content hashing)                  |
| FK dependencies           | Determines allocation order within a Submission                                              |
| Business-key fields       | Enables business-key serialization and resolution                                            |

### Source of truth

Shape Shifter's target model (`sead_standard_model.yml`) already catalogues SEAD entities with role (fact, classifier, lookup, bridge), foreign keys, identity columns, and unique sets. That metadata overlaps substantially with what SIMS needs.

The current design intent is that SIMS consumes Shape Shifter's target model as the source of truth for entity metadata, augmented by SIMS-specific attributes (reconciliation strategy, policy overrides) stored locally. See [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) for the entity register derived from the target model.

---

## Internal Origins

Not all identity operations originate from external provider submissions. SEAD administrator actions (e.g. adding a new method or classifier) and infrastructure changes (e.g. Sqitch migrations) also produce entities that require resolved identities before they can enter a Change Request (FR-27).

### Approach

Internal origins use the same Source Scope / Submission model as external providers. Well-known internal Source Scopes represent SEAD-internal origins:

- `sead://admin` — SEAD administrator actions (adding or modifying classifiers, methods, etc.)
- `sead://migration` — Sqitch-driven schema or data migrations
- `sead://reconciliation` — Reconciliation outputs

Internal actions create Submissions within these scopes, pass through normal identity resolution, produce Binding Sets, and associate with Change Requests — the same pipeline as external provider data. No special-case handling is needed in the data model or core operations.

**Design decision:** The tooling for manually curating SEAD-administered entities and submitting them through SIMS is out of scope. SIMS provides the identity resolution API and enforces the requirement that a Change Request must reference confirmed Binding Sets (FR-27). How internal entities are prepared and submitted is the responsibility of the curation tool — whether that is an internal Shape Shifter workflow (treating SEAD admin data the same way as external provider data), a dedicated admin tool, or a lightweight CLI client. This is a tooling gap, not a SIMS design gap.

---

## Rollout Approach

Rollout is incremental. Each phase stabilizes before the next begins.

1. **Infrastructure**: Deploy identity schema, core tables, and REST API to staging. No SEAD entity tables are modified.

2. **Pilot**: Select a small set of tracked entity types (e.g. sites, sample groups). Implement resolution and binding for provider-owned entities. Validate idempotency and lifecycle correctness.

3. **Shared metadata**: Extend resolution to shared metadata entities (classifiers, lookup tables). Implement reconciliation and unresolved-state surfacing.

4. **Entity table integration**: Reuse existing `{entity}_uuid` columns on tracked SEAD entity tables. Add UUID columns only where missing. Pre-existing UUIDs are treated as authoritative without retroactive Binding records.

5. **Change Request integration**: Record associations between confirmed Binding Sets and externally managed Change Requests (Sqitch). Validate integration with the SEAD Change Control System.

Detailed rollout planning (timelines, specific table selection, migration scripts) belongs to project planning, not this document.
