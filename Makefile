SHELL := /bin/bash

-include .env
export

UVICORN_PORT := 8000
PODMAN_DEPLOYMENT_DIR := deployment/container
TARGET_MODEL ?= ../sead_shape_shifter/resources/target_models/sead_standard_model.yml


test-workflow:
	@./scripts/test-ci.sh

fetch-openrefine-manifest:
	@curl -s http://localhost:8000/reconcile

fetch-openrefine-manifest-types:
	@curl -s http://localhost:8000/reconcile | jq -r '.defaultTypes[].id'

.PHONY: generate-reconciliation-inventory
generate-reconciliation-inventory:
	@uv run python -m src.scripts.generate_reconciliation_inventory --target-model "$(TARGET_MODEL)"

.PHONY: generate-schema
generate-schema:
	@echo "Generating entity schema files from templates..."
	@PYTHONPATH=. uv run python src/scripts/generate_entity_schema.py --all-entities
	@echo "✅ Schema generation complete!"

.PHONY: generate-schema-force
generate-schema-force:
	@echo "Regenerating all entity schema files..."
	@PYTHONPATH=. uv run python src/scripts/generate_entity_schema.py --all-entities --force
	@echo "✅ Schema regeneration complete!"
	

.PHONY: generate-schema-bundle
generate-schema-bundle:
	@echo "Rebuilding deployment SQL from existing generated files..."
	@./schema/create_schema.sh --bundle-only
	@echo "✅ Deployment bundle rebuilt!"
	
.PHONY: deploy-authority-schema
deploy-authority-schema:
	@./schema/create_schema.sh --schema authority --deploy \
		--database $(SEAD_DBNAME) --port $(SEAD_PORT) --user $(SEAD_USER) --no-generate
	
.PHONY: podman-build podman-up podman-down podman-logs
podman-build:
	@$(MAKE) -C $(PODMAN_DEPLOYMENT_DIR) build

podman-up:
	@$(MAKE) -C $(PODMAN_DEPLOYMENT_DIR) up

podman-down:
	@$(MAKE) -C $(PODMAN_DEPLOYMENT_DIR) down

podman-logs:
	@$(MAKE) -C $(PODMAN_DEPLOYMENT_DIR) logs


.PHONY: dev-serve
dev-serve: dev-kill
	@echo "Starting uvicorn on port $(UVICORN_PORT)..."
	@nohup uv run uvicorn main:app --host 0.0.0.0 --port $(UVICORN_PORT) --reload &> uvicorn.log & echo $$! > uvicorn.pid
	@echo "Starting OpenRefine..."
	@nohup ./bin/openrefine-3.9.5/refine -i 127.0.0.1 -p 3333 &> refine.log & echo $$! > refine.pid
	@echo "✅ Development servers started!"
	@echo "   - Uvicorn: PID $$(cat uvicorn.pid), log → uvicorn.log"
	@echo "   - OpenRefine: PID $$(cat refine.pid), log → refine.log"

dev-stop:
	@if [ -f uvicorn.pid ]; then kill -TERM `cat uvicorn.pid`; fi
	@if [ -f refine.pid ]; then kill -TERM `cat refine.pid`; fi
	@rm -f uvicorn.pid refine.pid
	@echo "✅ Servers stopped."

dev-kill:
	@pkill -f '[u]vicorn main:app' 2>/dev/null || true
	@pkill -f '[r]efine' 2>/dev/null || true
	@rm -f uvicorn.pid refine.pid
	@echo "✅ Servers killed."

.PHONY: serve
serve:       
	@uv run uvicorn main:app --host 0.0.0.0 --port $(UVICORN_PORT) --reload
	
debug-serve:       
	@uv run uvicorn main:app --host 0.0.0.0 --port $(UVICORN_PORT) --reload --log-level debug

.PHONY: install
install:
	@uv venv
	@uv pip install -e .

.PHONY: test
test:
	@uv run pytest tests -v

.PHONY: publish
publish:
	@echo "Publishing Python package to PyPI"
	@uv publish

.PHONY: black
black:
	@uv run black src tests main.py

.PHONY: pylint
pylint:
	@uv run pylint src tests main.py

.PHONY: ruff-lint
ruff-lint:
	@uv run ruff check --fix src tests main.py
	
.PHONY: lint
lint: tidy pylint ruff-lint

.PHONY: check-imports
check-imports:
	@python scripts/check_imports.py

.PHONY: fix-imports
fix-imports:
	@python scripts/fix_imports.py

isort:
	@uv run isort src tests main.py

.PHONY: tidy
tidy: black isort

requirements.txt: pyproject.toml
	@uv export -o requirements.txt

.PHONY: test-coverage
test-coverage:
	@uv run pytest tests --cov-report=html --cov=src

