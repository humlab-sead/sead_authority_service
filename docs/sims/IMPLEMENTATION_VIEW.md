# Implementation View

## Purpose

This document is the implementation-level view of the SEAD Identity System.

It sits after [REQUIREMENTS.md](./REQUIREMENTS.md) (what the system must do), [CONCEPTUAL_MODEL.md](./CONCEPTUAL_MODEL.md) (core concepts, relations, lifecycles), and [DESIGN_VIEW.md](./DESIGN_VIEW.md) (design rules and decision flow). It maps those concepts and rules to concrete implementation structures.

Domain concepts, functional requirements, lifecycles, and design rules are not restated here.

---

## Technology Context

- **PostgreSQL 12+** with `uuid-ossp` or `pgcrypto` for UUID generation.
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
| **Binding**             | `bindings` table           | Links Source Identity → Tracked Identity; lifecycle per [CM § Binding Lifecycle](./CONCEPTUAL_MODEL.md#binding-lifecycle) |
| **Identity Resolution** | Service operation          | Stateless process; outcomes expressed as Bindings and unresolved cases                                                    |
| **Change Request**      | External reference (by name) | Owned by SEAD Change Control System (Sqitch); SIMS records association between Bindings and Change Request name          |

### Key structural principles

- Each CM concept owned by SIMS maps to its own table. No composite "allocation" table conflating Source Identity, Tracked Identity, and Binding.
- Change Requests are external objects (owned by the SEAD Change Control System); SIMS references them by name on the Binding record.
- Binding and Tracked Identity lifecycles are expressed as state columns with allowed transitions enforced by application logic (or CHECK constraints).
- Identity Resolution is a service-layer operation, not a stored object. Its outcomes are Bindings.

---

## Storage Design

### Source Scopes

Represents the external namespace within which Source Identities are unique.

| Column | Purpose |
|---|---|
| `scope_uuid` (PK) | Unique identifier |
| `scope_name` | Human-readable label |
| `parent_scope_uuid` (FK, nullable) | Hierarchical nesting (system → provider → dataset) |
| `description` | Context for the scope |
| Audit columns | `created_at`, `created_by` |

### Submissions

Represents a delivered batch or ingest event within a single Source Scope.

| Column | Purpose |
|---|---|
| `submission_uuid` (PK) | Unique identifier |
| `scope_uuid` (FK) | The Source Scope this submission belongs to |
| `submission_name` | Human-readable label |
| `status` | Lifecycle state: `pending`, `completed`, `failed` |
| Audit columns | `created_at`, `created_by`, `completed_at` |

### Source Identities

Represents a persistent identity for a domain entity as expressed within a Source Scope.

| Column | Purpose |
|---|---|
| `source_identity_uuid` (PK) | Unique identifier |
| `scope_uuid` (FK) | The Source Scope this identity belongs to |
| `entity_type` | Target SEAD entity type (e.g. `site`, `sample_group`) |
| `identity_type` | `uuid`, `business_key`, `provider_key`, `authority_key` |
| `identity_value` | The serialized identifier value |
| `identity_signals` (JSONB, nullable) | Additional identity evidence (authority keys, alternative identifiers) |
| Audit columns | `created_at`, `created_by` |
| **Uniqueness** | `(scope_uuid, entity_type, identity_type, identity_value)` |

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

### Bindings

Represents the governed assertion linking a Source Identity to a Tracked Identity.

| Column | Purpose |
|---|---|
| `binding_uuid` (PK) | Unique identifier |
| `source_identity_uuid` (FK) | The Source Identity |
| `tracked_identity_uuid` (FK) | The Tracked Identity |
| `lifecycle_state` | `proposed`, `confirmed`, `rejected`, `superseded`, `invalidated` |
| `method` | How the binding was established (e.g. `exact_match`, `business_key`, `manual`, `policy`) |
| `change_request_name` (nullable) | Sqitch change name linking this Binding to a Change Request in the SEAD Change Control System |
| `provenance` (JSONB, nullable) | Supporting evidence, resolution context |
| Audit columns | `created_at`, `created_by`, `confirmed_at` |

Lifecycle transitions follow [CM § Binding Lifecycle](./CONCEPTUAL_MODEL.md#binding-lifecycle). A Source Identity normally has at most one Confirmed Binding at any time.

### Change Request References

Change Requests are owned by the SEAD Change Control System (Sqitch) and referenced by their unique Sqitch change name. SIMS does not store or manage Change Request state.

The `bindings` table carries an optional `change_request_name` column linking a confirmed Binding to the Change Request it supports. This is the sole integration point between SIMS and the Change Control System.

---

## Core Operations

These operations implement the decision flow defined in [DESIGN_VIEW.md § Decision flow](./DESIGN_VIEW.md#decision-flow). They map directly to the three-step sequence: Identity Resolution → Binding → Change Request.

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

**Input:** Resolution outcome from step 1.

**Behavior:**

- If `matched`: create a Proposed Binding linking the Source Identity to the existing Tracked Identity.
- If `new`: allocate a new Tracked Identity (mint UUID; optionally reserve integer PK), then create a Proposed Binding.
- If `unresolved`: record the unresolved case for later review. No Binding is created.

**Policy enforcement** (applied between Resolution and Binding per [DV § Policy boundary](./DESIGN_VIEW.md#policy-boundary)):

- Evaluate whether a provider-supplied UUID is accepted as the SEAD universal identity or retained only as a provider key (FR-11).
- Evaluate whether an unmatched shared metadata entity triggers allocation or is held as unresolved.

Proposed Bindings may be confirmed automatically (for provider-owned entities with high-confidence matches) or require review (for shared metadata entities or low-confidence matches).

### 3. Associate with Change Request

Implements step 3 of the decision flow: **Change Request** association.

**Input:** One or more confirmed Bindings and an externally provided Change Request name (Sqitch change name).

**Behavior:**

- Record the association between confirmed Bindings and the named Change Request.
- The Change Request itself is created and managed by the SEAD Change Control System, not by SIMS.
- SIMS does not alter identity correspondence when recording this association (FR-25).

### 4. Detect Change (Update Foundation)

Supports FR-24 (aggregate-level change detection) and FR-25 (identity independent of mutation).

**Behavior:**

- Compare incoming content against an existing materialized Tracked Identity.
- Hash scope and normalization rules are per entity type and per aggregate boundary.
- Returns: `insert` (new entity), `update` (content differs), or `skip` (content unchanged).

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

- The key is serialized into a deterministic string representation.
- Serialization rules (field selection, ordering, normalization) are defined per entity type.
- The serialized key is stored as the Source Identity's `identity_value` with `identity_type = 'business_key'`.
- Used for resolution against existing Tracked Identities or existing SEAD data.

### Authority-key intake

When an external authority identifier is available (e.g. GeoNames, Wikidata):

- It is recorded in the Source Identity's `identity_signals` alongside other evidence.
- It may contribute to reconciliation for shared metadata entities (FR-10).
- It is preserved distinctly from provider keys and SEAD universal identity.

---

## Entity Metadata

The identity system needs to know which SEAD tables are tracked entities, their subtypes, aggregate boundaries, and FK relationships. This metadata drives resolution strategy selection, allocation ordering, and change-detection scope.

### What the system needs per tracked entity

| Attribute | Purpose |
|---|---|
| Entity type and PK column | Target for Tracked Identity allocation |
| Entity subtype | Governs intake rules and resolution strategy (provider-owned, shared metadata, relationship) |
| Aggregate membership | Defines change-detection scope and update semantics |
| FK dependencies | Determines allocation order within a Submission |
| Business-key fields | Enables business-key serialization and resolution |

### Source of truth

Shape Shifter's target model (`sead_standard_model.yml`) already catalogues SEAD entities with role (fact, classifier, lookup, bridge), foreign keys, identity columns, and unique sets. That metadata overlaps substantially with what SIMS needs.

The current design intent is that SIMS consumes Shape Shifter's target model as the source of truth for entity metadata, augmented by SIMS-specific attributes (reconciliation strategy, policy overrides) stored locally. See [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) for the entity register derived from the target model.

---

## Open Implementation Questions

These questions must be resolved before DDL is finalized and core operations are coded.

1. **Business-key serialization**: What normalization and serialization rules govern business-key construction per entity type? (Affects Source Identity uniqueness and idempotency.)

2. **Change-detection hash scope**: What entity data constitutes the aggregate payload for hashing? Which owned child rows are included, whether associations count, and which fields are excluded. Depends on aggregate boundary definitions.

3. **Identity policy representation**: How is the administrable identity policy (FR-11) stored and managed? Configuration file, database table, or API-managed resource?

4. **Allocation origin model**: Not all identity operations originate from provider submissions. SEAD administrator actions and Sqitch change requests are additional origins. The Source Scope / Submission model may need scopes that represent internal SEAD origins.

5. **Change Request integration**: What information beyond the Sqitch change name should SIMS record when associating Bindings with a Change Request? Should SIMS query the Change Control System for status, or only store the reference?

---

## Rollout Approach

Rollout is incremental. Each phase stabilizes before the next begins.

1. **Infrastructure**: Deploy identity schema, core tables, and REST API to staging. No SEAD entity tables are modified.

2. **Pilot**: Select a small set of tracked entity types (e.g. sites, sample groups). Implement resolution and binding for provider-owned entities. Validate idempotency and lifecycle correctness.

3. **Shared metadata**: Extend resolution to shared metadata entities (classifiers, lookup tables). Implement reconciliation and unresolved-state surfacing.

4. **Entity table integration**: Reuse existing `{entity}_uuid` columns on tracked SEAD entity tables. Add UUID columns only where missing. Pre-existing UUIDs are treated as authoritative without retroactive Binding records.

5. **Change Request integration**: Record associations between confirmed Bindings and externally managed Change Requests (Sqitch). Validate integration with the SEAD Change Control System.

Detailed rollout planning (timelines, specific table selection, migration scripts) belongs to project planning, not this document.
