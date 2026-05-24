# SEAD Authority Service - Design

## Purpose

This document describes the architecture and design of the SEAD Authority Service: how the system is structured, how its major components interact, which design decisions shape the code, and what constraints and tradeoffs apply. It is the primary entry point for developers working on the codebase.

## Audience and Scope

Written for developers and maintainers who need to understand how the system is organized, how to extend it, and what boundaries must not be crossed. Local setup and contributor workflow belong in [DEVELOPMENT.md](DEVELOPMENT.md). Deployment procedures belong in [OPERATIONS.md](OPERATIONS.md).

---

## System Context and Boundaries

The SEAD Authority Service is a **reconciliation and identity service** with two primary functions: matching fuzzy text queries to canonical SEAD entity identifiers (OpenRefine Reconciliation API), and managing stable UUIDs for incoming SEAD data submissions (SIMS).

**In scope:** reconciliation strategy execution, entity candidate retrieval, LLM-assisted validation, identity resolution and UUID allocation, binding lifecycle management, entity schema generation.

**Out of scope:** the SEAD Clearinghouse and its ingestion pipeline, the Shape Shifter transformation tool, and the source databases. These are external systems that integrate with this service but are not owned by it.

**External integrations:**

| System | Direction | Protocol | Purpose |
|---|---|---|---|
| OpenRefine / data tools | Inbound | HTTP | Reconciliation query submission |
| Shape Shifter / submission tools | Inbound | HTTP | Identity resolution requests |
| PostgreSQL (SEAD database) | Outbound | SQL (psycopg3) | Entity candidate retrieval and identity storage |
| LLM providers (OpenAI, Anthropic, Ollama) | Outbound | HTTP | Candidate validation and ranking |
| MCP server (embedded) | Internal | stdio | Hybrid retrieval for RAG strategies |

---

## High-Level Architecture

```
┌──────────────────────────────────────────────┐
│           External Clients                   │
│  OpenRefine • Shape Shifter • Data tools     │
└─────────────────┬──────────────────┬─────────┘
                  │ /reconcile        │ /identity
                  ▼                  ▼
┌─────────────────────────────────────────────┐
│            FastAPI Application              │
│  Reconciliation Router • Identity Router   │
├─────────────────────────────────────────────┤
│  Reconciliation Orchestrator               │
│  Strategy Registry → Entity Strategies     │
├──────────────────────┬──────────────────────┤
│  Repository Layer    │  Identity Service    │
│  (per-entity SQL)    │  (SIMS)              │
└──────────┬───────────┴──────────────────────┘
           │
┌──────────▼───────────────────────────────────┐
│  PostgreSQL (SEAD + authority schema)        │
│  pg_trgm • pgvector • PostGIS               │
└──────────────────────────────────────────────┘
           │ (optional)
┌──────────▼──────────┐
│  LLM Providers      │
│  OpenAI / Ollama    │
└─────────────────────┘
```

The service runs as a single FastAPI process on port 8000. There is no frontend layer; all interaction is via the REST API.

---

## Components and Responsibilities

### API Layer (`src/api/`)

Thin HTTP boundary with two routers:

- **`router.py`**: OpenRefine-compatible endpoints — `POST /reconcile`, `GET /suggest/*`, `GET /flyout/entity`, `GET /reconcile/preview`. Parses OpenRefine's form-encoded or JSON query format and delegates to the reconciliation orchestrator.
- **`identity_router.py`**: SIMS endpoints under `/identity` — identity resolution, binding set management, change detection, and scope listing. See [SIMS documentation](SIMS/) for endpoint details.

Neither router contains business logic. All validation uses Pydantic models at the boundary.

### Reconciliation Orchestrator (`src/reconcile.py`, `src/suggest.py`, `src/preview.py`)

Coordinates batched reconciliation requests. For each query: extracts the entity type, looks up the registered strategy, retrieves candidates, scores them, and formats results in the OpenRefine response structure. Batch queries are processed sequentially (parallelism is a known limitation).

### Strategy Registry (`src/strategies/`)

The central extensibility mechanism. Strategies auto-register at import time via `@Strategies.register(key=..., repository_cls=...)`. The registry is populated when `main.py` imports `src.strategies`, which triggers recursive module loading.

Each strategy encapsulates entity-specific matching logic, property parsing (e.g., coordinates for sites), alternate identity matching (e.g., DOI for references), and scoring. The base class provides default behaviour; subclasses override only what differs.

**Strategy hierarchy:**