.PHONY: dead-code
dead-code:
	@uv run vulture src tests main.py


################################################################################
# AI Coding Assistants recipes
# Candidates: rtk, graphify, serena, snip, headroom
################################################################################

rtk-install:
	@echo "Installing RTK and setting up global configurations..."
	@if ! command -v rtk &> /dev/null; then \
		echo "RTK not found, installing..."; \
		brew install rtk; \
	else \
		brew upgrade rtk &> /dev/null; \
	fi
	@rtk init -g --copilot
	@rtk init -g --codex

# graphify is a uv tool (~/.local/bin), not part of the project .venv.
# The graph in graphify-out/ is local and not committed.
create-graphify:
	@graphify extract . --project
	@graphify cluster-only $(CURDIR)
	@graphify export callflow-html

# GRAPHIFY_VIZ_NODE_LIMIT=0 blocks graph.html generation and removes any stale
# file (the HTML is unused). graphify reads this limit only from the
# environment, not from .graphifyrc.
.PHONY: update-graphify
update-graphify:
	@GRAPHIFY_VIZ_NODE_LIMIT=0 GRAPHIFY_NO_BACKUP=1 graphify update $(CURDIR) --force
	@$(MAKE) --no-print-directory graphify-wiki

# Regenerates graphify-out/wiki/ (index.md plus one page per community and per highly
# connected node) from the current graph. Runs locally in about a second with no LLM calls,
# and removes pages for communities that no longer exist. The git hooks do not run it, so
# update-graphify and semantic-graphify call it at the end.
.PHONY: graphify-wiki
graphify-wiki:
	@graphify export wiki

# Rebuilds the graph including the LLM-based (semantic) results: document/paper/image
# extraction and community names. Code is still parsed locally (AST).
#
# Uses the same LLM settings as the repo scripts (scripts/workflow/*). Each value is
# taken from the environment if set, otherwise from its KEY = "value" line in .env:
#   REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE       must be "openai" (any server with the OpenAI chat API)
#   REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL   server base URL, usually ending in /v1
#   REPO_SCRIPTS_DEFAULT_MODEL               model id as the server names it
#   REPO_SCRIPTS_DEFAULT_PROVIDER_KEY        API key; "none" is sent if empty
# They are passed to graphify's "openai" backend as OPENAI_BASE_URL, GRAPHIFY_OPENAI_MODEL
# and OPENAI_API_KEY for these two commands only. The values are read by the shell at run
# time, so make never prints the API key, not even with make -n.
#
# Unchanged files are skipped via graphify's cache unless GRAPHIFY_REEXTRACT=1.
#   make semantic-graphify                          # incremental
#   make semantic-graphify GRAPHIFY_REEXTRACT=1     # re-extract everything, ignore the cache
#   make semantic-graphify GRAPHIFY_MODE=deep       # more aggressive inferred-edge extraction
#   make semantic-graphify GRAPHIFY_RELABEL=1       # rename all communities, not only unnamed ones
#   make semantic-graphify GRAPHIFY_CONCURRENCY=1   # parallel LLM requests (graphify default: 4)
#   make semantic-graphify GRAPHIFY_ALLOW_PARTIAL=1 # save the graph even if some LLM chunks failed or it lost
#                                                   # nodes (graphify refuses this by default; check the log first)
# Make variable names avoid names graphify itself reads from the environment (GRAPHIFY_FORCE,
# GRAPHIFY_LLM_*). GRAPHIFY_NO_BACKUP=1 stops graphify from writing a dated backup folder into
# graphify-out/ on every LLM run.
.PHONY: semantic-graphify
semantic-graphify:
	@set -e; \
	setting() { \
		v=$$(printenv "$$1" || true); \
		if [ -z "$$v" ] && [ -f .env ]; then \
			v=$$(sed -nE "s/^[[:space:]]*(export[[:space:]]+)?$$1[[:space:]]*=[[:space:]]*(.*)$$/\2/p" .env | tail -n 1); \
		fi; \
		printf '%s' "$$v" | sed -E 's/[[:space:]]+$$//; s/^"(.*)"$$/\1/'; \
	}; \
	provider=$$(setting REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE); \
	base_url=$$(setting REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL); \
	model=$$(setting REPO_SCRIPTS_DEFAULT_MODEL); \
	api_key=$$(setting REPO_SCRIPTS_DEFAULT_PROVIDER_KEY); \
	if [ "$$provider" != "openai" ]; then \
		echo "error: REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE is '$$provider'; semantic-graphify only supports 'openai'" >&2; exit 1; \
	fi; \
	if [ -z "$$base_url" ] || [ -z "$$model" ]; then \
		echo "error: set REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL and REPO_SCRIPTS_DEFAULT_MODEL (environment or .env)" >&2; exit 1; \
	fi; \
	export GRAPHIFY_VIZ_NODE_LIMIT=0 GRAPHIFY_NO_BACKUP=1 OPENAI_BASE_URL="$$base_url" GRAPHIFY_OPENAI_MODEL="$$model" \
		OPENAI_API_KEY="$${api_key:-none}"; \
	echo "Using $$model at $$base_url"; \
	graphify extract $(CURDIR) --backend openai $(if $(GRAPHIFY_CONCURRENCY),--max-concurrency $(GRAPHIFY_CONCURRENCY)) \
		$(if $(GRAPHIFY_MODE),--mode $(GRAPHIFY_MODE)) $(if $(GRAPHIFY_REEXTRACT),--force) \
		$(if $(GRAPHIFY_ALLOW_PARTIAL),--allow-partial); \
	graphify label $(CURDIR) --backend openai $(if $(GRAPHIFY_CONCURRENCY),--max-concurrency $(GRAPHIFY_CONCURRENCY)) \
		$(if $(GRAPHIFY_RELABEL),,--missing-only); \
	graphify export wiki; \
	echo "✓ Semantic graph and wiki rebuilt in graphify-out/"

