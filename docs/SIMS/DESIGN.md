# Design

> **Status:** Describes the current Phases 1–2 implementation, its disposable site-allocation prototype, and the approved-ID bind-time lifecycle check. The target architecture is a generic, entity-configured allocator owned by SIMS; it is not yet implemented. Production adoption, existing-data migration, and cutover are outside the current development task. See [OPERATIONS.md](./OPERATIONS.md) for deployment and [src/identity/README.md](../../src/identity/README.md) for the module entry point.

## Purpose

This document describes the SIMS design and its current Authority Service implementation.

It sits after [REQUIREMENTS.md](./REQUIREMENTS.md) (what the system must do) and [CONCEPTUAL_MODEL.md](./CONCEPTUAL_MODEL.md) (core concepts, design rules, decision flow). It maps those concepts and rules to concrete implementation structures.

Domain concepts, functional requirements, lifecycles, and design rules are not restated here.

---

## Technology Context

- **PostgreSQL 16+** with `uuid-ossp` or `pgcrypto` for UUID generation.
- **Python REST API** (FastAPI) as the service layer, hosted in the `sead_authority_service` repository (`src/identity/`).
- Schema migrations are plain SQL files in `schema/sql/identity/` applied directly (no migration framework).

---

## Concept-to-Structure Mapping

The table below maps each CM concept to its implementation anchor. This is the primary alignment contract between the conceptual model and the storage design.