- `ReconciliationStrategy` — abstract base; default find/score/format behaviour
- `RAGHybridReconciliationStrategy` — fuzzy retrieval → optional MCP retrieval → LLM validation
- Entity strategies (`SiteReconciliationStrategy`, `TaxonReconciliationStrategy`, `MethodReconciliationStrategy`, etc.) — entity-specific overrides

### Repository Layer (`src/strategies/query.py`)

Abstracts PostgreSQL queries from strategy logic. `BaseRepository` implements trigram-based fuzzy search, alternate-identity exact matching, and single-entity detail retrieval against generated `authority.*` views. Specialized subclasses (e.g., `SiteRepository`) add entity-specific queries such as geographic proximity search.

All repositories use `get_connection()` — the singleton connection pool — and parameterized SQL. No raw string interpolation.

### Configuration System (`src/configuration/`)

- **`ConfigValue`**: lazy resolver supporting colon-separated paths (`options:database:host`) and comma-separated fallback paths (`llm.ollama.model,llm.model`). All config lookups use `ConfigValue`.
- **Connection singleton**: created once at startup in `setup.py` and stored in runtime config. Retrieved via `get_connection()`. Never instantiate connections directly.
- **Config files**: `config.yml` (base), `entities.yml` (entity schemas, included via `@include`), `prompts.yml` (LLM prompt templates), `identity_policy.yml` (SIMS per-entity policy).
- **Environment variables**: `${VAR_NAME}` placeholders in YAML are substituted from `.env` at startup.

### LLM Integration (`src/llm/`)

Provider abstraction over OpenAI, Anthropic, and Ollama. Active provider is selected by `llm.provider` in config. Prompt templates live in `config/prompts.yml` and are rendered with Jinja2 before submission. LLM calls are async and only invoked when a strategy opts into the RAG hybrid path.

### Identity Module (`src/identity/`)

Fully implemented SEAD Identity Management System (SIMS). Manages stable UUID allocation and binding lifecycle for incoming SEAD data submissions.

- **`models.py`**: Pydantic domain types — `SourceScope`, `Submission`, `SourceIdentity`, `TrackedIdentity`, `BindingSet`, `Binding`, `ResolutionOutcome`, `ChangeDetectionResult`
- **`policy.py`**: `IdentityPolicy` loads `config/identity_policy.yml` and drives resolve/allocate/auto-confirm behaviour per entity type
- **`repository.py`**: async repositories for all six identity tables
- **`service.py`**: `IdentityService` orchestrates the full resolution and binding lifecycle
- **`types.py`**: `StrEnum` types for identity state, binding method, and change outcomes

Per-entity identity tracking values (defined in `sead_standard_model.yml` in the Shape Shifter repo): `tracked` (UUID + PK, aggregate roots), `reconciled` (matched by business key), `derived` (composed from FK references), `child` (inherits parent identity).

### Schema Generation (`src/scripts/`, `schema/`)

Entity database views, indexes, and search functions are **generated** from `config/entities.yml` using Jinja2 templates in `schema/templates/`. Run `make generate-schema` after editing entity config. Never edit files in `schema/generated/` directly.

---

## Key Flows

### Reconciliation request

```
OpenRefine → POST /reconcile
  ↓
router.py: parse form/JSON → ReconQuery validation
  ↓
reconcile_queries(): for each query
  ├─ Strategies.get(entity_type) → strategy instance
  ├─ strategy.find_candidates(query, properties, limit)
  │   ├─ parse property hints (e.g., lat/lon)
  │   ├─ check alternate identity (DOI, site code)
  │   ├─ repository.find(query, limit) → trigram SQL → PostgreSQL
  │   └─ [RAG path] LLM validate top candidates
  └─ strategy.as_candidate(data, query) → OpenRefine format
  ↓
ReconBatchResponse → JSON
```

### Identity resolution

```
Submission tool → POST /identity/resolve
  ↓
identity_router.py: validate ResolutionRequest
  ↓
IdentityService.resolve_identity()
  ├─ get_or_create_scope(source_system)
  ├─ create_submission()
  ├─ for each source identity:
  │   ├─ policy.get_entity_policy(entity_type) → behaviour flags
  │   ├─ lookup existing binding in identity tables
  │   ├─ [miss] allocate UUID / reconcile via Authority Service
  │   └─ bind(source_id → UUID)
  └─ return BindingSet (proposed or auto-confirmed)
  ↓
ResolutionOutcome → JSON
```

---

## Data and Persistence Design

**No application database of its own.** The service reads entity data from the SEAD PostgreSQL database (via generated `authority.*` views) and writes identity and binding records to six identity tables in the same database.

