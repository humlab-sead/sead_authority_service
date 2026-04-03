# SEAD Authority Service - AI Coding Agent Instructions

## Project Overview

FastAPI-based reconciliation service for SEAD (Strategic Environmental Archaeology Database) implementing the **OpenRefine Reconciliation API**. Core function: match fuzzy text queries to canonical entity identifiers from archaeological/environmental database.

**Key architectural insight**: This is a registry-based plugin system where reconciliation strategies auto-register via decorators and are looked up at runtime by entity type.

## Critical Patterns

### 1. Strategy Registry Pattern
All entity reconciliation strategies **must** be decorated with `@Strategies.register()`:

```python
from src.strategies.strategy import ReconciliationStrategy, Strategies

@Strategies.register(key="site", repository_cls=SiteRepository)
class SiteReconciliationStrategy(ReconciliationStrategy):
    # Implementation
```

**Why**: Strategies auto-register on import. [main.py](main.py#L7) imports `src.strategies` which triggers recursive module loading in [src/strategies/\_\_init\_\_.py](src/strategies/__init__.py) that instantiates all decorated classes.

### 2. Configuration Resolution with ConfigValue
Use `ConfigValue` for lazy config resolution instead of direct lookups:

```python
from src.configuration import ConfigValue

# Lazy resolution with fallback
threshold = ConfigValue("options:auto_accept_threshold", default=0.90).resolve()

# Multi-path fallback (checks each path in order)
model = ConfigValue("llm.ollama.model,llm.model", default="llama3").resolve()
```

**Location**: [src/configuration/resolve.py](src/configuration/resolve.py). Supports colon-separated paths (`options:database:dbname`) and comma-separated fallbacks.

### 3. Database Connection Singleton
**Never** create database connections directly. Use the config provider pattern:

```python
from src.configuration import get_connection

async with await get_connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute(query, params)
```

Connection is created once at startup via [src/configuration/setup.py](src/configuration/setup.py#L50) and stored in runtime config.

### 4. Schema Generation from Templates
Entity schemas are **generated**, not hand-written. To add a new entity:

1. Add entity config to [config/entities.yml](config/entities.yml)
2. Run `make generate-schema` (calls [src/scripts/generate_entity_schema.py](src/scripts/generate_entity_schema.py))
3. Generated SQL appears in [schema/generated/](schema/generated/)

**Do not** edit generated files directly. Edit [schema/templates/](schema/templates/) or [config/entities.yml](config/entities.yml) instead.

## Development Workflows

### Running the Service
```bash
make serve           # Development with auto-reload
make dev-serve       # Start uvicorn + OpenRefine together
make dev-stop        # Stop both services
```

**Port**: 8000 (uvicorn), 3333 (OpenRefine). PIDs written to `uvicorn.pid` and `refine.pid`.

### Testing
```bash
make test            # Run pytest suite
uv run pytest -m integration  # Integration tests only (require DB/Ollama)
uv run pytest -k test_name     # Run specific test
```

**Test markers**: `@pytest.mark.integration`, `@pytest.mark.manual`, `@pytest.mark.debug` (see [pyproject.toml](pyproject.toml#L119)).

### Code Quality
```bash
make lint            # Run tidy + pylint + check-imports
make tidy            # Run black + isort
make check-imports   # Verify no relative imports beyond current package
```

**Import rules**: Ruff enforces `ban-relative-imports = "parents"` (see [pyproject.toml](pyproject.toml#L46)). Use absolute imports from `src.*`.

## Architecture Deep Dive

### Request Flow
```
OpenRefine → POST /reconcile → router.py:reconcile() →
  reconcile.py:reconcile_queries() →
    Strategies.get("site") → SiteReconciliationStrategy →
      SiteRepository.search() → PostgreSQL
```

### SIMS Identity Module (`src/identity/`)

The SEAD Identity Management System (SIMS) is integrated into this service. It provides identity policy and allocation logic for incoming SEAD data submissions.

**Design docs**: [docs/sims/](docs/sims/) — REQUIREMENTS, DESIGN_VIEW, IMPLEMENTATION_VIEW, ASSESSMENT, TRACKED_ENTITIES.

**Planned submodules** (implementation not yet started):
- `src/identity/models.py` — Domain models: `IdentityEvidence`, `AllocationResult`, `ResolutionRequest`, `IdentityRecord`
- `src/identity/policy.py` — Resolve → Allocate → Map decision logic driven by entity `identity_tracking` and `reconciliation` properties
- `src/identity/registry.py` — UUID minting, identity evidence recording, idempotency against `identity_registry` table

**Entity metadata source of truth**: `sead_standard_model.yml` in the Shape Shifter repo defines per-entity `identity_tracking` and `reconciliation` properties that drive SIMS policy decisions.

**Key identity tracking values**: `tracked` (UUID + PK, aggregate roots), `reconciled` (matched by business key), `derived` (identity from FK references), `child` (inherits parent aggregate identity).

**Do not** place identity SQL scripts in `schema/sql/` until the `identity_registry` and `identity_evidence` tables are designed.

### RAG Hybrid Strategy (New Pattern)
Phase 1 implementation uses embedded MCP server for small-prompt reconciliation:

```python
from src.strategies.rag_hybrid import RAGHybridReconciliationStrategy

class MethodReconciliationStrategy(RAGHybridReconciliationStrategy):
    # Uses MCP search_lookup → 5-10 candidates → LLM validation
```

**Feature flag**: `features.use_mcp_server` in [config/config.yml](config/config.yml#L48). When disabled, falls back to standard fuzzy search.

### Multi-Environment Config
- **Base config**: [config/config.yml](config/config.yml)
- **Entity schemas**: [config/entities.yml](config/entities.yml)
- **LLM prompts**: [config/prompts.yml](config/prompts.yml)
- **Environment vars**: `.env` (loaded via [src/configuration/setup.py](src/configuration/setup.py#L12))

Override config file: `export CONFIG_FILE=./tests/config/config.yml`

## Common Gotchas

1. **Strategy not found**: Ensure strategy file is in `src/strategies/` and decorated with `@Strategies.register()`. Import errors are printed to console during startup but don't fail startup.

2. **Config not available**: Call `await setup_config_store()` before accessing config. FastAPI does this in [main.py](main.py#L20) startup event.

3. **Schema changes ignored**: Run `make generate-schema` after editing [config/entities.yml](config/entities.yml). The `--force` flag overwrites existing files.

4. **Test isolation**: Use fixtures from [tests/conftest.py](tests/conftest.py). `MockConfigProvider` prevents tests from hitting real database.

5. **LLM provider setup**: Ollama/OpenAI providers lazy-load config. See [src/llm/providers/](src/llm/providers/) for provider-specific settings.

## Git Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/) with **semantic-release** for automated versioning. AI agents making commits must follow this format:

```
<type>[optional scope]: <description>
```

### Release-Triggering Types
- **feat**: New feature → **MINOR** release (1.2.0)
- **fix**: Bug fix → **PATCH** release (1.2.1)
- **refactor/perf/style**: Code improvements → **PATCH** release
- **docs**: Documentation → **PATCH** if scope is README
- **test/build/ci/chore**: No release

### Breaking Changes
Add `!` after type/scope or `BREAKING CHANGE:` in footer → **MAJOR** release (2.0.0):
```bash
feat(api)!: change response format for validation errors
```

### Common Scopes
`core`, `config`, `api`, `cache`, `loaders`, `tests`, `deps`

### Examples
```bash
feat(cache): implement hash-based cache invalidation
fix(validation): prevent null pointer in entity resolution
refactor(core): simplify dependency resolution logic
docs(README): update installation instructions
test(loaders): add comprehensive UCanAccessSqlLoader tests
```

**Rules**: Use imperative mood, lowercase description, no trailing period, keep under 72 chars.

## Key Files Reference

- [main.py](main.py) - FastAPI app entry point, imports strategies
- [src/api/router.py](src/api/router.py) - All HTTP endpoints
- [src/reconcile.py](src/reconcile.py) - Core reconciliation logic
- [src/strategies/strategy.py](src/strategies/strategy.py) - Base strategy class and registry
- [src/configuration/](src/configuration/) - Config provider pattern
- [src/identity/](src/identity/) - SIMS identity module (stub; implementation pending)
- [config/entities.yml](config/entities.yml) - Entity definitions (source of truth)
- [docs/sims/](docs/sims/) - SIMS design documentation
- [Makefile](Makefile) - All developer commands

## Docker Deployment

Multi-environment support:
- **Development**: `cd docker && docker-compose up --build`
- **Production**: Uses GHCR images from CI/CD (see [docker/README.md](docker/README.md))

GitHub Actions builds on every push to `main`/`dev` and pushes to `ghcr.io/humlab-sead/sead_authority_service`.
