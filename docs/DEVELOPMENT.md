# SEAD Authority Service - Developer Guide

## Purpose

This guide covers everything a developer needs to set up, run, modify, and validate the SEAD Authority Service codebase day-to-day. For architecture and design decisions see [DESIGN.md](DESIGN.md). For deployment and operations see [OPERATIONS.md](OPERATIONS.md).

---

## Prerequisites

**Required:**
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Git

**Optional:**
- PostgreSQL — required for integration tests and local reconciliation against real SEAD data
- Ollama — required for LLM integration tests using local models
- OpenAI / Anthropic API key — required for cloud LLM strategies
- OpenRefine — required to test the reconciliation API end-to-end via the UI (`make dev-serve`)

---

## Local Setup

```bash
git clone https://github.com/humlab-sead/sead_authority_service.git
cd sead_authority_service
make install
```

`make install` creates `.venv/` and runs `uv pip install -e .`. All subsequent commands use `uv run` to invoke tools within that environment.

---

## Local Configuration

Create a `.env` file in the repo root (not committed) with your local values:

```ini
CONFIG_FILE=./config/config.yml

# Database (required for integration tests)
SEAD_AUTHORITY_OPTIONS_DATABASE_HOST=localhost
SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME=sead_staging
SEAD_AUTHORITY_OPTIONS_DATABASE_USER=humlab_admin
SEAD_AUTHORITY_OPTIONS_DATABASE_PORT=5433

# LLM provider (optional; required for RAG strategies)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

To run against a different config file:

```bash
export CONFIG_FILE=./tests/config/config.yml
```

For PostgreSQL passwords, prefer `~/.pgpass` over environment variables.

See `config/config.yml` and `docker/production/.env` for a full list of supported variables. For production/deployment configuration see [OPERATIONS.md](OPERATIONS.md).

---

## Project Structure

```
sead_authority_service/
├── main.py                  # FastAPI app entry point; imports all strategies
├── src/
│   ├── api/
│   │   ├── router.py        # Reconciliation endpoints (/reconcile, /suggest/*, /flyout/*)
│   │   └── identity_router.py  # SIMS endpoints (/identity/*)
│   ├── configuration/       # ConfigValue, get_connection(), setup_config_store()
│   ├── identity/            # SIMS module (models, policy, repository, service, types)
│   ├── llm/                 # LLM provider abstraction (OpenAI, Anthropic, Ollama)
│   ├── mcp/                 # Embedded MCP server (search_lookup tool)
│   ├── strategies/          # Reconciliation strategies (auto-registered via decorator)
│   ├── reconcile.py         # Batch reconciliation orchestrator
│   ├── suggest.py           # Autocomplete orchestrator
│   └── preview.py           # Entity preview orchestrator
├── config/
│   ├── config.yml           # Base configuration (includes entities.yml, prompts.yml)
│   ├── entities.yml         # Entity schema definitions (source of truth)
│   ├── prompts.yml          # LLM prompt templates
│   └── identity_policy.yml  # Per-entity SIMS policy
├── schema/
│   ├── templates/           # Jinja2 templates for SQL generation
│   └── generated/           # Generated SQL (do not edit directly)
├── tests/                   # pytest suite
├── docker/                  # Container definitions and deployment configs
├── scripts/                 # Developer and admin scripts
├── pyproject.toml           # Dependencies and tool configuration
└── Makefile                 # All supported development commands
```

The strategy auto-registration mechanism depends on `main.py` importing `src.strategies`, which triggers recursive module loading. A strategy file that is not in `src/strategies/` will never be registered.

---

## Common Development Commands

All supported commands are defined in `Makefile`.

### Running locally

```bash
make serve           # uvicorn on http://localhost:8000 with --reload
make debug-serve     # same, with --log-level debug
make dev-serve       # uvicorn :8000 + OpenRefine :3333 (backgrounded)
make dev-stop        # graceful stop of both processes
make dev-kill        # forceful kill of both processes
```

API docs are available at `http://localhost:8000/docs` when the service is running.

### Testing

```bash
make test                                  # Full pytest suite
make test-coverage                         # Run with HTML coverage report

uv run pytest tests -v                     # All tests, verbose
uv run pytest tests -v -k test_name        # Single test by name
uv run pytest -m integration               # Integration tests only (require DB)
uv run pytest -m "not integration"        # Unit tests only
```

Test markers (`pyproject.toml`):

| Marker | Purpose |
|--------|---------|
| `integration` | Hits real PostgreSQL or Ollama |
| `manual` | Requires manual environment setup |
| `debug` | Debugging helpers, not part of CI |
| `identity` | SIMS identity module tests |

Integration tests are excluded from `testpaths` by default. Run them explicitly with `-m integration`.

