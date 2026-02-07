# SEAD Authority Service

[![Docker Build](https://github.com/humlab-sead/sead_authority_service/actions/workflows/docker-build.yml/badge.svg)](https://github.com/humlab-sead/sead_authority_service/actions/workflows/docker-build.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

FastAPI-based reconciliation service for SEAD (Strategic Environmental Archaeology Database) implementing the **OpenRefine Reconciliation API**. This service enables fuzzy text matching of archaeological and environmental entities against canonical database identifiers.

## 🎯 Key Features

- **OpenRefine Integration**: Full implementation of the Reconciliation API specification
- **Entity Reconciliation**: Support for sites, taxa, methods, bibliographic references, and more
- **Hybrid Search**: Combines fuzzy text matching with optional semantic search
- **LLM-Enhanced Matching**: Optional LLM validation using OpenAI, Anthropic, or Ollama
- **Geographic Proximity**: Location-aware matching with distance-based scoring
- **MCP Server Support**: Embedded Model Context Protocol server for advanced retrieval
- **Auto-Registration**: Plugin-based strategy system with decorator-based registration
- **Schema Generation**: Template-based SQL schema generation for rapid entity onboarding

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Development](#development)
- [Docker Deployment](#docker-deployment)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Contributing](#contributing)

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL database with SEAD schema
- (Optional) OpenAI API key or Ollama installation

### Local Development

```bash
# Clone the repository
git clone https://github.com/humlab-sead/sead_authority_service.git
cd sead_authority_service

# Install dependencies using uv
uv venv
uv pip install -e .

# Configure environment
cp docker/.env.example .env
# Edit .env with your database credentials and API keys

# Start the service
make serve
```

The service will be available at `http://localhost:8000/reconcile`

### Docker Deployment

```bash
cd docker
cp .env.example .env
# Edit .env with your configuration
docker-compose up --build
```

See [docker/README.md](docker/README.md) for detailed deployment options.

## 🏗️ Architecture

### Registry-Based Plugin System

The core architecture uses a **strategy registry pattern** where reconciliation strategies auto-register via decorators:

```python
from src.strategies.strategy import ReconciliationStrategy, Strategies

@Strategies.register(key="site", repository_cls=SiteRepository)
class SiteReconciliationStrategy(ReconciliationStrategy):
    async def find_candidates(self, query, properties, limit):
        # Implementation
```

**Request Flow:**
```
OpenRefine → POST /reconcile → router.py
  → reconcile.py:reconcile_queries()
    → Strategies.get("site")
      → SiteReconciliationStrategy
        → SiteRepository.search()
          → PostgreSQL
```

### Key Components

- **Strategies**: Entity-specific reconciliation logic (`src/strategies/`)
- **Repositories**: Database query layer (`src/strategies/query.py`)
- **Configuration**: Lazy-loading config resolution (`src/configuration/`)
- **LLM Providers**: OpenAI, Anthropic, Ollama support (`src/llm/providers/`)
- **MCP Server**: Embedded retrieval server (`src/mcp_server/`)

## 📦 Installation

### Using UV (Recommended)

```bash
# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install
uv venv
uv pip install -e .
```

### Using pip

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## ⚙️ Configuration

Configuration is managed through YAML files and environment variables.

### Main Configuration Files

- **config/config.yml**: Base configuration (database, LLM, policies)
- **config/entities.yml**: Entity definitions (source of truth for schema generation)
- **config/prompts.yml**: LLM prompt templates
- **.env**: Environment variables (database credentials, API keys)

### Environment Variables

Required variables in `.env`:

```bash
# Database Connection
SEAD_AUTHORITY_OPTIONS_DATABASE_HOST=localhost
SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME=sead_staging
SEAD_AUTHORITY_OPTIONS_DATABASE_USER=postgres
SEAD_AUTHORITY_OPTIONS_DATABASE_PORT=5432

# LLM Provider (Optional)
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini

# GeoNames (Optional)
GEONAMES_USERNAME=your_username
```

### Configuration Resolution

Use `ConfigValue` for lazy configuration resolution:

```python
from src.configuration import ConfigValue

# Single path with fallback
threshold = ConfigValue("options:auto_accept_threshold", default=0.90).resolve()

# Multiple path fallback
model = ConfigValue("llm.ollama.model,llm.model", default="llama3").resolve()
```

## 🎮 Usage

### With OpenRefine

1. Start the service: `make serve`
2. Open OpenRefine
3. Create a project and select a column
4. Click **Reconcile** → **Start reconciling...**
5. Add Standard Service: `http://localhost:8000/reconcile`
6. Select entity type (Site, Taxon, Method, etc.)
7. Configure matching options
8. Start reconciliation

### API Endpoints

#### Health Check
```bash
curl http://localhost:8000/is_alive
```

#### Service Metadata
```bash
curl http://localhost:8000/reconcile
```

#### Reconciliation Request
```bash
curl -X POST http://localhost:8000/reconcile \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'queries={"q0":{"query":"Uppsala","type":"site","limit":10}}'
```

#### Entity Suggestions (Autocomplete)
```bash
curl "http://localhost:8000/suggest/entity?prefix=Uppsala&type=site"
```

See [API Reference](#api-reference) for complete endpoint documentation.

## 👨‍💻 Development

### Running the Service

```bash
# Development mode with auto-reload
make serve

# Start uvicorn + OpenRefine together
make dev-serve

# Stop services
make dev-stop
```

### Testing

```bash
# Run all tests
make test

# Run integration tests only
uv run pytest -m integration

# Run specific test
uv run pytest -k test_name

# Test coverage
make test-coverage
```

**Test Markers:**
- `@pytest.mark.integration`: Requires database/Ollama
- `@pytest.mark.manual`: Manual testing only
- `@pytest.mark.debug`: Debug tests

### Code Quality

```bash
# Run all linting
make lint

# Format code
make tidy

# Check imports
make check-imports
```

**Import Rules:** Use absolute imports from `src.*`. Ruff enforces `ban-relative-imports = "parents"`.

### Adding New Entities

1. Add entity configuration to [config/entities.yml](config/entities.yml)
2. Generate schema: `make generate-schema`
3. Create strategy class in `src/strategies/`
4. Register with `@Strategies.register()` decorator

Example:

```yaml
# config/entities.yml
new_entity:
  name: "New Entity"
  table_name: "tbl_new_entities"
  id_column: "entity_id"
  label_column: "entity_name"
  description_column: "description"
```

```bash
make generate-schema
```

```python
# src/strategies/new_entity.py
from src.strategies.strategy import ReconciliationStrategy, Strategies
from src.strategies.query import BaseRepository

@Strategies.register(key="new_entity", repository_cls=BaseRepository)
class NewEntityReconciliationStrategy(ReconciliationStrategy):
    pass  # Uses default implementation
```

## 🐳 Docker Deployment

Multiple deployment options supported:

### Option 1: Local Build
```bash
cd docker
docker-compose up --build
```

### Option 2: Production (GHCR)
```bash
cd docker
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
```

### Option 3: GitHub Tag Build
```bash
docker build -f docker/Dockerfile.github \
  --build-arg GIT_TAG=v0.1.0 \
  -t sead-authority-service:v0.1.0 .
```

**Available GHCR Tags:**
- `latest` - Latest stable release from main
- `dev` - Latest development version
- `v*` - Specific version tags (e.g., `v0.1.0`)

See [docker/README.md](docker/README.md) for detailed deployment guide.

## 📚 API Reference

### Reconciliation API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/reconcile` | GET | Service metadata |
| `/reconcile` | POST | Batch reconciliation queries |
| `/reconcile/properties` | GET | Available properties |
| `/reconcile/preview` | GET | Entity preview HTML |

### Suggest API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/suggest/entity` | GET | Entity autocomplete |
| `/suggest/type` | GET | Type autocomplete |
| `/suggest/property` | GET | Property autocomplete |
| `/flyout/entity` | GET/POST | Inline tooltip preview |

### Response Format

Reconciliation response:

```json
{
  "q0": {
    "result": [
      {
        "id": "https://w3id.org/sead/id/site/123",
        "name": "Uppsala Site",
        "score": 95.5,
        "match": true,
        "type": [{"id": "site", "name": "Site"}],
        "distance_km": 1.2
      }
    ]
  }
}
```

## 🧪 Testing

### Test Structure

- **tests/**: Unit and integration tests
- **tests/config/**: Test configuration files
- **tests/conftest.py**: Shared fixtures

### Running Tests

```bash
# All tests
make test

# With coverage
make test-coverage

# Specific test file
uv run pytest tests/test_reconcile.py

# Specific test function
uv run pytest -k test_reconcile_queries
```

### Test Fixtures

Key fixtures from [tests/conftest.py](tests/conftest.py):

- `test_config`: Test configuration object
- `test_provider`: Mock config provider
- `create_connection_mock()`: Mock database connections

## 🤝 Contributing

### Git Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/) with semantic-release.

**Format:**
```
<type>[optional scope]: <description>
```

**Types:**
- `feat`: New feature → MINOR release (1.2.0)
- `fix`: Bug fix → PATCH release (1.2.1)
- `refactor/perf/style`: Code improvements → PATCH
- `docs`: Documentation → PATCH (if scope is README)
- `test/build/ci/chore`: No release

**Breaking Changes:**
```bash
feat(api)!: change response format for validation errors
```

**Examples:**
```bash
feat(cache): implement hash-based cache invalidation
fix(validation): prevent null pointer in entity resolution
refactor(core): simplify dependency resolution logic
docs(README): update installation instructions
```

### Development Workflow

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make changes following code quality standards
4. Run tests: `make test`
5. Run linting: `make lint`
6. Commit with conventional commits
7. Push and create a pull request

## 📁 Project Structure

```
sead_authority_service/
├── config/                 # Configuration files
│   ├── config.yml         # Base configuration
│   ├── entities.yml       # Entity definitions
│   └── prompts.yml        # LLM prompt templates
├── docker/                # Docker deployment files
├── schema/                # Database schema
│   ├── templates/         # Jinja2 SQL templates
│   └── generated/         # Generated SQL files
├── src/
│   ├── api/              # FastAPI routes
│   ├── configuration/    # Config management
│   ├── llm/              # LLM provider integrations
│   ├── mcp_server/       # MCP server implementation
│   └── strategies/       # Reconciliation strategies
├── tests/                # Test suite
├── main.py               # FastAPI application entry point
├── Makefile              # Development commands
└── pyproject.toml        # Python package configuration
```

## 🔧 Common Gotchas

1. **Strategy not found**: Ensure strategy file is in `src/strategies/` and decorated with `@Strategies.register()`
2. **Config not available**: Call `await setup_config_store()` before accessing config
3. **Schema changes ignored**: Run `make generate-schema` after editing `config/entities.yml`
4. **Test isolation**: Use fixtures from `tests/conftest.py`
5. **Database connections**: Always use `get_connection()`, never create connections directly

## 📖 Additional Documentation

- [AGENTS.md](AGENTS.md): AI coding agent instructions
- [docker/README.md](docker/README.md): Docker deployment guide
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md): Production deployment
- [docs/OPTIMIZATION_QUICKSTART.md](docs/OPTIMIZATION_QUICKSTART.md): Performance optimization

## 📄 License

[MIT License](LICENSE)

## 👥 Authors

- **HUMLAB SEAD Team** - [GitHub](https://github.com/humlab-sead)

## 🙏 Acknowledgments

- OpenRefine reconciliation API specification
- SEAD (Strategic Environmental Archaeology Database) project
- FastAPI framework
- PostgreSQL and pgvector extension

## 📞 Support

For issues or questions:
- GitHub Issues: https://github.com/humlab-sead/sead_authority_service/issues
- Documentation: See files in `docs/` directory

---

**Built with ❤️ for archaeological and environmental research**
