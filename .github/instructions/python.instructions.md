---
description: "Use when editing Python code in src, backend, ingesters, or tests. Covers API/Core boundaries, dependency injection, validators, loaders, and test patterns."
applyTo: "src/**/*"
---
# Python Architecture

- Use absolute imports only: `from src....
- Keep API models in `src/api/model.py`.
- Prefer constructor injection or factory functions to break circular dependencies; use `TYPE_CHECKING` for type-only imports.
