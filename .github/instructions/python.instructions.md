---
description: "Use when editing Python code in src, backend, ingesters, or tests. Covers API/Core boundaries, dependency injection, validators, loaders, and test patterns."
applyTo: "src/**/*"
---
# Python Architecture

- Use absolute imports only: `from src....
- Keep API models in `src/api/model.py`.
- Prefer constructor injection or factory functions to break circular dependencies; use `TYPE_CHECKING` for type-only imports.
- Write docstrings using concrete behavior-first wording. Say what the function reads, returns, uses, or does not do. Prefer wording like `Reads sample rows from a CSV file.` and `Returns validation errors for missing required fields.` Avoid vague wording like `Ingests artifacts across the import boundary.`
