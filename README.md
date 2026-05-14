# SEAD Authority Service

[![Docker Build](https://github.com/humlab-sead/sead_authority_service/actions/workflows/docker-build.yml/badge.svg)](https://github.com/humlab-sead/sead_authority_service/actions/workflows/docker-build.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

FastAPI service implementing the [OpenRefine Reconciliation API](https://reconciliation-api.github.io/specs/latest/) for SEAD (Strategic Environmental Archaeology Database). It resolves fuzzy text queries to canonical SEAD entity identifiers and manages stable UUIDs for incoming data submissions via the SIMS identity module.

## Features

- OpenRefine Reconciliation API — compatible with OpenRefine and any client implementing the spec
- Entity reconciliation for sites, taxa, methods, bibliographic references, and more
- Trigram fuzzy search backed by PostgreSQL `pg_trgm`
- Optional LLM-assisted candidate validation (OpenAI, Anthropic, Ollama)
- Geographic proximity matching for site reconciliation
- Embedded MCP server for retrieval-augmented (RAG hybrid) strategies
- Plugin-based strategy registry with automatic decorator-based registration
- SIMS identity module — stable UUID allocation and binding lifecycle for incoming SEAD submissions

## Quick Start

**Prerequisites:** Python 3.13+, [uv](https://docs.astral.sh/uv/), Git, PostgreSQL (SEAD schema with `pg_trgm`)

```bash
git clone https://github.com/humlab-sead/sead_authority_service.git
cd sead_authority_service
make install
cp docker/development/.env.example .env   # fill in DB credentials
make serve
```

The service is available at `http://localhost:8000`. Connect OpenRefine by adding a standard service at `http://localhost:8000/reconcile`.

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for full local setup, configuration, and workflow guidance.

## Docker

```bash
cd docker
docker-compose up --build
```

See [docker/README.md](docker/README.md) for production and staging deployment options.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/is_alive` | GET | Health check |
| `/reconcile` | GET | Service metadata |
| `/reconcile` | POST | Batch reconciliation queries |
| `/suggest/entity` | GET | Entity autocomplete |
| `/suggest/type` | GET | Type autocomplete |
| `/flyout/entity` | GET | Inline entity preview |
| `/identity/resolve` | POST | SIMS identity resolution |
| `/identity/binding-sets/{uuid}` | GET | Binding set status |
| `/identity/scopes` | GET | List source scopes |

Interactive API docs: `http://localhost:8000/docs`

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/DESIGN.md](docs/DESIGN.md) | Architecture, components, key flows, and design decisions |
| [docs/DIAGRAMS.md](docs/DIAGRAMS.md) | System diagrams — context, components, flows, state machines |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Local setup, conventions, and contributor workflow |
| [docs/TESTING.md](docs/TESTING.md) | Test strategy, levels, markers, and CI behavior |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Environments, deployment, CI/CD, rollback, and observability |
| [docs/SIMS/](docs/SIMS/) | SIMS identity module design and requirements |
| [AGENTS.md](AGENTS.md) | AI coding agent instructions and canonical patterns |
| [docker/README.md](docker/README.md) | Docker deployment guide |

## License

[MIT License](LICENSE) — HUMLAB SEAD Team, [GitHub](https://github.com/humlab-sead)


