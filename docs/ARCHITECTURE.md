# SEAD Authority Service - Architecture Documentation

## Table of Contents

- [Overview](#overview)
- [High-Level Architecture](#high-level-architecture)
- [Core Design Patterns](#core-design-patterns)
- [Component Architecture](#component-architecture)
- [Request Flow](#request-flow)
- [Database Architecture](#database-architecture)
- [Configuration System](#configuration-system)
- [Strategy System](#strategy-system)
- [LLM Integration](#llm-integration)
- [MCP Server](#mcp-server)
- [Schema Generation](#schema-generation)
- [Testing Architecture](#testing-architecture)
- [Extension Points](#extension-points)
- [Performance Considerations](#performance-considerations)

## Overview

The SEAD Authority Service is a FastAPI-based reconciliation service implementing the OpenRefine Reconciliation API specification. It provides fuzzy text matching of archaeological and environmental entities against canonical database identifiers.

### Core Architectural Principles

1. **Plugin-Based Extensibility**: Strategies auto-register via decorators
2. **Lazy Configuration Resolution**: Config values resolved on-demand
3. **Singleton Database Connections**: Single connection pool for entire application
4. **Template-Based Schema Generation**: SQL schemas generated from YAML configs
5. **Strategy Pattern**: Entity-specific reconciliation logic isolated in strategies
6. **Repository Pattern**: Database queries abstracted from business logic
7. **Integrated Identity Module**: SIMS identity policy and allocation logic lives in `src/identity/`

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         OpenRefine Client                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │ HTTP
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    API Router Layer                        │ │
│  │  /reconcile  /suggest/*  /flyout/*  /preview              │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐ │
│  │              Reconciliation Orchestrator                   │ │
│  │            (reconcile.py, suggest.py, preview.py)         │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
│                             │                                    │
│  ┌──────────────────────────▼─────────────────────────────────┐ │
│  │                  Strategy Registry                         │ │
│  │         Strategies.get(entity_type) → Strategy             │ │
│  └──────────────────────────┬─────────────────────────────────┘ │
└────────────────────────────┬┴─────────────────────────────────┬─┘
                             │                                   │
          ┌──────────────────▼──────────┐    ┌─────────────────▼──────┐
          │  Entity Strategies          │    │   LLM Providers         │
          │  - SiteStrategy             │    │   - OpenAI              │
          │  - TaxonStrategy            │    │   - Anthropic           │
          │  - MethodStrategy           │    │   - Ollama              │
          │  - RAGHybridStrategy        │    └─────────┬───────────────┘
          └──────────────┬──────────────┘              │
                         │                             │
          ┌──────────────▼──────────────┐    ┌─────────▼───────────────┐
          │     Repository Layer        │    │    MCP Server           │
          │   (BaseRepository)          │    │   (Embedded Retrieval)  │
          └──────────────┬──────────────┘    └─────────────────────────┘
                         │
          ┌──────────────▼──────────────────────────────────────────┐
          │            PostgreSQL Database                          │
          │  - SEAD Schema                                          │
          │  - Authority Views (generated)                          │
          │  - Embeddings (pgvector)                                │
          │  - Trigram indexes (pg_trgm)                            │
          └─────────────────────────────────────────────────────────┘
```

## Core Design Patterns

### 1. Strategy Registry Pattern

**Purpose**: Enable dynamic strategy registration and lookup without tight coupling.

**Implementation**:

```python
# Registry metaclass in src/strategies/strategy.py
class StrategyRegistry(Registry):
    items: dict[str, type[ReconciliationStrategy]] = {}

    @classmethod
    def registered_class_hook(cls, fn_or_class: Any, **args) -> Any:
        # Hook called after registration
        if args.get("repository_cls"):
            setattr(fn_or_class, "repository_cls", args["repository_cls"])
        return fn_or_class

Strategies: StrategyRegistry = StrategyRegistry()
```

**Usage**:

```python
# Strategy classes self-register on import
@Strategies.register(key="site", repository_cls=SiteRepository)
class SiteReconciliationStrategy(ReconciliationStrategy):
    pass
```

**Key Benefits**:
- No manual strategy registration required
- Strategies discovered automatically on import
- Easy to add new entity types
- Loose coupling between registry and implementations

**Registration Flow**:
1. `main.py` imports `src.strategies` package
2. `src/strategies/__init__.py` recursively imports all submodules
3. Each strategy class decorated with `@Strategies.register()` is added to registry
4. Runtime lookup via `Strategies.get(entity_type)`

### 2. Lazy Configuration Resolution (ConfigValue)

**Purpose**: Resolve configuration values on-demand with fallback support.

**Implementation**:

```python
# src/configuration/resolve.py
@dataclass
class ConfigValue(Generic[T]):
    key: str | Type[T]
    default: T | None = None
    mandatory: bool = False
    after: Callable[[T], T] | None = None  # Post-processing

    def resolve(self, context: str | None = None, **kwargs) -> T | None:
        provider = get_config_provider()
        config = provider.get_config(context)
        
        # Support comma-separated fallback paths
        paths = [p.strip() for p in str(self.key).split(",")]
        val = config.get(*paths, default=self.default)
        
        if self.after:
            val = self.after(val)
        
        return val
```

**Usage Examples**:

```python
# Single path with default
threshold = ConfigValue("options:auto_accept_threshold", default=0.90).resolve()

# Multi-path fallback (tries each path in order)
model = ConfigValue("llm.ollama.model,llm.model", default="llama3").resolve()

# As property
@property
def auto_threshold(self):
    return ConfigValue("options:auto_accept_threshold", default=0.85).value
```

**Key Benefits**:
- Deferred resolution allows testing with mock configs
- Fallback paths enable flexible config structure
- Type-safe with generics
- Post-processing via `after` parameter

### 3. Repository Pattern

**Purpose**: Abstract database access from business logic.

**Implementation**:

```python
# src/strategies/query.py
class BaseRepository:
    def __init__(self, specification: StrategySpecification):
        self.spec = specification
    
    async def find(self, query: str, limit: int) -> list[dict]:
        """Fuzzy search by name"""
        sql = f"""
            SELECT * FROM authority.{self.spec['view_name']}
            WHERE {self.spec['label_field']} % %s
            ORDER BY similarity({self.spec['label_field']}, %s) DESC
            LIMIT %s
        """
        async with await get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, [query, query, limit])
                return [dict(row) for row in await cur.fetchall()]
    
    async def get_details(self, entity_id: str) -> dict | None:
        """Get full entity details by ID"""
        # Implementation
```

**Specialized Repositories**:

```python
# src/strategies/site.py
class SiteRepository(BaseRepository):
    async def find_with_proximity(self, query: str, lat: float, lon: float, limit: int):
        """Site-specific search with geographic proximity"""
        # Custom implementation for site entities
```

### 4. Configuration Provider Pattern

**Purpose**: Centralized configuration management with singleton lifecycle.

**Implementation**:

```python
# src/configuration/provider.py
class ConfigProvider:
    def __init__(self, config: Config):
        self._config = config
    
    def get_config(self, context: str | None = None) -> ConfigLike:
        return self._config if context is None else self._config.get(context)
    
    def is_configured(self) -> bool:
        return self._config is not None

# Singleton instance
_config_provider: ConfigProvider | None = None

def get_config_provider() -> ConfigProvider:
    global _config_provider
    if _config_provider is None:
        raise RuntimeError("Config provider not initialized")
    return _config_provider
```

**Lifecycle**:
1. Application startup: `setup_config_store()` called in `main.py`
2. Reads config files and environment variables
3. Creates database connection pool
4. Stores in singleton provider
5. Application shutdown: `shutdown_connection_pool()` closes pool

## Component Architecture

### API Layer (`src/api/`)

**File**: `router.py`

**Responsibilities**:
- HTTP endpoint definitions
- Request/response serialization
- OpenRefine API compliance
- Error handling

**Key Endpoints**:

```python
@router.get("/reconcile")  # Service metadata
@router.post("/reconcile")  # Batch reconciliation
@router.get("/suggest/entity")  # Entity autocomplete
@router.get("/suggest/type")  # Type autocomplete
@router.get("/suggest/property")  # Property autocomplete
@router.get("/flyout/entity")  # Tooltip preview
@router.get("/reconcile/preview")  # Full preview
```

### Reconciliation Orchestrator (`src/reconcile.py`)

**Purpose**: Coordinate batch reconciliation requests across multiple queries.

**Flow**:

```python
async def reconcile_queries(queries: dict[str, Any]) -> dict[str, Any]:
    results = {}
    
    for query_id, query in queries.items():
        # 1. Validate query
        entity_type = query.get("type")
        
        # 2. Get strategy from registry
        strategy_cls = Strategies.items.get(entity_type)
        strategy = strategy_cls()
        
        # 3. Find candidates
        candidate_data = await strategy.find_candidates(
            query=query.get("query"),
            properties={p["pid"]: p["v"] for p in query.get("properties", [])},
            limit=query.get("limit", 10)
        )
        
        # 4. Convert to OpenRefine format
        candidates = [strategy.as_candidate(data, query.get("query")) 
                      for data in candidate_data]
        
        results[query_id] = {"result": candidates}
    
    return results
```

### Strategy Layer (`src/strategies/`)

**Base Class**: `ReconciliationStrategy` (abstract)

**Responsibilities**:
- Entity-specific matching logic
- Candidate retrieval
- Score calculation
- Result formatting

**Key Methods**:

```python
class ReconciliationStrategy(ABC):
    async def find_candidates(self, query: str, properties: dict, limit: int) -> list[dict]:
        """Find and rank candidate matches"""
        
    def as_candidate(self, entity_data: dict, query: str) -> dict:
        """Convert entity to OpenRefine candidate format"""
        
    async def get_details(self, entity_id: str) -> dict | None:
        """Fetch full entity details"""
```

**Strategy Hierarchy**:

```
ReconciliationStrategy (abstract)
├── SiteReconciliationStrategy
│   └── Uses SiteRepository with proximity matching
├── TaxonReconciliationStrategy  
│   └── Handles taxonomic hierarchies
├── MethodReconciliationStrategy
│   └── RAGHybridReconciliationStrategy variant
├── BibliographicReferenceReconciliationStrategy
│   └── DOI and citation matching
└── LocationReconciliationStrategy
    └── Geographic filtering
```

### Repository Layer (`src/strategies/query.py`)

**Purpose**: Database query abstraction.

**Base Repository**:

```python
class BaseRepository:
    async def find(self, query: str, limit: int) -> list[dict]:
        """Fuzzy text search using pg_trgm"""
        
    async def fetch_by_alternate_identity(self, identifier: str) -> list[dict]:
        """Exact match on alternate ID (e.g., DOI, site code)"""
        
    async def get_details(self, entity_id: str) -> dict | None:
        """Fetch single entity by ID"""
```

**Specialized Repositories** extend base with entity-specific queries:

```python
class SiteRepository(BaseRepository):
    async def find_with_proximity(self, query: str, lat: float, lon: float):
        """Geographic proximity search"""
        sql = """
            SELECT *, 
                   ST_Distance(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) as distance_km
            FROM authority.view_site
            WHERE site_name % %s
            ORDER BY similarity(site_name, %s) DESC, distance_km ASC
        """
```

### Configuration System (`src/configuration/`)

**Files**:
- `config.py`: Config object and factory
- `provider.py`: Singleton provider
- `resolve.py`: ConfigValue lazy resolution
- `setup.py`: Initialization and teardown
- `interface.py`: Type definitions

**Configuration Hierarchy**:

```yaml
# config/config.yml (base)
options:
  database: {...}
  auto_accept_threshold: 0.90

policy:
  site:
    proximity_boost: {...}
    
llm:
  provider: "openai"
  openai:
    model: "${OPENAI_MODEL}"
    
table_specs: "@include entities.yml"  # File inclusion
```

**Environment Variable Substitution**:

```yaml
# ${VAR_NAME} in YAML → replaced with os.environ["VAR_NAME"]
api_key: "${OPENAI_API_KEY}"
model: "${OPENAI_MODEL:-gpt-4o-mini}"  # With default
```

### LLM Integration (`src/llm/`)

**Provider Architecture**:

```
LLMProvider (abstract base)
├── OpenAIProvider
├── AnthropicProvider
└── OllamaProvider
```

### Identity Module (`src/identity/`)

**Purpose**: SEAD Identity Management System (SIMS) — policy and allocation logic for incoming data submissions. Migrated from the retired `sead_identity_system` repository.

**Design documentation**: [docs/sims/](sims/) — REQUIREMENTS, DESIGN_VIEW, IMPLEMENTATION_VIEW, ASSESSMENT, TRACKED_ENTITIES.

**Status**: Package stub created; implementation pending.

**Planned submodules**:

| Module | Responsibility |
|--------|----------------|
| `models.py` | Domain models: `IdentityEvidence`, `AllocationResult`, `ResolutionRequest`, `IdentityRecord` |
| `policy.py` | Resolve → Allocate → Map decision logic, driven by per-entity `identity_tracking` and `reconciliation` properties |
| `registry.py` | UUID minting, evidence recording, idempotency against `identity_registry` table |

**Identity tracking values** (from `sead_standard_model.yml` in Shape Shifter):

| Value | Meaning |
|-------|---------|
| `tracked` | Aggregate root — full UUID + PK allocation per submission |
| `reconciled` | Matched against existing records by business key |
| `derived` | Identity composed from FK references (bridge entities) |
| `child` | Inherits parent aggregate identity; no independent UUID |

**Decision flow** (see [docs/sims/DESIGN_VIEW.md](sims/DESIGN_VIEW.md)):
```
Incoming entity
  → Resolve: does a match exist in identity_registry?
      → yes → return existing UUID
      → no  → Allocate: mint new UUID (tracked) or reconcile via Authority Service
                → Map: record evidence, link submission PK → UUID
```

**SQL schema**: `identity_registry` and `identity_evidence` tables are not yet defined. Do **not** place identity DDL in `schema/sql/` until the schema design is finalised.

**Provider Selection**:

```python
# src/llm/provider.py
def get_llm_provider() -> LLMProvider:
    provider_name = ConfigValue("llm.provider").resolve()
    
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "anthropic":
        return AnthropicProvider()
    elif provider_name == "ollama":
        return OllamaProvider()
```

**LLM Strategy Pattern** (`src/llm/llm_strategy.py`):

```python
class LLMReconciliationStrategy:
    async def reconcile_with_llm(
        self, 
        data: list[dict],
        lookup_data: list[dict],
        context: str
    ) -> list[dict]:
        # 1. Load prompt template
        prompt = self._build_prompt(data, lookup_data, context)
        
        # 2. Call LLM provider
        provider = get_llm_provider()
        response = await provider.complete(prompt)
        
        # 3. Parse JSON response
        results = json.loads(response)
        
        # 4. Map back to input data
        return self._map_results(results, data)
```

### Identity Module (`src/identity/`)

**Purpose**: SEAD Identity Management System (SIMS) — policy and allocation logic for incoming data submissions. Migrated from the retired `sead_identity_system` repository.

**Design documentation**: [docs/sims/](sims/) — REQUIREMENTS, DESIGN_VIEW, IMPLEMENTATION_VIEW, ASSESSMENT, TRACKED_ENTITIES.

**Status**: Package stub created; implementation pending.

**Planned submodules**:

| Module | Responsibility |
|--------|----------------|
| `models.py` | Domain models: `IdentityEvidence`, `AllocationResult`, `ResolutionRequest`, `IdentityRecord` |
| `policy.py` | Resolve → Allocate → Map decision logic, driven by per-entity `identity_tracking` and `reconciliation` properties |
| `registry.py` | UUID minting, evidence recording, idempotency against `identity_registry` table |

**Identity tracking values** (defined in `sead_standard_model.yml` in Shape Shifter):

| Value | Meaning |
|-------|---------|
| `tracked` | Aggregate root — full UUID + PK allocation per submission |
| `reconciled` | Matched against existing records by business key |
| `derived` | Identity composed from FK references (bridge entities) |
| `child` | Inherits parent aggregate identity; no independent UUID |

**Decision flow** (see [docs/sims/DESIGN_VIEW.md](sims/DESIGN_VIEW.md)):
```
Incoming entity
  → Resolve: does a match exist in identity_registry?
      → yes → return existing UUID
      → no  → Allocate: mint new UUID (tracked) or reconcile via Authority Service
                → Map: record evidence, link submission PK → UUID
```

**SQL schema**: `identity_registry` and `identity_evidence` tables are not yet defined. Do **not** place identity DDL in `schema/sql/` until the schema design is finalised.

## Request Flow

### Complete Reconciliation Flow

```
1. Client Request
   │
   ├─→ OpenRefine → POST /reconcile
   │   Content-Type: application/x-www-form-urlencoded
   │   Body: queries={"q0": {"query": "Uppsala", "type": "site", ...}}
   │
2. API Layer (router.py)
   │
   ├─→ Parse form data / JSON
   ├─→ Validate queries with Pydantic (ReconQuery model)
   ├─→ Call reconcile_queries(validated_queries)
   │
3. Orchestrator (reconcile.py)
   │
   ├─→ For each query:
   │   ├─→ Extract entity_type from query
   │   ├─→ Strategies.get(entity_type) → Strategy instance
   │   ├─→ strategy.find_candidates(query, properties, limit)
   │   │   │
   │   │   4. Strategy Layer
   │   │   │
   │   │   ├─→ Parse properties (coordinates, etc.)
   │   │   ├─→ Check alternate identity (DOI, site code)
   │   │   ├─→ Get repository instance
   │   │   ├─→ repository.find(query, limit)
   │   │   │   │
   │   │   │   5. Repository Layer
   │   │   │   │
   │   │   │   ├─→ Build SQL query (trigram search)
   │   │   │   ├─→ get_connection() → connection pool
   │   │   │   ├─→ Execute query
   │   │   │   └─→ Return list[dict]
   │   │   │
   │   │   ├─→ (Optional) LLM validation
   │   │   ├─→ (Optional) MCP server retrieval
   │   │   ├─→ Score and rank candidates
   │   │   └─→ Return candidate_data: list[dict]
   │   │
   │   └─→ strategy.as_candidate(data, query) for each result
   │       ├─→ Format as OpenRefine candidate
   │       ├─→ Calculate score percentage
   │       ├─→ Determine auto-match threshold
   │       └─→ Return formatted candidate
   │
   └─→ Collect results for all queries
   
6. Response
   │
   └─→ ReconBatchResponse(root=results)
       └─→ JSON serialization → Client
```

### Suggest/Autocomplete Flow

```
1. Client Request
   │
   └─→ GET /suggest/entity?prefix=Upp&type=site
   
2. API Layer
   │
   └─→ suggest.suggest_entities(prefix="Upp", entity_type="site")
   
3. Suggest Module (suggest.py)
   │
   ├─→ Strategies.get("site")
   ├─→ strategy.get_repository().find(prefix, limit=10)
   └─→ Format as suggest response
   
4. Response
   │
   └─→ SuggestEntityResponse(result=[...])
```

## Database Architecture

### Schema Organization

```
PostgreSQL Database
│
├── public schema (SEAD core tables)
│   ├── tbl_sites
│   ├── tbl_taxa_tree_master
│   ├── tbl_methods
│   └── ... (100+ tables)
│
├── authority schema (generated views)
│   ├── view_site
│   ├── view_taxa_tree_master
│   ├── view_method
│   └── ... (generated from templates)
│
└── Extensions
    ├── pg_trgm (trigram indexes for fuzzy search)
    ├── pgvector (embedding vectors for semantic search)
    └── PostGIS (geographic queries)
```

### Generated View Structure

Each entity has a generated view following this pattern:

```sql
-- schema/generated/site.sql (generated from template)

CREATE OR REPLACE VIEW authority.view_site AS
SELECT 
    t.site_id,                                    -- ID column
    t.site_name,                                  -- Label column
    t.site_description,                           -- Description column
    t.national_site_identifier,                   -- Alternate identity
    t.latitude_dd,                                -- Extra columns
    t.longitude_dd,
    ST_SetSRID(ST_MakePoint(
        t.longitude_dd, t.latitude_dd
    ), 4326) AS geom,
    similarity(t.site_name, '') AS name_sim       -- Trigram similarity
FROM public.tbl_sites t;

-- Trigram index for fast fuzzy search
CREATE INDEX IF NOT EXISTS idx_site_name_trgm 
ON public.tbl_sites 
USING gin (site_name gin_trgm_ops);

-- Search function
CREATE OR REPLACE FUNCTION authority.search_site(
    p_query text,
    p_limit integer DEFAULT 10
) RETURNS TABLE (...) AS $$
    SELECT * FROM authority.view_site
    WHERE site_name % p_query
    ORDER BY similarity(site_name, p_query) DESC
    LIMIT p_limit;
$$ LANGUAGE sql STABLE;
```

### Embedding Tables (Semantic Search)

For entities with `embedding_config`, additional tables are generated:

```sql
-- schema/generated/semantic-method.sql

CREATE TABLE IF NOT EXISTS authority.method_embeddings (
    method_id INTEGER PRIMARY KEY,
    embedding vector(768),
    created_at TIMESTAMP DEFAULT NOW()
);

-- IVFFlat index for fast nearest-neighbor search
CREATE INDEX IF NOT EXISTS idx_method_embeddings_ivfflat
ON authority.method_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Semantic search function
CREATE OR REPLACE FUNCTION authority.semantic_search_method(
    p_embedding vector(768),
    p_limit integer DEFAULT 10
) RETURNS TABLE (...) AS $$
    SELECT m.*, 
           1 - (e.embedding <=> p_embedding) AS similarity
    FROM authority.method_embeddings e
    JOIN authority.view_method m USING (method_id)
    ORDER BY e.embedding <=> p_embedding
    LIMIT p_limit;
$$ LANGUAGE sql STABLE;
```

### Connection Pooling

**Implementation** (`src/configuration/setup.py`):

```python
async def create_connection_pool() -> AsyncConnectionPool:
    config = get_config_provider().get_config()
    
    db_config = {
        "host": config.get("options:database:host"),
        "dbname": config.get("options:database:dbname"),
        "user": config.get("options:database:user"),
        "password": config.get("options:database:password"),
        "port": config.get("options:database:port"),
    }
    
    pool = AsyncConnectionPool(
        conninfo=" ".join(f"{k}={v}" for k, v in db_config.items()),
        min_size=config.get("options:database:pool_min_size", 2),
        max_size=config.get("options:database:pool_max_size", 10),
        timeout=config.get("options:database:pool_timeout", 30.0),
    )
    
    await pool.open()
    return pool
```

**Usage Pattern**:

```python
async with await get_connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        results = await cur.fetchall()
```

## Configuration System

### Configuration Loading Order

```
1. Base Config File (config/config.yml)
   ├─→ Read YAML
   ├─→ Process @include directives
   └─→ Load included files (entities.yml, prompts.yml)

2. Environment Variables
   ├─→ Load from .env file
   └─→ Substitute ${VAR_NAME} placeholders in config

3. Runtime Configuration
   ├─→ Create database connection pool
   ├─→ Store in config["runtime:connection_pool"]
   └─→ Additional runtime values

4. Config Provider Initialization
   └─→ Singleton provider with merged config
```

### Config Structure

```python
# Hierarchical access with colon-separated paths
config.get("options:database:host")          # → "localhost"
config.get("llm:openai:model")               # → "gpt-4o-mini"

# Multi-path fallback with comma separation
config.get("llm.ollama.model,llm.model")     # → Try first, then fallback

# Nested dictionary access
config.get("policy.site.proximity_boost")    # → {...}
```

### Entity Configuration (`config/entities.yml`)

Each entity is defined with:

```yaml
site:
  name: "Site"                                # Display name
  table_name: "tbl_sites"                     # Source table
  id_column: "site_id"                        # Primary key
  label_column: "site_name"                   # Display field
  description_column: "site_description"      # Description field
  alternate_identity_column: "national_site_identifier"  # Alternate ID
  materialized: true                          # Materialized view?
  extra_columns:                              # Additional fields
    - "t.latitude_dd"
    - "t.longitude_dd"
    - "ST_SetSRID(ST_MakePoint(t.longitude_dd, t.latitude_dd), 4326) AS geom"
  embedding_config:                           # Optional semantic search
    dimension: 768
    ivfflat_lists: 100
    analyze: false
```

## Strategy System

### Strategy Specification Resolution

Each strategy needs a specification that defines its database schema:

```python
# src/strategies/__init__.py
def resolve_specification(specification: str | dict) -> dict:
    if isinstance(specification, dict):
        return specification
    
    # Load from entity config
    entity_config = ConfigValue(f"table_specs.{specification}").resolve()
    
    return {
        "key": specification,
        "table_name": entity_config["table_name"],
        "view_name": f"view_{specification}",
        "id_field": entity_config["id_column"],
        "label_field": entity_config["label_column"],
        "description_field": entity_config.get("description_column"),
        "alternate_identity_field": entity_config.get("alternate_identity_column"),
        # ... additional fields
    }
```

### Strategy Lifecycle

```python
# 1. Strategy Class Definition
@Strategies.register(key="site", repository_cls=SiteRepository)
class SiteReconciliationStrategy(ReconciliationStrategy):
    pass

# 2. Auto-Registration on Import
# Happens when src/strategies/__init__.py imports the module

# 3. Runtime Instantiation
strategy_cls = Strategies.get("site")         # Get class from registry
strategy = strategy_cls()                     # Instantiate

# 4. Lazy Repository Creation
repository = strategy.get_repository()        # Creates on first call

# 5. Query Execution
candidates = await strategy.find_candidates(query, properties, limit)
```

### RAG Hybrid Strategy

Combines traditional fuzzy search with LLM validation:

```python
class RAGHybridReconciliationStrategy(ReconciliationStrategy):
    async def find_candidates(self, query, properties, limit):
        # Phase 1: Fuzzy retrieval (fast, broad)
        fuzzy_candidates = await self.repository.find(query, limit=30)
        
        # Phase 2: MCP server retrieval (optional)
        if self.use_mcp_server:
            mcp_candidates = await self.mcp_lookup(query, limit=10)
            candidates = self.merge_candidates(fuzzy_candidates, mcp_candidates)
        else:
            candidates = fuzzy_candidates
        
        # Phase 3: LLM validation (slow, precise)
        if len(candidates) > 0:
            validated = await self.llm_validate(query, candidates[:10])
            return validated
        
        return candidates[:limit]
```

## LLM Integration

### Provider Abstraction

```python
# src/llm/provider.py
class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        """Generate completion from prompt"""
        
    @abstractmethod
    async def chat(self, messages: list[dict], **kwargs) -> str:
        """Chat completion with message history"""
```

### OpenAI Provider Implementation

```python
class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.api_key = ConfigValue("llm.openai.api_key").resolve()
        self.model = ConfigValue("llm.openai.model").resolve()
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def complete(self, prompt: str, **kwargs) -> str:
        options = ConfigValue("llm.openai.options").resolve()
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            **{**options, **kwargs}
        )
        
        return response.choices[0].message.content
```

### Prompt Template System

Prompts stored in `config/prompts.yml` and rendered with Jinja2:

```yaml
# config/prompts.yml
reconciliation: |
  You are reconciling input values against {{ entity_type }}.
  
  Lookup data ({{ lookup_format }}):
  {{ lookup_data | safe }}
  
  Input values:
  {{ data | safe }}
  
  Return JSON with candidates...
```

```python
# src/llm/llm_strategy.py
from jinja2 import Template

def build_prompt(data, lookup_data, entity_type):
    template_str = ConfigValue("llm.prompts.reconciliation").resolve()
    template = Template(template_str)
    
    return template.render(
        entity_type=entity_type,
        lookup_format="json",
        lookup_data=json.dumps(lookup_data, indent=2),
        data=json.dumps(data, indent=2)
    )
```

## MCP Server

### Embedded MCP Architecture

The MCP (Model Context Protocol) server is embedded within the FastAPI application:

```
┌─────────────────────────────────────────────┐
│         FastAPI Application                  │
│  ┌────────────────────────────────────────┐ │
│  │   Standard Reconciliation Endpoints     │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │        MCP Server (stdio)              │ │
│  │  - search_lookup tool                  │ │
│  │  - fetch_entity resource               │ │
│  │  - Configurable retrieval strategies   │ │
│  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### MCP Server Implementation

```python
# src/mcp_server/server.py
from mcp.server.stdio import stdio_server

@mcp.tool()
async def search_lookup(entity_type: str, query: str, k: int = 10) -> list[dict]:
    """
    Retrieve top-k candidates for a query using hybrid search.
    
    Combines:
    - Trigram fuzzy matching
    - (Optional) Semantic embedding search
    - Configurable ranking
    """
    strategy = Strategies.get(entity_type)
    repository = strategy.get_repository()
    
    # Phase 1: Fuzzy search
    fuzzy_results = await repository.find(query, limit=k * 3)
    
    # Phase 2: Semantic search (if enabled)
    if has_embeddings(entity_type):
        semantic_results = await semantic_search(entity_type, query, k)
        results = merge_and_rank(fuzzy_results, semantic_results, k)
    else:
        results = fuzzy_results[:k]
    
    return results

@mcp.resource("entity://{entity_type}/{entity_id}")
async def fetch_entity(uri: str) -> dict:
    """Fetch full entity details by URI"""
    entity_type, entity_id = parse_uri(uri)
    strategy = Strategies.get(entity_type)
    return await strategy.get_details(entity_id)
```

### MCP Configuration

```yaml
# config/config.yml
mcp:
  version: "0.1.0"
  retrieval:
    k_fuzzy: 30         # Top-K from fuzzy search
    k_sem: 30           # Top-K from semantic search
    k_final: 20         # Final merged results
    min_score_threshold: 0.6
  enable_caching: true
  cache_ttl_seconds: 86400
```

## Schema Generation

### Template-Driven Generation

**Process**:

```
1. Define Entity in config/entities.yml
   └─→ Specify table, columns, indexes, etc.

2. Run make generate-schema
   └─→ Executes src/scripts/generate_entity_schema.py

3. Jinja2 Template Rendering
   ├─→ schema/templates/entity.sql.jinja2 → Trigram search
   └─→ schema/templates/semantic-entity.sql.jinja2 → Embeddings

4. Generated SQL Output
   ├─→ schema/generated/site.sql
   └─→ schema/generated/semantic-site.sql
```

### Template Structure

```jinja2
{# schema/templates/entity.sql.jinja2 #}

-- Generated view for {{ entity.name }}
CREATE OR REPLACE VIEW authority.{{ entity_key }} AS
SELECT 
    t.{{ entity.id_column }},
    t.{{ entity.label_column }},
    {% if entity.description_column %}
    t.{{ entity.description_column }},
    {% endif %}
    {% for col in entity.extra_columns %}
    {{ col }},
    {% endfor %}
    similarity(t.{{ entity.label_column }}, '') AS name_sim
FROM {{ entity.table_name }} t
{% for join in entity.joins %}
{{ join }}
{% endfor %}
{% if entity.where_clause %}
WHERE {{ entity.where_clause }}
{% endif %};

-- Trigram index
CREATE INDEX IF NOT EXISTS idx_{{ entity_key }}_{{ entity.label_column }}_trgm
ON {{ entity.table_name }}
USING gin ({{ entity.label_column }} gin_trgm_ops);

-- Search function
CREATE OR REPLACE FUNCTION authority.search_{{ entity_key }}(
    p_query text,
    p_limit integer DEFAULT 10
    {% for param in entity.filter_params %}
    , {{ param.name }} {{ param.type }} DEFAULT {{ param.default }}
    {% endfor %}
) RETURNS TABLE (
    {{ entity.id_column }} integer,
    {{ entity.label_column }} text,
    name_sim real
) AS $$
    SELECT * FROM authority.view_{{ entity_key }}
    WHERE {{ entity.label_column }} % p_query
    ORDER BY similarity({{ entity.label_column }}, p_query) DESC
    LIMIT p_limit;
$$ LANGUAGE sql STABLE;
```

### Generation Script

```python
# src/scripts/generate_entity_schema.py (simplified)

def generate_trigram_sql(entity_key, entity, env, output_dir):
    template = env.get_template("entity.sql.jinja2")
    
    context = {
        "entity_key": entity_key,
        "entity": entity,
        "trigram_config": get_trigram_config(entity)
    }
    
    sql_content = template.render(**context)
    output_file = output_dir / f"{entity_key}.sql"
    output_file.write_text(sql_content)
```

## Testing Architecture

### Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── config/                     # Test configuration
│   ├── config.yml
│   └── .env
├── test_reconcile.py          # Reconciliation tests
├── test_strategies.py         # Strategy tests
├── test_configuration.py      # Config system tests
├── test_llm.py               # LLM integration tests
└── integration/              # Integration tests
    ├── test_database.py
    └── test_mcp_server.py
```

### Mock Configuration Provider

```python
# tests/conftest.py
class ExtendedMockConfigProvider(MockConfigProvider):
    def create_connection_mock(self, **kwargs):
        """Create mock database connection"""
        connection = create_connection_mock(**kwargs)
        
        mock_pool = MagicMock()
        mock_pool.connection = MagicMock(
            side_effect=lambda: self._connection_context(connection)
        )
        
        self.get_config().update({
            "runtime:connection_pool": mock_pool
        })
    
    @asynccontextmanager
    async def _connection_context(self, connection):
        yield connection
```

### Test Fixtures

```python
@pytest.fixture
def test_config() -> Config:
    """Provide test configuration"""
    factory = ConfigFactory()
    return factory.load(
        source="./tests/config/config.yml",
        context="default",
        env_filename="./tests/.env"
    )

@pytest.fixture
def test_provider(test_config):
    """Provide mock config provider with test config"""
    provider = ExtendedMockConfigProvider(test_config)
    provider.create_connection_mock(
        fetchall=[
            {"site_id": 1, "site_name": "Uppsala", "name_sim": 0.95}
        ]
    )
    return provider
```

### Test Patterns

```python
# Unit test with mocks
async def test_reconcile_queries(test_provider):
    with patch("src.reconcile.get_config_provider", return_value=test_provider):
        results = await reconcile_queries({
            "q0": {"query": "Uppsala", "type": "site"}
        })
        
        assert "q0" in results
        assert len(results["q0"]["result"]) > 0

# Integration test (marked)
@pytest.mark.integration
async def test_database_connection():
    async with await get_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            result = await cur.fetchone()
            assert result[0] == 1
```

## Extension Points

### 1. Adding New Entity Types

**Steps**:

1. Add entity to `config/entities.yml`
2. Run `make generate-schema`
3. Deploy generated SQL to database
4. Create strategy class (optional, can use base)
5. Strategy auto-registers on import

**Minimal Strategy** (uses all defaults):

```python
# src/strategies/my_entity.py
from src.strategies.strategy import ReconciliationStrategy, Strategies
from src.strategies.query import BaseRepository

@Strategies.register(key="my_entity", repository_cls=BaseRepository)
class MyEntityReconciliationStrategy(ReconciliationStrategy):
    pass  # Inherits all default behavior
```

### 2. Custom Repository Logic

```python
class CustomRepository(BaseRepository):
    async def find(self, query: str, limit: int) -> list[dict]:
        # Custom search logic
        sql = """
            SELECT * FROM authority.view_my_entity
            WHERE custom_field ILIKE %s
            ORDER BY custom_score DESC
            LIMIT %s
        """
        async with await get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, [f"%{query}%", limit])
                return [dict(row) for row in await cur.fetchall()]

@Strategies.register(key="my_entity", repository_cls=CustomRepository)
class MyEntityStrategy(ReconciliationStrategy):
    pass
```

### 3. Custom Scoring Logic

```python
class CustomStrategy(ReconciliationStrategy):
    async def find_candidates(self, query, properties, limit):
        # Get base candidates
        candidates = await super().find_candidates(query, properties, limit * 2)
        
        # Apply custom scoring
        for candidate in candidates:
            custom_score = self.calculate_custom_score(candidate, properties)
            candidate["score"] = (candidate["score"] + custom_score) / 2
        
        # Re-sort and limit
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:limit]
    
    def calculate_custom_score(self, candidate, properties):
        # Custom scoring logic
        return 0.5
```

### 4. New LLM Provider

```python
# src/llm/providers/custom_provider.py
class CustomLLMProvider(LLMProvider):
    def __init__(self):
        self.api_endpoint = ConfigValue("llm.custom.endpoint").resolve()
        self.api_key = ConfigValue("llm.custom.api_key").resolve()
    
    async def complete(self, prompt: str, **kwargs) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_endpoint,
                json={"prompt": prompt, **kwargs},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()["completion"]
```

Register in provider factory:

```python
# src/llm/provider.py
def get_llm_provider() -> LLMProvider:
    provider_name = ConfigValue("llm.provider").resolve()
    
    if provider_name == "custom":
        return CustomLLMProvider()
    # ... existing providers
```

## Performance Considerations

### Database Query Optimization

1. **Trigram Indexes**: All label fields have GIN indexes for fast fuzzy matching
2. **Connection Pooling**: Reuses connections to avoid overhead
3. **Prepared Statements**: Queries use parameterized SQL
4. **Index-Only Scans**: Views include only necessary columns
5. **Materialized Views**: Large entity sets can be materialized

### Caching Strategies

```python
# Future: Response caching
from functools import lru_cache

@lru_cache(maxsize=1000)
def cached_reconcile(query_hash: str):
    # Cache reconciliation results
    pass

# MCP server caching
mcp:
  enable_caching: true
  cache_ttl_seconds: 86400
```

### Async/Await Throughout

All I/O operations are async:
- Database queries
- LLM API calls
- HTTP requests
- File I/O (where possible)

### Batch Processing

```python
# Process multiple queries in parallel (future enhancement)
async def reconcile_queries_parallel(queries):
    tasks = [
        reconcile_single_query(query_id, query)
        for query_id, query in queries.items()
    ]
    results = await asyncio.gather(*tasks)
    return dict(zip(queries.keys(), results))
```

## Security Considerations

1. **SQL Injection Prevention**: Parameterized queries only
2. **Environment Variable Protection**: Secrets in .env, not in code
3. **Non-root Container**: Docker runs as `appuser`
4. **Read-only Config Mount**: Configuration files mounted read-only
5. **Input Validation**: Pydantic models validate all inputs
6. **Connection Pool Limits**: Prevents resource exhaustion

---

**Document Version**: 1.0  
**Last Updated**: January 8, 2026  
**Maintainer**: HUMLAB SEAD Team