### Code quality

```bash
make tidy            # Format: black + isort
make pylint          # Pylint check
make ruff-lint       # Ruff lint + auto-fix
make lint            # tidy + pylint + ruff-lint (full pass)
make check-imports   # Verify no relative imports beyond current package
make dead-code       # Vulture dead code check
```

Run `make tidy && make lint` before opening a pull request.

### Schema generation

```bash
make generate-schema         # Generate SQL from config/entities.yml (skips existing)
make generate-schema-force   # Regenerate all (overwrites existing)
```

Run this after editing `config/entities.yml`. Never edit files in `schema/generated/` directly.

---

## Code Conventions

### Python

- Python 3.13+; always invoke via `uv run` to use the project `.venv/`.
- Absolute imports only: `from src.strategies.strategy import ...` — never relative across packages. Ruff enforces `ban-relative-imports = "parents"`.
- Line length: 140 characters (configured in `pyproject.toml`).
- Logging: `from loguru import logger` everywhere — do not use `print` or stdlib `logging`.
- Type hints required on all function signatures.
- Naming: `snake_case` for modules and variables; `PascalCase` for classes.

### Architecture invariants (critical)

- **Strategy registration**: every strategy class must be decorated with `@Strategies.register(key=..., repository_cls=...)`. No registration = no runtime availability.
- **Config access**: always use `ConfigValue(...).resolve()`. Never read config dicts directly.
- **Database connections**: always use `get_connection()` from `src.configuration`. Never instantiate connections or pools directly.
- **Generated schema**: run `make generate-schema` after entity config changes. Never hand-edit `schema/generated/`.

See [DESIGN.md](DESIGN.md) for the full architecture and invariant rationale.

---

## Development Workflow

1. **Create a branch** from `dev`:
   ```bash
   git checkout dev && git pull
   git checkout -b feature/my-feature
   ```

2. **Make changes.** Run `make serve` and test locally. For reconciliation UI testing, use `make dev-serve` with OpenRefine pointed at `http://localhost:8000/reconcile`.

3. **Run targeted tests** for the changed area. Run `make test` when the change crosses layers.

4. **Format and lint** before committing:
   ```bash
   make tidy && make lint
   ```

5. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat(scope): ...` — new feature → minor release
   - `fix(scope): ...` — bug fix → patch release
   - `refactor`, `test`, `chore`, `docs` — no release
   - Append `!` or use `BREAKING CHANGE:` footer for major releases
   - Common scopes: `core`, `config`, `api`, `identity`, `strategies`, `tests`, `deps`

6. **Open a pull request** against `dev`. Semantic-release runs on merges to `main` and generates version tags and `CHANGELOG.md` automatically.

---

## Adding a New Entity Type

1. Add the entity definition to `config/entities.yml`.
2. Run `make generate-schema` and deploy the generated SQL to the target database.
3. Create a strategy class in `src/strategies/`:

   ```python
   from src.strategies.strategy import ReconciliationStrategy, Strategies
   from src.strategies.query import BaseRepository

   @Strategies.register(key="my_entity", repository_cls=BaseRepository)
   class MyEntityReconciliationStrategy(ReconciliationStrategy):
       pass  # inherits all default behaviour
   ```

4. The strategy is available at runtime immediately after the file is imported. No manual registration step needed.

---

## Debugging and Troubleshooting

**Service won't start:**
```bash
uv run uvicorn main:app --reload   # run directly for full traceback
lsof -i :8000                      # check if port is in use
```

**Strategy not found at runtime:**
- Confirm the file is in `src/strategies/` and decorated with `@Strategies.register(...)`.
- Check startup logs — import errors are printed but do not halt startup.

**Config not available:**
- Ensure `setup_config_store()` runs before any `ConfigValue` is resolved. FastAPI lifespan handles this; tests must call it explicitly or use `MockConfigProvider`.

**Integration tests failing with DB errors:**
- Verify `.env` credentials and that the database host is reachable.
- Confirm `pg_trgm` is installed on the target database.

**Import errors in tests:**
```bash
uv run pytest tests -v   # uv sets PYTHONPATH automatically
```

---

## Related Documents

- [DESIGN.md](DESIGN.md) — architecture, component responsibilities, key flows, design decisions
- [TESTING.md](TESTING.md) — test strategy, levels, and repository-specific testing guidance
- [OPERATIONS.md](OPERATIONS.md) — environments, deployment, CI/CD, rollback, and observability
- [SIMS documentation](SIMS/) — identity module design and requirements
- `.github/instructions/` — task-specific AI coding guidance (auto-loaded in VS Code Copilot)
- API reference: `http://localhost:8000/docs` when running locally
