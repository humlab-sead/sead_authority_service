# SEAD Authority Service - AI Coding Instructions

Keep this file small and always-on. Use `.github/instructions/*.instructions.md` for task-specific guidance.

## Documentation scope

- Use `docs/` (current). Ignore `docs/archive/`. Treat `docs/proposals/` as future backlog unless actively working on a proposal.
- For proposal work: follow `.github/instructions/proposal-writing-guide.instructions.md` and use `docs/templates/PROPOSAL_TEMPLATE.md`.

## Documentation Evidence

- Treat current code, configuration, scripts, workflows, and generated artifacts as authoritative for the behavior each implements.
- Treat `docs/archive/` as historical context, not current practice.
- Verify documentation claims against the source that implements or executes the described behavior.

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

## Always-on architecture rules

- All reconciliation strategies **must** be decorated with `@Strategies.register(key=..., repository_cls=...)`. Strategies auto-register on import via `src/strategies/__init__.py`.
- Use `ConfigValue` for all config lookups — never read config dicts directly. Supports colon-separated paths and comma-separated fallbacks.
- **Never** create DB connections directly. Use `get_connection()` from `src.configuration` — connection is a singleton created at startup.
- Entity schemas are **generated** from `config/entities.yml` via `make generate-schema`. Never edit files in `schema/generated/` directly.
- Use absolute imports only: `from src.*`. Ruff enforces `ban-relative-imports = "parents"`.

## Workflow expectations

- Serve: `make serve` (uvicorn :8000 with reload). Dev mode: `make dev-serve` (uvicorn + OpenRefine :3333).
- Test: `make test` or `uv run pytest tests -v`. Integration tests: `uv run pytest -m integration`.
- Code quality: line length 140; format with `make tidy` (Black + isort); use `loguru.logger`; add type hints to all functions; use `snake_case` for modules and variables and `PascalCase` for classes.
- Lint: `make lint`. Format: `make tidy`. Import check: `make check-imports`.
- Schema: `make generate-schema` after editing `config/entities.yml`.
- Use the unified environment at `.venv/` for Python work.
- Run targeted tests for the changed area before finishing.
- Run broader tests when a change crosses layers.
- When completing work tracked by a task or phase plan, update its progress tracker, checklist, status, and deliverables in the same change; do not leave completed work marked as not started.
- When drafting a pull request title or description, follow `.github/pr-description-instructions.md`. Use `.github/promotion_pr_template.md` for promotions (`dev` into `staging` or `staging` into `main`), and `.github/pull_request_template.md` for other pull requests.
- When uncommitted work must reach `dev` through review, run `scripts/workflow/create_change_pr.py` instead of assembling branch, commit, push, and `gh pr create` calls by hand. Pass `--closes <issue>` for every issue the change resolves.
- Prepare and publish a promotion with `scripts/workflow/promote_dev_to_staging.sh prepare` and `publish <number>`. The script verifies that code changes reached the source branch through pull requests.

## Cross-cutting instructions

- `writing-style.instructions.md`: prose, docstrings, PR text, and AI coding-agent instructions
- `diagrams.instructions.md`: Mermaid diagram style and conventions
- `github-workflow.instructions.md`: issue creation and commit workflow

## graphify

graphify is a uv tool (`~/.local/bin/graphify`), not part of the project `.venv`. The graph in `graphify-out/` is built locally and is not committed; git hooks installed by `make install-graphify` rebuild it after commit, checkout, merge and rebase. When `graphify-out/graph.json` exists, run `graphify query "<question>"` before broad codebase exploration, architecture searches, or relationship searches. Use `graphify path "<source>" "<target>"` for a specific relationship and `graphify explain "<concept>"` for a focused concept. Verify graphify results against current source code, tests, configuration, and applicable instructions. Use `rg` or targeted file reads for exact text and local implementation details. Do not run `graphify update` after every edit; run `GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update .` only when you changed code and need to query the graph before committing. Follow the full graphify quick start and fallback guidance in `AGENTS.md`.

<!-- rtk-instructions v2 -->
**rtk** is a CLI proxy that filters and compresses command outputs, saving 60-90% tokens.

Use `rtk` for shell commands unless raw output, shell built-ins, or interactive commands require otherwise.

Examples:
```bash
rtk uv run pytest
rtk make test
rtk pylint src/
rtk git status
rtk git log -10
rtk cat docs/proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md
```

If `rtk` fails, retry without it.

Meta: `rtk gain`, `rtk gain --history`, `rtk discover`, `rtk proxy <cmd>`
<!-- /rtk-instructions -->
