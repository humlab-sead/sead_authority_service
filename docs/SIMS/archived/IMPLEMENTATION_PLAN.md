# SIMS Implementation Plan

## Scope

Phase 1 implementation of the SEAD Identity Management System as described in the [IMPLEMENTATION_VIEW](../IMPLEMENTATION_VIEW.md). Covers Rollout phases 1–2 (Infrastructure + Pilot). Phases 3–5 (Shared metadata, Entity table integration, CR integration) are outlined for sequencing but not detailed here.

**Repository:** `sead_authority_service` — branch `dev`
**Module root:** `src/identity/`
**Test root:** `tests/identity/`

---

## Prerequisites

Before starting implementation:

| Item                                     | Status   | Notes                                          |
|------------------------------------------|----------|------------------------------------------------|
| Documentation suite complete             | Done     | CM, REQ, DV, IMPL, ASSESSMENT — all aligned    |
| All ASSESSMENT gaps resolved             | Done     | content_hash, junction DDL, unresolved removal |
| `psycopg` + `psycopg-pool` available     | Done     | Already in `pyproject.toml`                    |
| FastAPI app with startup lifecycle       | Done     | `main.py` with `setup_config_store()`          |
| ConfigStore / `get_connection()` pattern | Done     | `src/configuration/`                           |
| PostgreSQL 16+ staging database          | Required | Needs `uuid-ossp` or `pgcrypto` extension      |

---

## Phase 1 Status: COMPLETE (2026-04-04)

All Phase 1 tasks implemented. **1054 tests pass** (zero failures) across the full test suite.

| Phase                    | Tests | Status |
|--------------------------|-------|--------|
| 1.1 SQL Schema (9 files) | —     | ✅ Done |
| 1.2 Domain Models        | 25    | ✅ Done |
| 1.3 Repository           | 25    | ✅ Done |
| 1.4 Identity Policy      | 29    | ✅ Done |
| 1.5 Service Operations   | 25    | ✅ Done |
| 1.6 API Endpoints        | 28    | ✅ Done |
| 1.7 Wiring & Config      | —     | ✅ Done |

---

## Design Decisions

All decisions confirmed (2026-04-04).

| #  | Decision               | **Decision**                                                                                               | Rationale                                                                                 |
|----|------------------------|------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| D1 | Schema namespace       | **`sead_identity` schema**                                                                                 | Separate from `authority` (reconciliation). Clean boundary.                               |
| D2 | UUID generation        | **PostgreSQL-side `gen_random_uuid()`**                                                                    | Single source of truth. Avoids Python/DB mismatch.                                        |
| D4 | API auth               | **Deferred to Phase 3**                                                                                    | Pilot runs on staging; reconciliation endpoints already unauthenticated.                  |
| D5 | Entity metadata source | **Local config file (`config/identity_policy.yml`)** seeded from Shape Shifter's `sead_superset_model.yml` | Avoids runtime cross-repo dependency. Refresh manually per release.                       |
| D6 | Binding auto-confirm   | **Provider-owned entities: auto-confirm. Shared metadata: require review.**                                | Per IMPLEMENTATION_VIEW § Bind. Phase 1 covers only provider-owned → always auto-confirm. |

---

## Work Breakdown

### Phase 1: Infrastructure

**Goal:** Deploy identity schema, domain models, repository layer, and basic API to staging. No SEAD entity tables modified.

#### 1.1 SQL Schema

Create the 7 identity tables defined in IMPLEMENTATION_VIEW § Storage Design.

| Task                                              | Output                                                     | References                                                                            |
|---------------------------------------------------|------------------------------------------------------------|---------------------------------------------------------------------------------------|
| Create `sead_identity` schema with UUID extension | `schema/sql/identity/000_schema.sql`                       | D1, D2                                                                                |
| `source_scopes` table                             | `schema/sql/identity/001_source_scopes.sql`                | IMPL § Source Scopes                                                                  |
| `submissions` table                               | `schema/sql/identity/002_submissions.sql`                  | IMPL § Submissions                                                                    |
| `source_identities` table + uniqueness constraint | `schema/sql/identity/003_source_identities.sql`            | IMPL § Source Identities                                                              |
| `submission_source_identities` junction           | `schema/sql/identity/004_submission_source_identities.sql` | IMPL § Junction                                                                       |
| `tracked_identities` table                        | `schema/sql/identity/005_tracked_identities.sql`           | IMPL § Tracked Identities                                                             |
| `binding_sets` table                              | `schema/sql/identity/006_binding_sets.sql`                 | IMPL § Binding Sets                                                                   |
| `bindings` table + FK constraints                 | `schema/sql/identity/007_bindings.sql`                     | IMPL § Bindings                                                                       |
| Seed well-known internal scopes                   | `schema/sql/identity/008_seed_scopes.sql`                  | IMPL § Internal Origins (`sead://admin`, `sead://migration`, `sead://reconciliation`) |

