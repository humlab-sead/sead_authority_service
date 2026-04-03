# Implementation View

## Purpose

This document is the implementation-level view of the SEAD Identity System.

It sits after [REQUIREMENTS.md](./REQUIREMENTS.md) (what the system must do) and [DESIGN_VIEW.md](./DESIGN_VIEW.md) (design rules and architectural decisions). It specifies how those requirements and design rules translate into concrete implementation structures.

Domain concepts and functional requirements are defined in REQUIREMENTS.md. Design rules and the Resolve → Allocate → Map decision flow are defined in DESIGN_VIEW.md. Neither is restated here.

---

## Technology Choices

- **PostgreSQL 12+** with `uuid-ossp` for UUID generation.
- **Sqitch** for database change control and migration sequencing.
- **Python REST API** (FastAPI) as the service layer above database operations.
- **OAuth 2.0** (client credentials for machine-to-machine) and **API keys** (for trusted systems such as Shape Shifter) for authentication.

---

## Storage Design

The identity system requires three categories of persistent structure: a central allocation registry, a submission tracker, and extensions to existing SEAD entity tables.

### Identity Allocations

> **Provisional DDL — see [ASSESSMENT.md](./ASSESSMENT.md) Gaps 9, 10, 11 and checklist H8.** The context/grouping model (submission FK, cascade delete) presupposes design decisions about allocation origins and atomicity that have not yet been made. Treat this as an illustrative sketch, not a structural commitment.

The central registry maps external identifiers to SEAD integer primary keys within an allocation context.

```sql
CREATE TABLE authority.identity_allocations (
    allocation_uuid     UUID NOT NULL DEFAULT uuid_generate_v4() PRIMARY KEY,

    -- Target
    table_name          TEXT NOT NULL,
    column_name         TEXT NOT NULL,

    -- External evidence
    external_id         TEXT NOT NULL,                    -- UUID string or composite natural key
    external_id_type    TEXT NOT NULL DEFAULT 'uuid',     -- 'uuid' | 'natural_key'

    -- Allocated SEAD identity
    alloc_integer_id    INTEGER NOT NULL,

    -- Allocation context (PROVISIONAL: origin model not yet defined; see ASSESSMENT.md Gap 10)
    -- These columns reflect assumed provider-submission origin only.
    submission_uuid     UUID NULL                         -- NULL for non-submission origins
        REFERENCES authority.submissions(submission_uuid) ON DELETE SET NULL,
    submission_name     TEXT NULL,

    -- Change control
    change_request_id   TEXT NULL,                        -- Sqitch change set ID (primary context for change-request origin)

    -- Optional audit context
    external_system_id  TEXT NULL,
    external_data       JSONB NULL,

    -- Change detection
    content_hash        TEXT NULL,                        -- SHA-256

    -- Lifecycle
    status              TEXT NOT NULL DEFAULT 'allocated', -- allocated | committed | rolled_back
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by          TEXT NOT NULL DEFAULT CURRENT_USER,
    committed_at        TIMESTAMP NULL,

    -- Idempotency: one external_id per table/column
    CONSTRAINT uq_identity_allocation UNIQUE (table_name, column_name, external_id),

    -- Integrity: one integer ID per table/column
    CONSTRAINT uq_allocated_id UNIQUE (table_name, column_name, alloc_integer_id)
);
```

Key indexes: `submission_uuid`, `(table_name, column_name)`, `status`, `external_id`, `content_hash WHERE NOT NULL`.

### Submissions

Groups related allocations into a named, auditable batch.

```sql
CREATE TABLE authority.submissions (
    submission_uuid      UUID NOT NULL DEFAULT uuid_generate_v4() PRIMARY KEY,
    submission_name      TEXT NOT NULL UNIQUE,
    source_system        TEXT NOT NULL,                   -- e.g. 'shape_shifter'
    data_type            TEXT NOT NULL,                   -- e.g. 'dendro', 'ceramics'
    status               TEXT NOT NULL DEFAULT 'pending', -- pending | validated | committed | failed | rolled_back
    created_at           TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by           TEXT NOT NULL DEFAULT CURRENT_USER,
    committed_at         TIMESTAMP NULL,
    change_request_id    TEXT NULL,
    notes                TEXT NULL,
    external_data        JSONB NULL,
    total_allocations    INTEGER DEFAULT 0,
    new_allocations      INTEGER DEFAULT 0,
    existing_allocations INTEGER DEFAULT 0
);
```