**Entity views**: generated SQL in `schema/generated/` defines views (`authority.view_site`, etc.), trigram indexes, and optional embedding tables (`authority.method_embeddings`). The authority schema is logically separate from the SEAD `public` schema.

**Identity tables**: `identity_scopes`, `identity_submissions`, `source_identities`, `tracked_identities`, `binding_sets`, `bindings`. All managed exclusively by the identity service; no other component writes to them.

**Configuration files**: `config/*.yml` are the source of truth for entity schema definitions and identity policy. They are read-only at runtime.

**No in-process cache**: there is no Redis, no session store, and no in-memory entity cache. Stateless across requests except for the connection pool singleton.

---

## Cross-Cutting Concerns

### Configuration resolution
All config access goes through `ConfigValue`. The config provider is initialized once at startup; code that runs before `setup_config_store()` completes cannot access config. FastAPI lifespan handles initialization order.

### Import-time registration
Strategies register at import time. A strategy file that is never imported is never registered. Import errors during startup are logged but do not halt startup — the strategy is silently absent. This is a known risk for new strategies.

### Async and the connection pool
All database I/O and LLM calls are async. The connection pool is async (psycopg3 `AsyncConnectionPool`). Never call `asyncio.run()` inside a request handler or loader. The service can run with multiple Uvicorn workers because there is no in-process shared state beyond the connection pool.

### Logging
Loguru throughout. All modules use `from loguru import logger`. No `print()` for diagnostic output.

### Security
- All SQL uses parameterized queries; no string interpolation with user input.
- Database credentials are read from environment variables at startup; never logged or included in responses.
- Pydantic validates all inbound request bodies at the API boundary.
- The service has no authentication layer; it is expected to run inside a trusted network or behind a reverse proxy.

---

## Constraints and Assumptions

- **PostgreSQL extensions required**: `pg_trgm` (fuzzy search), `pgvector` (semantic search, optional), `PostGIS` (site proximity, optional). Without them the corresponding strategy features are unavailable.
- **Ollama or LLM API key required for RAG strategies**: strategies that use LLM validation will fail at runtime without a configured provider.
- **Schema generation is not automatic**: entity view changes require `make generate-schema` and a manual SQL deployment step.
- **No built-in TLS**: TLS termination is expected upstream.
- **Single `.env` file per environment**: multi-environment config is managed by supplying different `.env` files and optionally overriding `CONFIG_FILE`.

---

## Design Decisions and Tradeoffs

| Decision | Rationale | Tradeoff |
|---|---|---|
| Strategy auto-registration via decorator | Zero boilerplate to add a new entity type | Silent failure if strategy file is not imported |
| `ConfigValue` lazy resolution | Enables mocking in tests without patching env | All callers must use `ConfigValue`; direct dict access is a violation |
| Connection pool as runtime config value | Keeps initialization in one place (`setup.py`) | Indirect access pattern; pool must be initialized before first use |
| Generated entity views | Single source of truth in `entities.yml`; schema consistent with config | Schema changes require a separate deployment step |
| Embedded MCP server | No separate process; simpler deployment | MCP server shares the FastAPI process; cannot scale independently |
| SIMS co-located with reconciliation | Shared PostgreSQL connection and config; single container | Both functions scale together; cannot deploy separately |
| No in-process cache | Stateless; supports multiple workers | Repeated identical queries hit the database each time |

---

## Known Limitations and Technical Debt

- **Sequential batch processing**: reconciliation batch queries are processed one at a time; parallel execution is not yet implemented.
- **No request authentication**: any client with network access can submit reconciliation or identity requests.
- **LLM error recovery is partial**: if an LLM call fails mid-batch, the affected queries may return empty results rather than falling back gracefully to fuzzy results.
- **Embedding generation is offline**: `authority.*_embeddings` tables must be populated by a separate script; there is no automatic re-embedding on entity data change.
- **Schema deployment is manual**: `make generate-schema` produces SQL but does not apply it to the database; deployment is a manual operator step.

---

## Related Documents

- [DEVELOPMENT.md](DEVELOPMENT.md) — local setup, contributor workflow, and common commands
- [TESTING.md](TESTING.md) — test strategy, levels, and repository-specific testing guidance
- [OPERATIONS.md](OPERATIONS.md) — environments, deployment, CI/CD, rollback, and observability
- [SIMS documentation](SIMS/) — REQUIREMENTS, DESIGN_VIEW, IMPLEMENTATION_VIEW, ASSESSMENT, TRACKED_ENTITIES
- API reference: `http://localhost:8000/docs` (Swagger) or `/redoc` when running locally

