SHELL := /bin/bash

serve:       
	@uv run uvicorn main:app --reload

.PHONY: install
install:
	@uv venv
	@uv pip install -e .

.PHONY: test
test:
	@echo "No tests defined"
	@exit 0

# Build and publish Python package on PyPI using uv
.PHONY: publish
publish:
	@echo "Publishing Python package to PyPI"
	uv publish
	@echo "Published Python package to PyPI"

.PHONY: black
black:
	@uv run black src tests main.py

.PHONY: pylint
pylint:
	@uv run pylint src tests main.py

.PHONY: lint
lint: tidy pylint flake8

isort:
	@uv run isort src tests main.py

.PHONY: tidy
tidy: black isort

requirements.txt: pyproject.toml
	@uv export -o requirements.txt