### Entity Table Extensions

Each tracked SEAD entity table gains three columns following a repeatable pattern:

| Column | Type | Purpose |
|--------|------|---------|
| `{entity}_external_id` | TEXT NULL | External identifier (UUID or natural key) |
| `{entity}_external_id_type` | TEXT NULL DEFAULT 'uuid' | Identifier type discriminator |
| `content_hash` | TEXT NULL | SHA-256 hash for change detection |

A partial unique index enforces uniqueness where the external_id is populated:

```sql
CREATE UNIQUE INDEX uq_{entity}_external_id
    ON public.tbl_{entities}({entity}_external_id)
    WHERE {entity}_external_id IS NOT NULL;
```

Columns start as nullable. After backfill of existing rows, NOT NULL constraints are applied.

---

## Core Operations

These operations implement the Resolve → Allocate → Map decision flow defined in DESIGN_VIEW.md. Each is implemented as a PostgreSQL function exposed through the REST API.

### Allocate Identity

Atomic, idempotent allocation of a SEAD integer ID for a given external identifier.

**Behavior:**

1. If `external_id` already exists for the given table/column, return the existing `alloc_integer_id`.
2. Otherwise, determine the next available integer ID (considering allocated IDs, existing table data, and sequence values), insert a new allocation record, and return the new ID.
3. Concurrency is handled via unique constraint: a race condition on INSERT triggers a conflict retry that reads the winner's allocation.

**Interface:**

```
allocate_identity(
    submission_uuid, submission_name,
    table_name, column_name,
    external_id, external_id_type,
    content_hash?, external_system_id?, external_data?
) → INTEGER
```

A batch variant accepts a JSONB array of allocations and returns a set of `(external_id, alloc_integer_id, is_new_allocation)` rows.

### Resolve External ID

Looks up the allocated integer ID for a given external identifier. Used during foreign key resolution.

Returns the allocated ID if status is `allocated` or `committed`. Raises an error if not found.

### Commit Submission

Marks all allocations for a submission as `committed` and records the Sqitch change request ID. Called after the generated DML has been executed successfully.

### Rollback Submission

Marks allocations as `rolled_back` (soft delete, preserves audit trail) or deletes them (hard delete, allows ID reuse). Updates the submission status accordingly.

### Detect Change

Compares a new content hash against the stored hash for a committed allocation. Returns one of three outcomes: `insert` (no existing record), `update` (hash differs or no stored hash), or `skip` (hash unchanged).

---

## Identity Intake Rules

These rules make concrete the identity intake patterns described in the requirements.

### UUID intake

When a provider supplies a UUID:

- Identity policy determines whether it is accepted as the SEAD universal identity or recorded only as a provider key (FR-11).
- If accepted, the UUID is used as the `external_id` with `external_id_type = 'uuid'`.
- If not accepted, the provider UUID is preserved in `external_data` for traceability.

### Business-key intake

When a provider supplies a natural key or key set:

- The key is serialized into a deterministic string representation (e.g. `"LAB_123|SITE_A|2024"`).
- Serialization rules (delimiter, field ordering, normalization) are defined per entity type.
- The serialized key is stored as `external_id` with `external_id_type = 'natural_key'`.

### Authority-key intake

When an external authority identifier is available (e.g. GeoNames, Wikidata):

- It is recorded in `external_data` alongside any other identity evidence.
- It may contribute to reconciliation for shared metadata entities.
- It is preserved distinctly from provider keys and SEAD universal identity.

---

## Submission Lifecycle

A submission moves through these states:

```
pending → validated → committed
pending → failed → rolled_back
pending → rolled_back
```

| State | Meaning |
|-------|---------|
| `pending` | Submission created, allocations may be added |
| `validated` | All allocations verified, ready for DML execution |
| `committed` | DML executed successfully, allocations permanent |
| `failed` | DML execution failed |
| `rolled_back` | Submission cancelled, allocations soft- or hard-deleted |

---

## API Surface

