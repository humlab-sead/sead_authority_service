# MCP Embedded Server - Quick Start Guide

## Getting Started (5 Minutes)

### 1. Enable the Feature Flag

Add to your `config/config.yml`:

```yaml
features:
  use_mcp_server: false  # Start disabled, flip to true when ready

mcp:
  retrieval:
    k_fuzzy: 30
    k_sem: 30
    k_final: 20
    min_score_threshold: 0.6
```

### 2. Test the MCP Server

```bash
# Run MCP tests
pytest tests/test_mcp.py -vdata

# Run integration test (requires database)
pytest tests/test_mcp.py::test_search_lookup_integration -v -m integration
```

### 3. Try It in Python REPL

```python
import asyncio
from src.mcp import SEADMCPServer, SearchLookupParams
from src.configuration import get_connection

async def test_mcp():
    async with await get_connection() as conn:
        server = SEADMCPServer(conn)
        
        # Get server info
        info = await server.get_server_info()
        print(f"MCP Server v{info.version}")
        print(f"Features: {info.features}")
        
        # List available tables
        tables = await server.list_lookup_tables()
        print(f"\nAvailable tables: {[t['table'] for t in tables]}")
        
        # Search for candidates
        result = await server.search_lookup(
            SearchLookupParams(
                table="methods",
                query="radiocarbon",
                k_final=5
            )
        )
        
        print(f"\nSearch results for 'radiocarbon':")
        for c in result["candidates"]:
            score = c.get("raw_scores", {}).get("blend", 0)
            print(f"  - {c['value']} (score: {score:.3f})")

# Run it
asyncio.run(test_mcp())
```

### 4. Integrate into a Strategy

Create or modify a reconciliation strategy:

```python
# src/strategies/methods.py (example)

from src.mcp.rag_hybrid_strategy import RAGHybridReconciliationStrategy
from src.strategies.strategy import Strategies

METHODS_SPECIFICATION = {
    "key": "methods",
    "display_name": "Methods",
    "id_field": "method_id",
    "label_field": "method_name",
    # ... rest of specification
}

@Strategies.register(key="methods")
class MethodsReconciliationStrategy(RAGHybridReconciliationStrategy):
    def __init__(self):
        from .query import MethodsQueryProxy
        super().__init__(METHODS_SPECIFICATION, MethodsQueryProxy)
```

### 5. Enable and Test via OpenRefine

1. Set feature flag: `features.use_mcp_server: true`
2. Restart your FastAPI service
3. In OpenRefine, reconcile a column against "Methods"
4. Check logs for MCP activity:

```bash
tail -f logs/app.log | grep "MCP"
```

You should see:
```
SEAD MCP Server initialized (v0.1.0)
MCP search returned 5 candidates for 'radiocarbon' (threshold=0.6)
```

## What's Working Now (Phase 1)

✅ **MCP Server** - Initialized and callable
✅ **Fallback Search** - Uses existing `authority.fuzzy_*()` functions
✅ **Feature Flag** - Easy enable/disable
✅ **Structured Logs** - All retrieval operations logged
✅ **Models & Validation** - Pydantic models for type safety

## What's Coming Next

### Phase 2: Embedding Ingestion
```sql
-- Add embedding column
ALTER TABLE tbl_methods ADD COLUMN emb VECTOR(768);

-- Create index
CREATE INDEX idx_methods_emb ON tbl_methods 
USING ivfflat (emb vector_cosine_ops) 
WITH (lists = 100);
```

### Phase 3: Hybrid Search
```sql
-- Create hybrid function
CREATE OR REPLACE FUNCTION authority.search_methods_hybrid(
    query_text TEXT,
    k_fuzzy INT DEFAULT 30,
    k_sem INT DEFAULT 30,
    k_final INT DEFAULT 20
) RETURNS TABLE (...) AS $$
    -- Combine fuzzy + semantic + blend scores
$$ LANGUAGE plpgsql;
```

Update `MCPTools._fallback_fuzzy_search()` to call the hybrid function.

### Phase 4: Optional Reranking
Deploy a cross-encoder reranker and implement `MCPTools.rerank()`.

## Troubleshooting

### Feature flag not working
Check that your config is being loaded:
```python
from src.configuration import ConfigValue
print(ConfigValue("features.use_mcp_server").resolve())
```

### "Unsupported table" error
Add your table to `MCPTools.allowed_tables`:
```python
self.allowed_tables = {
    "methods": "tbl_methods",
    "your_table": "tbl_your_table",  # Add here
}
```

### No candidates returned
Check the score threshold:
```yaml
mcp:
  retrieval:
    min_score_threshold: 0.3  # Lower threshold for testing
```

### Connection errors
Verify database connection:
```python
from src.configuration import get_connection
async with await get_connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute("SELECT version()")
        print(await cur.fetchone())
```

## Next Steps

1. **Run tests**: `pytest tests/test_mcp.py -v`
2. **Check Phase 1**: Review [implementation-checklist.md](../../docs/MCP%20Server/implementation-checklist.md)
3. **Prepare Phase 2**: Install `pgvector` and plan embedding ingestion
4. **Monitor**: Watch logs and metrics when feature flag is enabled

## Resources

- [MCP Module README](README.md)
- [Architecture Doc](../../docs/MCP%20Server/SEAD%20Reconciliation%20via%20MCP%20—%20Architecture%20Doc%20(Outline).md)
- [Implementation Checklist](../../docs/MCP%20Server/implementation-checklist.md)
