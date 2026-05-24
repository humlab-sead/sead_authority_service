# SEAD Authority Service - AI Coding Instructions

This file is always-on. Put task-specific guidance in `.github/instructions/` so it loads only when relevant.

## Repository structure

- `src/`: core Python service — reconciliation strategies, identity module, config, LLM providers
- `src/strategies/`: reconciliation strategy plugins (auto-registered via decorator)
- `src/identity/`: SIMS identity module (UUID allocation, binding lifecycle)
- `src/api/`: FastAPI routers — reconciliation and identity endpoints
- `src/configuration/`: config provider, `ConfigValue`, DB connection singleton
- `config/`: `config.yml`, `entities.yml`, `prompts.yml`, `identity_policy.yml`
- `tests/`: pytest suite; integration tests require DB + Ollama
- Python environment: `.venv/` at repo root

Request flow: `OpenRefine → POST /reconcile → router.py → reconcile.py → Strategies.get(type) → XxxStrategy → XxxRepository → PostgreSQL`

## Architecture invariants

- All reconciliation strategies **must** be decorated with `@Strategies.register(key=..., repository_cls=...)`. Strategies auto-register on import via `src/strategies/__init__.py`.
- Use `ConfigValue` for all config lookups — never read config dicts directly. Supports colon-separated paths and comma-separated fallbacks.
- **Never** create DB connections directly. Use `get_connection()` from `src.configuration` — connection is a singleton created at startup.
- Entity schemas are **generated** from `config/entities.yml` via `make generate-schema`. Never edit files in `schema/generated/` directly.
- Use absolute imports only: `from src.*`. Ruff enforces `ban-relative-imports = "parents"`.

## Code conventions

- Line length: 140. Format with `make tidy` (Black + isort).
- Logging: `loguru.logger`. All functions must have type hints.
- Naming: `snake_case` for modules and variables, `PascalCase` for classes.

## Workflow

- Serve: `make serve` (uvicorn :8000 with reload). Dev mode: `make dev-serve` (uvicorn + OpenRefine :3333).
- Test: `make test` or `uv run pytest tests -v`. Integration tests: `uv run pytest -m integration`.
- Lint: `make lint`. Format: `make tidy`. Import check: `make check-imports`.
- Schema: `make generate-schema` after editing `config/entities.yml`.
- Run targeted tests before finishing; broader tests when a change crosses layers.

## Documentation scope

- Use `docs/` (current). Ignore `docs/archive/`. Treat `docs/proposals/` as future backlog unless actively working on a proposal.
- For proposal work: follow `.github/instructions/proposal-writing-guide.instructions.md` and use `docs/templates/PROPOSAL_TEMPLATE.md`.

## Scoped instructions

Instruction files auto-load via `applyTo:` when a matching file is open — no manual reference needed:

- `python.instructions.md` — all `src/**/*` Python files
- `readme.instructions.md` — `README.md`
- `design.instructions.md` — `docs/DESIGN.md`
- `development.instructions.md` — `docs/DEVELOPMENT.md`
- `testing.instructions.md` — `docs/TESTING.md`
- `operations.instructions.md` — `docs/OPERATIONS.md`
- `proposal-writing-guide.instructions.md` — `docs/proposals/**`

Cross-cutting (no path trigger — load when relevant):
- `diagrams.instructions.md`: Mermaid diagram style and conventions
- `github-workflow.instructions.md`: issue creation and commit workflow