| CM Concept              | Implementation Structure   | Notes                                                                                                                     |
|-------------------------|----------------------------|---------------------------------------------------------------------------------------------------------------------------|
| **Source Scope**        | `source_scopes` table      | Hierarchical namespace; stable across submissions                                                                         |
| **Submission**          | `submissions` table        | Temporal provenance; belongs to one Source Scope                                                                          |
| **Source Identity**     | `source_identities` table  | Persistent per scope; carries identity signals                                                                            |
| **Tracked Identity**    | `tracked_identities` table | SIMS-owned aggregate identity and UUID; lifecycle per [CM § Tracked Identity Lifecycle](./CONCEPTUAL_MODEL.md#tracked-identity-lifecycle) |
| **Binding**             | `bindings` table           | Links Source Identity → Tracked Identity; belongs to one Binding Set                                                     |
| **Binding Set**         | `binding_sets` table       | Atomic batch of Bindings; owns lifecycle, audit, and optional opaque consumer reference (FR-26)                            |
| **Identity Resolution** | Service operation          | Stateless process; outcomes expressed as a Binding Set containing Bindings (rejected submissions receive diagnostics)     |
| **Change Request**      | Optional external reference | Consumer-owned domain-change process; current SEAD integration stores a Sqitch change name                               |

### Key structural principles

- Each CM concept owned by SIMS maps to its own table. No composite "allocation" table conflating Source Identity, Tracked Identity, and Binding.
- Binding Sets are the atomic identity-governance unit. Lifecycle state, audit trail, and optional consumer references live on the Binding Set, not on individual Bindings.
- Any consumer change reference is opaque metadata to SIMS; the current SEAD-specific Sqitch field is a legacy integration detail.
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
| `entity_type`                        | Configured tracked aggregate type                                      |
| `identity_type`                      | `uuid`, `business_key`, `provider_key`, `authority_key`                |
| `identity_value`                     | The serialized identifier value                                        |
| `identity_signals` (JSONB, nullable) | Additional identity evidence (authority keys, alternative identifiers) |
| Audit columns                        | `created_at`, `created_by`                                             |
| **Uniqueness**                       | `(scope_uuid, entity_type, identity_type, identity_value)`             |

A Source Identity may be observed in multiple Submissions. A junction table (`submission_source_identities`) records which Submission carried which Source Identities, reflecting the M:N relation from [CM § Relations](./CONCEPTUAL_MODEL.md#relations-and-cardinalities) (relation 3).

### Submission–Source Identity Junction

Records which Source Identities were carried by which Submissions.

| Column                        | Purpose                                                  |
|-------------------------------|----------------------------------------------------------|
| `submission_uuid` (PK, FK)    | References `submissions`                                 |
| `source_identity_uuid` (PK, FK) | References `source_identities`                        |
| `observed_at`                 | Timestamp when this Source Identity was observed in this Submission |

The composite primary key `(submission_uuid, source_identity_uuid)` enforces uniqueness.

### Tracked Identities

Represents SIMS' current identity record for a tracked aggregate. This schema includes prototype fields that reflect the initial SEAD integration and are not requirements for the target generic allocator.

| Column                        | Purpose                                                               |
|-------------------------------|-----------------------------------------------------------------------|
| `tracked_identity_uuid` (PK)  | SIMS' stable UUID for this tracked aggregate                           |
| `entity_type`                 | Configured tracked aggregate type                                     |
| `aggregate_id` (nullable)       | SIMS-minted, entity-scoped aggregate identity value; consumers interpret it using their own data models |
| `content_hash` (nullable)     | Opaque aggregate content hash for change detection (FR-24)            |
| `lifecycle_state`             | `allocated`, `pending_materialization`, `materialized`, `invalidated` |
| Audit columns                 | `created_at`, `created_by`, `materialized_at`                         |

SIMS mints and stores both `tracked_identity_uuid` and `aggregate_id`. The aggregate ID is unique within its entity type in the SIMS identity store. SIMS does not map it to a consumer table or column.

**Historical disposable allocator prototype:** Initial verification used per-type allocator setup and a nullable SEAD integer-ID field for selected examples. That prototype does not define the target architecture. The target allocator must use generic SIMS code and validated entity-scoped configuration, mint the configured aggregate identity value and tracked UUID, and enforce uniqueness only in the SIMS identity store. SIMS must not read or allocate from SEAD tables or sequences. The target contract requires consumers to trust and store SIMS-issued values; it does not make SIMS responsible for consumer database integrity.

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

Change Requests are owned by consuming workflows. SIMS does not store or manage their state.

The current `binding_sets` table carries an optional `change_request_name` field from the SEAD integration. In the target design, any consumer change reference is opaque metadata; SIMS does not integrate with or manage a change-control system.

---

## Core Operations

These operations implement the identity steps defined in [CONCEPTUAL_MODEL.md § Decision Flow](./CONCEPTUAL_MODEL.md#decision-flow). A consuming workflow may separately reference a domain-change process.

### 1. Resolve Identity

Implements step 1 of the decision flow: **Identity Resolution**.

**Input:** Source Identity (within a Source Scope), entity type, identity signals.

**Behavior:**

1. Look up the Source Identity within its scope. If it already has a confirmed Binding, return that Tracked Identity.
2. If the caller supplies an approved existing SIMS identity, bind the Source Identity to it (FR-17).
3. If the caller requests a new identity, use the configured generic allocation operation. Reject the request when configuration does not permit it (FR-20).
4. Return the existing or newly allocated Tracked Identity and its SIMS-issued identity values.

**Design decision:** Reconciliation against SEAD or another consumer's domain records is outside SIMS. The consuming workflow supplies its approved match or allocation decision. SIMS stores and resolves source identities against its own Tracked Identities and applies validated SIMS configuration; it does not inspect consumer tables or implement per-entity reconciliation branches.

**Idempotency:** The same identity signals within the same scope always produce the same resolution outcome (FR-12, FR-13).

### 2. Bind

Implements step 2 of the decision flow: **Binding**.

**Input:** Resolution outcomes from step 1 (one or more resolved Source Identities).

**Output:** A Proposed Binding Set containing individual Bindings.

**Behavior:**

- Create a new Binding Set in `proposed` state.
- For each resolved Source Identity:
  - If `matched`: create a Binding within the set linking the Source Identity to the existing Tracked Identity.
  - If `new`: use the generic allocator and validated configuration to create a SIMS Tracked Identity, then create a Binding within the set. The current site prototype is not the target allocator design.

**Policy enforcement** (applied between Resolution and Binding per [CONCEPTUAL_MODEL.md § Policy boundary](./CONCEPTUAL_MODEL.md#policy-boundary)):

- Evaluate source-key semantics and permitted identity operations from validated SIMS entity configuration (FR-11).
- Evaluate whether the requested identity operation is permitted by validated SIMS configuration.

For a caller-supplied approved aggregate ID, the service locks the matching Tracked Identity by UUID, entity type, and aggregate ID in the binding transaction. It creates a Binding only when the current lifecycle state is `materialized`. The same check applies when reusing a confirmed Binding or replaying a stored batch; a missing or non-materialized identity returns HTTP 409. The service does not change the identity's lifecycle state, query SEAD, or alter allocation for requests without an approved ID. The row lock makes concurrent lifecycle updates wait until the binding transaction finishes.

**Design decision:** Identity operation configuration (FR-11) is stored in SIMS. Shared service code validates and applies it for configured entity types; adding an entity type must not require a type-specific allocator branch.

Proposed Binding Sets may be confirmed automatically or require review according to validated operation configuration. Caller reconciliation and approval remain outside SIMS.

### 3. Record external reference (current integration)

The current implementation can associate a confirmed Binding Set with an external reference. This is not a SIMS domain-change operation.

**Input:** A confirmed Binding Set and an opaque consumer reference. The current SEAD adapter supplies a Sqitch change name.

**Behavior:**

- Record the association as opaque metadata on the Binding Set. The current schema uses `change_request_name`.
- The consumer owns and manages the referenced change process.
- SIMS does not alter identity correspondence when recording this association (FR-25).

**Design decision:** SIMS does not query the reference, inspect its status, apply associated data changes, or interpret its format.

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

- Store the provider UUID as a scoped Source Identity value according to validated SIMS configuration (FR-11).
- Do not adopt the provider UUID as the Tracked Identity UUID. SIMS mints its own tracked UUID when it creates a Tracked Identity.
- The current `accept_uuid` policy is legacy behavior and is not part of the target identity contract.

### Business-key intake

When a provider supplies a natural key or key set:

- The submitting system constructs a deterministic serialized string from provider data using its own model and identity rules.
- SIMS receives the serialized string as an opaque token and stores it as the Source Identity's `identity_value` with `identity_type = 'business_key'`.
- SIMS does not interpret the internal structure of the business key. It uses the string solely for equality comparison and uniqueness enforcement.
- Used for resolution against existing SIMS Tracked Identities.

**Design decision:** Business-key serialization (field selection, ordering, normalization) is the responsibility of the submitting system, not SIMS. Different data providers have different schemas; only the submitting system understands how to map provider data to its domain model. SIMS requires only that the serialized string is deterministic within a Source Scope — the same entity with the same input always produces the same string — to guarantee idempotency (FR-12, FR-13).

### Authority-key intake

When an external authority identifier is available (e.g. GeoNames, Wikidata):

- It is recorded in the Source Identity's `identity_signals` alongside other evidence.
- It may contribute to reconciliation for shared metadata entities (FR-10).
- It is preserved distinctly from provider keys and SIMS tracked identity values.

---

## Entity Configuration

The target design configures tracked aggregate types and identity behavior without making SIMS aware of consumer tables, columns, primary keys, or sequences. Adding a configured type must not require a type-specific allocator branch.

### What SIMS needs per configured type

| Attribute | Purpose |
|---|---|
| Entity type | Scopes tracked identities and their configured identity values |
| Identity strategy | Selects generic allocation or lookup behavior |
| Source-key rules | Defines accepted source identity forms and resolution inputs |
| Resolution policy | Defines handling for new, matched, ambiguous, or rejected identities |

### Configuration ownership

SIMS configuration is the source of truth for SIMS identity behavior. A client may use its own model to decide which aggregates to submit and how to store returned values, but SIMS does not consume that model to discover target tables, columns, foreign keys, or storage identifiers.

---

## Internal Origins

SIMS accepts identity requests from scoped callers; it does not define caller workflows or require SEAD-specific origins. The following source-scope names describe the current SEAD integration and are not required by the target generic design.

### Approach

The current integration uses the same Source Scope and Submission model for external and internal requests:

- `sead://admin` — SEAD administrator actions (adding or modifying classifiers, methods, etc.)
- `sead://migration` — Sqitch-driven schema or data migrations
- `sead://reconciliation` — Reconciliation outputs

Internal actions create Submissions within these scopes and use the normal identity operations. A consumer may associate a Binding Set with its own change workflow; SIMS does not interpret or apply that workflow.

**Design decision:** Preparation, reconciliation, approval, and submission of domain data are caller responsibilities. SIMS provides configured identity operations and reports Binding Set state; it does not enforce rules for a consumer's change process.

---

## Historical SEAD Integration Plan

The following sequence reflects an earlier SEAD-specific integration plan. It is not the target SIMS architecture and does not authorize production adoption or cutover:

1. **Infrastructure**: Deploy identity schema, core tables, and REST API to staging.

2. **Pilot**: Validate generic identity resolution, allocation, and binding with configured entity types.

3. **Shared metadata**: Keep target-system reconciliation and approval in the consuming workflow; SIMS receives approved identity requests.

4. **Consumer integration**: Consumers store SIMS-issued identity values under the trust contract. SIMS does not map those values to consumer tables or columns.

5. **Operational adoption**: Existing-data migration, deployment checks, and cutover require a separate operational plan and are outside the current development task.

SIMS guarantees uniqueness only within its own identity store. Consumer database integrity remains with each consumer.