**Acceptance:** All tables created on staging. FK constraints validated. Seed data present. ✅

#### 1.2 Domain Models

Pydantic/dataclass models representing SIMS concepts in Python.

| Task                                                                                                 | Output                          |
|------------------------------------------------------------------------------------------------------|---------------------------------|
| Core value types: `EntityType`, `IdentityType`, `LifecycleState` enums                               | `src/identity/types.py`         |
| `SourceScope`, `Submission`, `SourceIdentity` models                                                 | `src/identity/models.py`        |
| `TrackedIdentity`, `BindingSet`, `Binding` models                                                    | `src/identity/models.py`        |
| Request/response DTOs: `ResolutionRequest`, `ResolutionOutcome`, `BindRequest`, `BindingSetResponse` | `src/identity/models.py`        |
| Unit tests for model construction and validation                                                     | `tests/identity/test_models.py` |

**Acceptance:** All models instantiate with valid data. Validation rejects invalid states (e.g. unknown lifecycle transitions). Tests pass. ✅

#### 1.3 Repository Layer

Async database access following the existing `get_connection()` pattern.

| Task                                                                                    | Output                              |
|-----------------------------------------------------------------------------------------|-------------------------------------|
| Base repository with connection helper                                                  | `src/identity/repository.py`        |
| `SourceScopeRepository` — CRUD + lookup by name                                         | `src/identity/repository.py`        |
| `SubmissionRepository` — create, update status, lookup                                  | `src/identity/repository.py`        |
| `SourceIdentityRepository` — upsert (idempotent by uniqueness), lookup by scope+signals | `src/identity/repository.py`        |
| `TrackedIdentityRepository` — create (mint UUID), update lifecycle/hash, lookup         | `src/identity/repository.py`        |
| `BindingSetRepository` — create, transition lifecycle, lookup by submission             | `src/identity/repository.py`        |
| `BindingRepository` — create within set, lookup by source or tracked identity           | `src/identity/repository.py`        |
| Integration tests against test database                                                 | `tests/identity/test_repository.py` |

**Acceptance:** All CRUD operations work. Uniqueness constraint on `source_identities` enforces idempotency. Lifecycle transitions validated. Integration tests pass against a test PostgreSQL instance. ✅

#### 1.4 Identity Policy

Configuration-driven policy engine per IMPLEMENTATION_VIEW § Bind.

| Task                                                                                        | Output                                                  |
|---------------------------------------------------------------------------------------------|---------------------------------------------------------|
| Policy config schema and loader                                                             | `config/identity_policy.yml` + `src/identity/policy.py` |
| `IdentityPolicy` class: per-entity-type rules (accept_uuid, allow_allocation, auto_confirm) | `src/identity/policy.py`                                |
| Default policy: provider-owned entities accept UUID + allow allocation + auto-confirm       | `config/identity_policy.yml`                            |
| Unit tests for policy evaluation                                                            | `tests/identity/test_policy.py`                         |

**Acceptance:** Policy loads from config. Provider-owned entities get expected defaults. Unknown entity types fall back to safe defaults (reject UUID, block allocation). ✅

#### 1.5 Core Service Operations

Implement the 4 operations from IMPLEMENTATION_VIEW § Core Operations.

| Task                                                                | Output                    | Dependencies |
|---------------------------------------------------------------------|---------------------------|--------------|
| `resolve_identity()` — lookup existing binding or evaluate signals  | `src/identity/service.py` | 1.3, 1.4     |
| `create_binding_set()` — batch resolve + bind, apply policy         | `src/identity/service.py` | 1.3, 1.4     |
| `confirm_binding_set()` — lifecycle transition proposed → confirmed | `src/identity/service.py` | 1.3          |
| `associate_change_request()` — link confirmed set to CR name        | `src/identity/service.py` | 1.3          |
| `detect_change()` — compare content hash                            | `src/identity/service.py` | 1.3          |
| Unit tests with mocked repositories | `tests/identity/test_service.py` |
| Integration tests with real DB | `tests/identity/test_service_integration.py` |

