
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
	
lint: tidy pylint flake8
.PHONY: lint
tidy: black isort
.PHONY: tidy
black:
	@poetry run black penelope tests