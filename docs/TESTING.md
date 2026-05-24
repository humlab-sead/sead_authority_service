# SEAD Authority Service - Testing Guide

## Purpose

This guide describes how the SEAD Authority Service is tested: what test levels exist, what each level covers, how to run tests, and what is expected before merging. For local environment setup see [DEVELOPMENT.md](DEVELOPMENT.md). For runtime and deployment see [OPERATIONS.md](OPERATIONS.md).

---

## Testing Goals

- Catch regressions in reconciliation query logic, result ranking, and response formatting.
- Validate that reconciliation strategy auto-registration works correctly and that each registered strategy resolves against its expected entity type.
- Ensure the SIMS identity module (resolve, bind, confirm, change-detect) handles lifecycle state correctly.
- Confirm API routes produce correct OpenRefine-compatible responses and error formats.
- Prevent `ConfigValue` resolution failures and `get_connection()` misuse from reaching production.

---

## Test Levels and Responsibilities

### Core module tests (`tests/`)

Unit tests for the service's internal modules. These run without a database or running service. Located in `tests/` and its subdirectories.

| Directory | What it covers |
|-----------|---------------|
| `tests/` | Reconciliation, suggest, preview, metadata, and utility orchestration |
| `tests/api/` | Router request/response handling, Pydantic model validation |
| `tests/strategies/` | Per-entity strategy behaviour, registry lookup, query building |
| `tests/identity/` | SIMS models, policy, service, and API endpoint tests |
| `tests/configuration/` | Config loading, `ConfigValue` resolution, env var handling |
| `tests/llm/` | LLM provider abstraction and prompt formatting |
| `tests/mcp/` | MCP server search_lookup tool |
| `tests/geonames/` | GeoNames module |

### Integration tests (`tests/integration/`)

Marked `integration` and excluded from the standard test run. These require a live PostgreSQL database and optionally Ollama.

Currently covers:
- `test_reconcile_integration.py` — end-to-end reconciliation against a real SEAD database
- `tests/identity/test_service_integration.py` — SIMS service against a live database

Run explicitly when testing against a real database or validating query performance.

### Manual testing

Tests requiring specific external setup (OpenRefine running, specific seed data) are marked `manual` and excluded from all automated runs. Run locally only when verifying a specific integration scenario.

---

## Test Environment

- Python tests: run via `uv run` to use the project `.venv/`. No database needed unless the test is marked `integration`.
- `asyncio_mode = "auto"` is set in `pyproject.toml` — `@pytest.mark.asyncio` is accepted but not required on individual async tests.
- The directories `tests/integration/` and `tests/manual/` are excluded from pytest's default discovery via `norecursedirs` in `pyproject.toml`. Integration tests must be invoked explicitly.
- For integration tests: provide DB credentials via `.env` (see [DEVELOPMENT.md](DEVELOPMENT.md)) and ensure the target database has `pg_trgm` installed.

### pytest markers

| Marker | Meaning | Run in CI? |
|--------|---------|-----------|
| `integration` | Hits real PostgreSQL or Ollama | No |
| `manual` | Requires manual environment setup | No |
| `debug` | Debugging helpers, not assertions | No |
| `identity` | SIMS identity module tests | Yes (no DB required) |

---

## Test Data, Fixtures, and Mocking Strategy

- **`tests/config/config.yml`**: override config used in tests — points to mock or in-memory resources instead of production databases.
- **`tests/conftest.py`**: session-scoped logging setup; `MockConfigProvider` for config isolation; `MockRow` for simulating psycopg row responses without a real connection.
- **`tests/identity/conftest.py`**: identity-specific fixtures covering mock repositories and pre-built domain objects.
- **Mocking strategy**: tests mock at the service boundary. Repositories that call the database receive `AsyncMock` patches. Pure logic (models, policy, config resolution) is tested directly without mocking.
- **`MockConfigProvider`**: prevents tests from triggering `setup_config_store()` and avoids any real DB connection being opened.
- Do not add `print` statements or debug logging to tests. Use `pytest -s` locally to see stdout when debugging.

---

## Test Execution Commands

```bash
# Full standard test suite (excludes integration and manual)
make test
uv run pytest tests -v

# Single test or test file
uv run pytest tests/test_reconcile.py -v -s
uv run pytest tests/strategies/test_registry.py::test_name -v

# Integration tests only (requires DB)
uv run pytest -m integration

# Skip all external tests explicitly
uv run pytest tests -v -m "not integration and not manual and not debug"

# With coverage report
make test-coverage         # outputs HTML to htmlcov/
```

---

## Validation Before Merge

Before opening a pull request:

1. Run the full standard test suite:
   ```bash
   make test
   ```

2. Format and lint:
   ```bash
   make tidy && make lint
   ```

3. For changes to reconciliation query logic, strategy registration, or the SIMS service layer: run the relevant strategy and identity test directories explicitly and confirm no regressions.

4. Add or update tests for any bug fixed or feature added. Regression tests should be narrow and tied to the specific broken input or entity type.

5. If a new reconciliation strategy is added: add a corresponding test in `tests/strategies/` that verifies registration and a basic query response structure.

---

## CI Test Execution

The `docker-build.yml` workflow runs on every push to `main` and on manual dispatch. It gates the Docker build behind a test step:

```
Run tests (uv run pytest --verbose)
Run linter (uv run ruff check src/ tests/)
  ↓ (only if both pass)
Build and push Docker image to GHCR
```

Integration tests are excluded from CI automatically (via `norecursedirs` in `pyproject.toml`). Only the standard unit test suite runs in CI.

The `release.yml` workflow runs semantic-release on `main` pushes independently — it does not run tests and does not gate releases on test results. Passing tests before merge is therefore the contributor's responsibility.

---

## Troubleshooting

**Strategy tests fail with `KeyError` on registry lookup:**
Strategy registration happens at import time via `@Strategies.register(...)`. If a strategy module is not imported, it is not registered. In tests, import the strategy explicitly or ensure `src.strategies` is imported.

**`ConfigValue` raises outside application context:**
Use `MockConfigProvider` from `tests/conftest.py` to inject config values without initialising `ConfigStore`. See existing identity and strategy tests for usage patterns.

**Async test failures (`Event loop is closed`):**
`asyncio_mode = "auto"` is active. Mismatched fixture scopes cause this — ensure async fixtures use the same scope as the test function.

**Integration tests fail with connection errors:**
Verify `.env` credentials and that the database host is reachable from your machine. Confirm `pg_trgm` is installed: `CREATE EXTENSION IF NOT EXISTS pg_trgm;`.

**pytest collects no tests:**
Confirm test files match `test_*.py` and test functions match `test_*`. The `tests/integration/` and `tests/manual/` directories are excluded by default — pass them explicitly if you want to run them.

---

## Related Documents

- [DEVELOPMENT.md](DEVELOPMENT.md) — local setup, commands, and contributor workflow
- [DESIGN.md](DESIGN.md) — architecture, component responsibilities, and design decisions
- [OPERATIONS.md](OPERATIONS.md) — environments, deployment, CI/CD, and rollback
- [SIMS documentation](SIMS/) — identity module design and requirements