The REST API exposes the core operations under `/api/v1/identity/`.

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/submissions` | Create a named submission |
| POST | `/submissions/{id}/allocations` | Allocate a single identity |
| POST | `/submissions/{id}/allocations/batch` | Allocate identities in batch |
| GET | `/submissions/{id}/resolve` | Resolve external_id → integer |
| POST | `/submissions/{id}/commit` | Commit submission |
| POST | `/submissions/{id}/rollback` | Roll back submission |
| GET | `/submissions/{id}` | Get submission status and statistics |

Authentication: OAuth 2.0 client credentials or API key (`X-API-Key` header) with scopes `identity:read`, `identity:write`, `identity:admin`.

---

## Rollout Strategy

Rollout proceeds in five phases. Each phase completes and stabilizes before the next begins.

### Phase 1 — Infrastructure

Deploy the `sead_utility` schema, core tables, PostgreSQL functions, and REST API to the staging environment. Establish monitoring.

### Phase 2 — Pilot tables

Add external_id columns to five priority aggregate root tables: `tbl_locations`, `tbl_sites`, `tbl_sample_groups`, `tbl_physical_samples`, `tbl_analysis_entities`. Backfill existing rows with generated UUIDs. Test with Shape Shifter on staging data.

### Phase 3 — Core tables rollout

Extend external_id columns to all remaining tracked entity tables. Backfill in batches during low-traffic windows. Update dependent views and stored procedures.

### Phase 4 — Enforcement

Make external_id columns NOT NULL on pilot tables. Deprecate allocation methods that bypass the identity API. Migrate all ingesters to use the new API.

### Phase 5 — Production

Blue-green deployment to production with canary traffic routing. Maintain the old workflow in parallel for a transition period. Post-deployment review.

---

## Entity Metadata

The identity system needs to know which SEAD tables are tracked entities, what their aggregate boundaries are, and how they relate to each other. This metadata drives topological sorting, submission validation, and allocation ordering.

### What the system needs per tracked entity

| Attribute | Purpose |
|-----------|---------|
| Table name and PK column | Target for identity allocation |
| Entity subtype | Governs identity intake rules (provider-owned vs. shared metadata vs. relationship) |
| Aggregate membership | Defines content-hash scope and update semantics |
| FK dependencies | Determines allocation order and submission validation |
| Business-key fields | Enables natural-key resolution and serialization |

### Design question: where does this metadata live?

Shape Shifter's target model (`sead_standard_model.yml`) already catalogues 47 SEAD entities with role (fact/lookup/classifier/bridge), foreign keys, identity columns, column specs, and unique sets. That metadata overlaps substantially with what SIMS needs.

Two options are open:

1. **Consume the target model.** SIMS reads Shape Shifter's model spec at deployment time and derives entity type, dependency, and natural-key metadata from it. Advantages: single source of truth, no metadata duplication, changes propagate automatically. Risk: couples SIMS to Shape Shifter's data model format.

2. **Maintain a separate entity registry.** SIMS stores its own entity metadata in database tables (a simpler version of the retired aggregate model). Advantages: SIMS is self-contained, can track SIMS-specific attributes (allocation strategy, reconciliation rules) that the target model does not carry. Risk: two sources of entity truth that can drift.

A hybrid — SIMS bootstraps from the target model but stores SIMS-specific attributes locally — is also possible. See [ASSESSMENT.md](./ASSESSMENT.md) Gap 8 for the recorded design question.

Reference SQL patterns for topological depth, submission validation, and allocation ordering were drafted during early design. Those SQL files have been removed from this repository (they referenced retired aggregate model tables). New SQL will need to be written against the chosen entity metadata storage structure once the design question in [ASSESSMENT.md](./ASSESSMENT.md) Gap 8 is resolved.

---

## Open Implementation Questions

1. What serialization and normalization rules should govern business-key construction per entity type?
2. How should existing UUID-bearing SEAD tables be reconciled with the new external_id pattern where naming or semantics differ?
3. What scope of entity data constitutes the canonical aggregate payload for change detection hashing? Specifically: which owned child rows are included, whether associations count, and which fields are excluded.

---

## Relationship To Other Documents

- [REQUIREMENTS.md](./REQUIREMENTS.md) — what the system must do.
- [DESIGN_VIEW.md](./DESIGN_VIEW.md) — design rules and architectural decisions.
- [ASSESSMENT.md](./ASSESSMENT.md) — design strengths, weaknesses, and unresolved issues.
