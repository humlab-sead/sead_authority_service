SHELL := /bin/bash

-include .env
export

UVICORN_PORT := 8000
PODMAN_DEPLOYMENT_DIR := deployment/container


test-workflow:
	@./scripts/test-ci.sh

fetch-openrefine-manifest:
	@curl -s http://localhost:8000/reconcile

fetch-openrefine-manifest-types:
	@curl -s http://localhost:8000/reconcile | jq -r '.defaultTypes[].id'

.PHONY: generate-schema
generate-schema:
	@echo "Generating entity schema files from templates..."
	@uv run python src/scripts/generate_entity_schema.py --all
	@echo "✅ Schema generation complete!"

.PHONY: generate-schema-force
generate-schema-force:
	@echo "Regenerating all entity schema files..."
	@uv run python src/scripts/generate_entity_schema.py --all --force
	@echo "✅ Schema regeneration complete!"
	

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

# graphify comes from brew (~/.local/bin), not the project .venv.
create-graphify:
	@graphify extract . --project
	@graphify cluster-only $(HOME)/source/sead_authority_service
	@graphify export callflow-html

# GRAPHIFY_VIZ_NODE_LIMIT=0 blocks graph.html generation and removes any stale
# file (the HTML is unused). graphify reads this limit only from the
# environment, not from .graphifyrc.
update-graphify:
	@GRAPHIFY_VIZ_NODE_LIMIT=0 graphify update $(HOME)/source/sead_authority_service --force
	@git add graphify-out
	@if git diff --cached --quiet -- graphify-out; then \
		echo "No changes in graphify-out"; \
	else \
		git commit -m "chore: updated graphify graph"; \
	fi

install-graphify:
	@uv tool install "graphifyy[all]" --force
	@graphify hook install
	@graphify vscode install
	@graphify codex install
	@echo "✓ Graphify installed and pre-commit hook set up"

#	@graphify extract . --project
#	@graphify cluster-only $(HOME)/source/sead_authority_service
# 	@graphify export callflow-html

commit-graphify:
	@git add graphify-out
	@if git diff --cached --quiet -- graphify-out; then \
		echo "No changes in graphify-out"; \
	else \
		git commit -m "chore: updated graphify graph"; \
	fi

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
