#!/bin/bash
# Local CI test script - mimics GitHub Actions workflow
set -e

echo "🧪 Running CI tests locally..."
echo ""

echo "📦 Installing dependencies..."
uv sync --dev
echo "✅ Dependencies installed"
echo ""

echo "🧪 Running tests..."
uv run pytest --verbose
echo "✅ Tests passed"
echo ""

echo "🔍 Running linter..."
uv run ruff check --fix src/ tests/
echo "✅ Linting passed"
echo ""

echo "🎉 All CI checks passed!"
