SHELL := /bin/bash

-include .env
export

UVICORN_PORT := 8000
SEAD_TOOLS_DIR := /home/sead/sead-tools/sead_authority_service


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
	

.PHONY: dev-deploy-to-sead-tools
dev-deploy-to-sead-tools:
	@echo "Deploying docker image using local build..." \
	 && ./docker/build.sh \
	 && pushd $(SEAD_TOOLS_DIR) \
	 && sudo docker compose up -d \
	 && popd \
	 && docker logs `docker ps -q --filter "publish=$(UVICORN_PORT)"` --follow
	@echo "✅ Development environment deployed!"

.PHONY: logs-supersead
logs-supersead:
	@docker logs `docker ps -q --filter "publish=$(UVICORN_PORT)"` --follow


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

.PHONY: rtk rtk-setup rtk-status

rtk: rtk-status

rtk-setup:
	@command -v rtk >/dev/null 2>&1 || { \
		echo "RTK is not installed."; \
		echo "Install with: brew install rtk-ai/tap/rtk"; \
		exit 1; \
	}
	@rtk init --copilot
	@rtk init --codex
	@echo "✓ RTK project integrations installed"

rtk-status:
	@rtk --version
	@rtk gain

.PHONY: \
	graphify \
	graphify-setup \
	graphify-create \
	graphify-update \
	graphify-skills \
	graphify-cluster

# Update the existing knowledge graph.
graphify: graphify-update

# One-time project setup for new developers.
graphify-setup: graphify-skills
	@echo "✓ Graphify setup complete"

# Create/recreate the knowledge graph.
graphify-create:
	@echo "Creating Graphify knowledge graph..."
	@uv run graphify extract . --project --backend openai --wiki --force

# Update the existing knowledge graph.
graphify-update:
	@echo "Updating Graphify knowledge graph..."
	@uv run graphify update .
	@echo "✓ Graphify graph updated"

# Install project-local agent integrations.
graphify-skills:
	@echo "Installing Graphify agent integrations..."
	@uv run graphify install --project
	@uv run graphify install --project --platform copilot
	@uv run graphify install --project --platform codex
	@echo "✓ Graphify agent integrations installed"

graphify-cluster:
	@uv run graphify cluster-only .
	@uv run graphify export callflow-html