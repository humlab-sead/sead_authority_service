# SEAD MCP Server - Embedded Implementation

An embedded Model Context Protocol (MCP) server for SEAD reconciliation that provides a clean, standardized interface for hybrid retrieval over PostgreSQL.

## Overview

This MCP implementation runs **in-process** with the FastAPI reconciliation service, providing:

- **Standard MCP protocol** - Clean tool/resource interface
- **Hybrid retrieval** - Trigram (fuzzy) + Semantic (pgvector) search
- **Small prompts** - Only 5-10 candidates sent to LLM
- **Auditability** - Structured logs of all retrieval operations
- **Feature flags** - Easy rollout and rollback

## Architecture

```
FastAPI
   ↓
RAGHybridReconciliationStrategy
   ↓
SEADMCPServer (in-process)
   ↓
PostgreSQL (authority schema)
```

## Module Structure

```
src/
├── mcp/  
    ├── __init__.py                  # Public API exports
    ├── server.py                    # SEADMCPServer main facade
    ├── tools.py                     # Core retrieval tools (search_lookup, get_by_id)
    ├── resources.py                 # Metadata resources (lookup_tables, server_info)
    ├── models.py                    # Pydantic data models
    └── config.py                    # Configuration classes
...
├── strategies/                      # RAG hybrid reconciliation strategies
    └── rag_hybrid/
        ├── rag_hybrid_strategy.py   # RAG hybrid strategy base class
        ├── method.py                # RAG hybrid strategy method class
        ├── ...                      # RAG hybrid strategy xyz class
        ├── ...                      # RAG hybrid strategy xyz class
        └── ...
```

## Usage

### Basic Example

```python
from src.mcp import SEADMCPServer, SearchLookupParams
from src.configuration import get_connection

# Get database connection
async with await get_connection() as conn:
    # Initialize MCP server
    server = SEADMCPServer(conn, version="0.1.0")
    
    # Search for candidates
    result = await server.search_lookup(
        SearchLookupParams(
            table="methods",
            query="radiocarbon dating",
            k_final=10,
            active_only=True
        )
    )
    
    # Use candidates
    for candidate in result["candidates"]:
        print(f"{candidate['id']}: {candidate['value']} (score: {candidate['raw_scores']['blend']})")
```

### In a Reconciliation Strategy

```python
from src.mcp import SEADMCPServer, SearchLookupParams
from src.strategies.strategy import ReconciliationStrategy

class MethodsRAGStrategy(ReconciliationStrategy):
    async def find_candidates(self, query: str, properties=None, limit=10):
        async with await get_connection() as conn:
            mcp = SEADMCPServer(conn)
            
            result = await mcp.search_lookup(
                SearchLookupParams(
                    table="methods",
                    query=query,
                    k_final=limit
                )
            )
            
            return [
                {
                    "method_id": c["id"],
                    "method_name": c["value"],
                    "score": c["raw_scores"]["blend"]
                }
                for c in result["candidates"]
            ]
```

## Configuration

Add to your `config.yml`:

```yaml
features:
  use_mcp_server: false  # Feature flag (start disabled)

mcp:
  version: "0.1.0"
  retrieval:
    k_fuzzy: 30        # Top-K from trigram search
    k_sem: 30          # Top-K from semantic search (Phase 3)
    k_final: 20        # Final candidate count
    min_score_threshold: 0.6  # Minimum score to return
  enable_caching: true
  cache_ttl_seconds: 86400
```

## MCP Tools

### `search_lookup`
Hybrid retrieval combining trigram and semantic search.

**Input:**
```python
SearchLookupParams(
    table="methods",
    query="radiocarbon dating",
    k_fuzzy=30,      # Top-K from fuzzy
    k_sem=30,        # Top-K from semantic (Phase 3)
    k_final=20,      # Union size
    active_only=True
)
```

**Output:**
```python
{
    "table": "methods",
    "query": "radiocarbon dating",
    "candidates": [
        {
            "id": "123",
            "value": "Radiocarbon dating",
            "raw_scores": {
                "trgm": 0.95,
                "sem": 0.88,
                "blend": 0.915
            }
        }
    ],
    "elapsed_ms": 47.2
}
```

### `get_by_id`
Fetch single entry by canonical ID.

### `list_lookup_tables`
Browse available tables and metadata.

## Implementation Phases

### ✅ Phase 0: Setup (Current)
- [x] Module structure created
- [x] Basic models and server facade
- [x] Feature flag support

### 🔄 Phase 1: Database Prep (In Progress)
- [x] `pg_trgm` enabled and tested
- [ ] `pgvector` installed
- [ ] `emb` columns added to authority tables
- [ ] IVFFLAT indexes created

### 📋 Phase 2: Embedding Ingestion
- [ ] Select embedding model (`nomic-embed-text`)
- [ ] Backfill embeddings
- [ ] Scheduled re-embedding job

### 📋 Phase 3: Hybrid Retrieval
- [ ] Implement `authority.search_*_hybrid()` SQL functions
- [ ] Update `MCPTools._fallback_fuzzy_search()` → hybrid
- [ ] Tune blend weights (0.5/0.5 default)

### 📋 Phase 4: Optional Reranking
- [ ] Deploy cross-encoder reranker
- [ ] Implement `MCPTools.rerank()`

### 📋 Phase 5: LLM Integration
- [ ] Update strategies to use MCP
- [ ] Small prompt templates (5-10 candidates only)
- [ ] Strict JSON validation

### 📋 Phase 6: Rollout
- [ ] Shadow mode testing
- [ ] Feature flag rollout
- [ ] Monitor KPIs (Recall@5, latency)

## Testing

```bash
# Run MCP tests
pytest tests/test_mcp.py -v

# Test with specific table
pytest tests/test_mcp.py::test_search_methods -v
```

## Performance Targets (Phase 5 SLOs)

- **MCP search_lookup**: ≤ 150ms (p95)
- **Rerank** (optional): ≤ 120ms (p95)
- **End-to-end**: ≤ 900ms (p95)
- **Quality**: Recall@5 ≥ 0.95

## Observability

All MCP operations are logged with structured context:

```json
{
  "tool": "search_lookup",
  "table": "methods",
  "query_hash": "abc123",
  "k_final": 20,
  "candidate_count": 15,
  "elapsed_ms": 47.2,
  "top_score": 0.92
}
```

## Future Enhancements

- **Multi-KB search**: Query multiple authority sources
- **Curation tools**: Write-enabled MCP for alias management
- **Language packs**: Per-language weights and filters
- **LoRA fine-tuning**: Improve JSON fidelity (retrieval unchanged)

## References

- [Architecture Doc](../MCP%20Server/SEAD%20Reconciliation%20via%20MCP%20—%20Architecture%20Doc%20(Outline).md)
- [Implementation Checklist](../MCP%20Server/implementation-checklist.md)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)

## Contact

- Owner: HUMlab SEAD Team
- Lead: @roger.mahler