**Acceptance:** Resolve is idempotent (FR-12, FR-13). Binding sets transition correctly. Change detection returns insert/update/skip. Tests pass. ✅

#### 1.6 API Endpoints

REST API for SIMS operations, following existing router pattern.

| Task                                                                | Output                       |
|---------------------------------------------------------------------|------------------------------|
| Identity router with prefix `/identity`                             | `src/api/identity_router.py` |
| `POST /identity/resolve` — resolve a batch of source identities     | `src/api/identity_router.py` |
| `GET /identity/binding-sets/{id}` — binding set status              | `src/api/identity_router.py` |
| `POST /identity/binding-sets/{id}/confirm` — confirm a proposed set | `src/api/identity_router.py` |
| `POST /identity/binding-sets/{id}/change-request` — associate CR    | `src/api/identity_router.py` |
| `POST /identity/detect-change` — content hash comparison            | `src/api/identity_router.py` |
| `GET /identity/scopes` — list source scopes                         | `src/api/identity_router.py` |
| Register router in `main.py`                                        | `main.py` (edit)             |
| API tests with TestClient                                           | `tests/identity/test_api.py` |

**Acceptance:** All endpoints return correct status codes. Resolve endpoint is idempotent. OpenAPI schema generated. ✅

#### 1.7 Configuration + Wiring

| Task                                              | Output                            |
|---------------------------------------------------|-----------------------------------|
| Add `identity:` section to `config/config.yml`    | `config/config.yml` (edit)        |
| Update `src/identity/__init__.py` with public API | `src/identity/__init__.py` (edit) |
| Add identity router import to `main.py` startup   | `main.py` (edit)                  |
| Update test config at `tests/config/config.yml`   | `tests/config/config.yml` (edit)  |
| Add `@pytest.mark.identity` test marker           | `pyproject.toml` (edit)           |

**Acceptance:** Service starts with identity module loaded. Config values resolve. Test markers work.

---

### Phase 2: Pilot

## Phase 2 Status: COMPLETE (2026-04-06)

All 15 integration tests pass (live DB: `sead_staging` on `humlabseadserv.srv.its.umu.se:5433`). 1054 unit tests continue to pass — no reconciliation regressions.

**Goal:** Resolve and bind provider-owned entities (sites, sample_groups) end-to-end. Validate idempotency and lifecycle correctness.

**Prerequisite:** Phase 1 fully deployed to staging.

| Task                                              | Notes                                                                  | Status |
|---------------------------------------------------|------------------------------------------------------------------------|--------|
| Select pilot entity types                         | `site`, `sample_group`, `sample`, `analysis_entity` in policy          | ✅ Done |
| Seed identity policy for pilot types              | `config/identity_policy.yml`                                           | ✅ Done |
| Create test submission with known identities      | Covered by integration test fixtures (unique scope per run)            | ✅ Done |
| Validate Resolve → Bind → Confirm flow end-to-end | `TestResolveAndBindSite`, `TestResolveAndBindSampleGroup`               | ✅ Done |
| Validate idempotency                              | `test_resolve_is_idempotent`, `test_second_resolve_returns_matched_after_bind` | ✅ Done |
| Validate content hash change detection            | `TestDetectChange`: insert / skip / update / unknown-UUID              | ✅ Done |
| Validate shared_metadata stays proposed           | `TestConfirmAndChangeRequest::test_confirm_proposed_set_transitions_lifecycle` | ✅ Done |
| Validate Change Request association               | `TestConfirmAndChangeRequest::test_associate_change_request_on_confirmed_set` | ✅ Done |
| Document any issues found                         | One gap fixed: `BindingRepository.create()` wrongly included `created_by` (not in DDL) — removed. | ✅ Done |

**Acceptance criteria met:**
- ✅ Full happy-path flow works for provider-owned entities
- ✅ Idempotency holds (FR-12, FR-13)
- ✅ Change detection works (FR-24): insert / skip / update
- ✅ No regressions in reconciliation endpoints (1054 unit tests pass)

---

### Phase 3: Shared Metadata (Outline)

- Extend identity policy for shared metadata entity types (methods, sample_types, bibliographic_references)
- Implement rejection with diagnostics when reconciliation fails (FR-20)
- Integration with Shape Shifter reconciliation workflow — SIMS consumes reconciliation outcomes
- Policy configuration for which entity types require reconciliation vs. allow allocation

### Phase 4: Entity Table Integration (Outline)

- Audit existing `{entity}_uuid` columns on SEAD entity tables
- Add UUID columns where missing
- Treat pre-existing UUIDs as authoritative tracked identities (no retroactive binding records)
- Validate that SIMS tracked_identity UUIDs align with entity table UUIDs