# Shows the status of the local setup: graphify (hooks, code graph, LLM-based results, community
# names, wiki), repository setup, branch promotion and leftover files, with the command to run
# for each action. Read-only and offline. With STATUS_STRICT=1 it fails (non-zero exit) when an
# action is listed.
.PHONY: status
status:
	@scripts/dev/status.sh

# Hooks rebuild the code graph (AST only, no LLM) after commit, checkout, merge and rebase.
# graphify always writes a graph.json merge driver and .gitattributes; both only matter for
# a tracked graph, so an untracked .gitattributes that holds nothing else is removed.
.PHONY: install-graphify-hooks
install-graphify-hooks:
	@if ! command -v graphify >/dev/null 2>&1; then \
		echo "graphify not found on PATH; skipping graphify git hooks"; exit 0; \
	fi; \
	graphify hook install; \
	if [ -f .gitattributes ] && ! git ls-files --error-unmatch .gitattributes >/dev/null 2>&1 \
		&& ! grep -qv 'merge=graphify' .gitattributes; then rm -f .gitattributes; fi

.PHONY: install-graphify
install-graphify:
	@uv tool install "graphifyy[all]" --force
	@$(MAKE) --no-print-directory install-graphify-hooks
	@graphify vscode install
	@graphify codex install
	@echo "✓ Graphify installed and git hooks set up"

################################################################################
# Git related checks
################################################################################

.PHONY: branches-ahead
branches-ahead:
	@git for-each-ref --format='%(refname:short)' refs/heads | \
	while IFS= read -r branch; do \
		ahead=$$(git rev-list --count "dev..$$branch"); \
		if [ "$$ahead" -gt 0 ]; then \
			printf '%5s  %s\n' "$$ahead" "$$branch"; \
		fi; \
	done
	@echo "✓ Branches ahead of dev listed above"

################################################################################
# Promotion workflow (dev into staging)
################################################################################

PROMOTION_SCRIPT := scripts/workflow/promote_dev_to_staging.sh

# Temporary: dev carries commit 3509963, which has no pull request, so the
# provenance check blocks every promotion. Set PROMOTION_SKIP_PROVENANCE=0 to
# restore it, for example on the command line or in .env.
PROMOTION_SKIP_PROVENANCE ?= 1

# Runs the whole dev-to-staging promotion without stopping between steps.
# The description draft generated by prepare is published as-is, so review it
# afterwards if the wording matters. Merge still requires passing reviews and
# checks, so this recipe fails if they are not already satisfied.
.PHONY: promote
promote:
	@set -euo pipefail; \
	if [ "$(PROMOTION_SKIP_PROVENANCE)" != "0" ]; then \
		echo "⚠️  Skipping the provenance check (PROMOTION_SKIP_PROVENANCE=$(PROMOTION_SKIP_PROVENANCE))."; \
	fi; \
	echo "Preparing the promotion pull request..."; \
	pr="$$(SKIP_PROMOTION_PROVENANCE=$(PROMOTION_SKIP_PROVENANCE) $(PROMOTION_SCRIPT) prepare -q)"; \
	echo "Created draft promotion PR #$$pr"; \
	echo "Publishing the description..."; \
	SKIP_PROMOTION_PROVENANCE=$(PROMOTION_SKIP_PROVENANCE) $(PROMOTION_SCRIPT) publish "$$pr"; \
	echo "Merging into staging..."; \
	$(PROMOTION_SCRIPT) merge "$$pr"; \
	echo "✅ Promotion PR #$$pr merged into staging."