### Phase 5: Change Request Integration (Outline)

- Integrate Binding Set → Change Request association with Sqitch workflow
- Validate that confirmed Binding Sets are required before CR can be applied (FR-27)
- End-to-end flow: Shape Shifter submission → SIMS resolution → Sqitch CR → SEAD mutation

---

## Implementation Order (Phase 1)

Dependencies determine the order. The critical path is: Schema → Models → Repository → Service → API.

```
1.1 Schema ──────────────────────┐
                                 ▼
1.2 Models ──► 1.4 Policy ──► 1.5 Service ──► 1.6 API
                                 ▲               │
1.3 Repository ──────────────────┘               ▼
                                           1.7 Wiring
```

**Suggested execution sequence:**

| Step | Tasks                       | Can parallelize?                 |
|------|-----------------------------|----------------------------------|
| 1    | 1.1 Schema + 1.2 Models     | Yes — independent                |
| 2    | 1.3 Repository + 1.4 Policy | Yes — both depend only on models |
| 3    | 1.5 Service                 | Depends on repository + policy   |
| 4    | 1.6 API                     | Depends on service               |
| 5    | 1.7 Wiring                  | Final integration                |

---

## File Map

New files to create:

```
config/
  identity_policy.yml              ← Entity-type policy configuration
schema/sql/identity/
  000_schema.sql                   ← Schema + extension
  001_source_scopes.sql            ← Source scopes table
  002_submissions.sql              ← Submissions table
  003_source_identities.sql        ← Source identities + uniqueness
  004_submission_source_identities.sql  ← Junction table
  005_tracked_identities.sql       ← Tracked identities + content_hash
  006_binding_sets.sql             ← Binding sets + lifecycle
  007_bindings.sql                 ← Bindings + FK constraints
  008_seed_scopes.sql              ← Well-known internal scopes
src/identity/
  __init__.py                      ← Public API (edit existing)
  types.py                         ← Enums: EntityType, IdentityType, LifecycleState
  models.py                        ← Domain models
  repository.py                    ← Async DB repositories
  policy.py                        ← Identity policy engine
  service.py                       ← Core operations (resolve, bind, confirm, detect)
src/api/
  identity_router.py               ← REST API endpoints
tests/identity/
  __init__.py                      ← Exists (empty)
  test_models.py                   ← Model unit tests
  test_policy.py                   ← Policy unit tests
  test_repository.py               ← Repository integration tests
  test_service.py                  ← Service unit tests (mocked repo)
  test_service_integration.py      ← Service integration tests
  test_api.py                      ← API endpoint tests
```

Files to edit:

```
main.py                            ← Register identity router
config/config.yml                  ← Add identity: section
pyproject.toml                     ← Add identity test marker
tests/config/config.yml            ← Add test identity config
```

---

## Risks

| Risk                                                                            | Likelihood | Impact | Mitigation                                                           |
|---------------------------------------------------------------------------------|------------|--------|----------------------------------------------------------------------|
| Schema namespace conflicts with existing `authority` schema                     | Low        | Medium | Use separate `sead_identity` schema (D1)                             |
| Entity metadata drift between Shape Shifter target model and SIMS policy config | Medium     | Medium | Seed from `sead_superset_model.yml`; version-tag the extract (D5)    |
| Idempotency edge cases in concurrent submissions                                | Medium     | High   | Rely on DB uniqueness constraint; add advisory locks if needed       |
| Reconciliation integration complexity (Phase 3)                                 | High       | High   | Phase 1 avoids shared metadata entirely — risk is deferred           |
| Test database setup complexity                                                  | Medium     | Low    | Use Docker Compose for isolated test DB; reuse existing pool pattern |

---

## Success Criteria

**Phase 1 is complete when:**

1. All 7 identity tables exist in `sead_identity` schema on staging
2. Domain models cover all IMPLEMENTATION_VIEW concepts
3. All 4 core operations (Resolve, Bind, Associate CR, Detect Change) are implemented
4. REST API endpoints are functional and documented via OpenAPI
5. Identity policy loads from configuration and governs resolution/binding decisions
6. Unit and integration tests pass with adequate coverage
7. Reconciliation endpoints continue working (no regressions)

**Phase 2 is complete when:**

8. End-to-end flow works for `site` and `sample_group` entity types
9. Idempotency validated — duplicate submissions produce identical results
10. Content hash change detection returns correct insert/update/skip outcomes
