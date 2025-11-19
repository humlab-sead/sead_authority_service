# Phase 1: SQL Schema Updates - COMPLETED ✅

## Overview
Phase 1 of the MCP/RAG implementation has been completed. All SEAD authority schema SQL files have been updated to support pgvector embeddings and hybrid search (trigram + semantic).

## Implementation Pattern
Each entity follows this consistent pattern:

### 1. Embeddings Side Table
```sql
CREATE TABLE authority.{entity}_embeddings (
  {entity}_id INTEGER PRIMARY KEY REFERENCES public.tbl_{entity}({entity}_id) ON DELETE CASCADE,
  emb         VECTOR(768) NOT NULL,
  updated     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS {entity}_embeddings_ivfflat_idx
  ON authority.{entity}_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);
```

### 2. Updated View/Materialized View
```sql
CREATE [MATERIALIZED] VIEW authority.{entity}s AS
  SELECT 
    e.*,
    emb.emb
  FROM public.tbl_{entity} e
  LEFT JOIN authority.{entity}_embeddings emb USING ({entity}_id);
```

### 3. Semantic Search Function
```sql
CREATE OR REPLACE FUNCTION authority.semantic_{entity}s(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  {entity}_id INTEGER,
  label       TEXT,
  sem_sim     DOUBLE PRECISION
)
-- Returns top k results by cosine similarity
```

### 4. Hybrid Search Function
```sql
CREATE OR REPLACE FUNCTION authority.search_{entity}s_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  {entity}_id INTEGER,
  label       TEXT,
  trgm_sim    DOUBLE PRECISION,
  sem_sim     DOUBLE PRECISION,
  blend       DOUBLE PRECISION
)
-- Blends trigram and semantic scores: blend = alpha * trgm + (1-alpha) * sem
```

## Completed Files

### ✅ sql/03_site.sql (Reference Implementation)
- **Status**: Complete (already existed as reference)
- **Table**: `site_embeddings` with VECTOR(768)
- **View**: `sites` materialized view with `emb` column
- **Functions**: 
  - `semantic_sites(qemb, limit)`
  - `search_sites_hybrid(text, qemb, k_trgm, k_sem, k_final, alpha)`
- **Special Features**: Materialized view, multiple indexes (name, country)

### ✅ sql/02_location.sql
- **Status**: Complete
- **Table**: `location_embeddings` with VECTOR(768), IVFFLAT index
- **View**: `locations` view with LEFT JOIN to embeddings
- **Functions**: 
  - `semantic_locations(qemb, limit)`
  - `search_locations_hybrid(text, qemb, k_trgm, k_sem, k_final, alpha, location_type_ids)`
- **Special Features**: Optional `location_type_ids` filter parameter preserved from original
- **Indexes**: Trigram index on `norm_label`

### ✅ sql/04_feature_type.sql
- **Status**: Complete
- **Table**: `feature_type_embeddings` with VECTOR(768), IVFFLAT index
- **View**: `feature_types` view with LEFT JOIN to embeddings
- **Functions**: 
  - `semantic_feature_types(qemb, limit)`
  - `search_feature_types_hybrid(text, qemb, k_trgm, k_sem, k_final, alpha)`
- **Special Features**: Simple structure, straightforward implementation
- **Indexes**: Trigram index on `norm_label`

### ✅ sql/06_method.sql
- **Status**: Complete
- **Table**: `method_embeddings` with VECTOR(768), IVFFLAT index
- **View**: `method` view with LEFT JOIN to embeddings
- **Functions**: 
  - `semantic_method(qemb, limit)`
  - `search_method_hybrid(text, qemb, k_trgm, k_sem, k_final, alpha)`
- **Special Features**: ~~Materialized~~ view, includes `description` field
- **Indexes**: Trigram index on normalized method_name

### ✅ sql/05_bibliographic_reference.sql
- **Status**: Complete
- **Table**: `bibliographic_reference_embeddings` with VECTOR(768), IVFFLAT index
- **View**: `bibliographic_references` view with LEFT JOIN to embeddings
- **Functions**: 
  - `semantic_bibliographic_references(qemb, limit)`
  - `search_bibliographic_references_hybrid(text, qemb, k_trgm, k_sem, k_final, alpha)`
- **Special Features**: Most complex entity with multiple fields (title, authors, bugs_reference)
- **Embeddings Based On**: `full_reference` field (primary citation text)
- **Existing Functions Preserved**: `fuzzy_bibliographic_references()` with multi-mode support
- **Indexes**: Multiple trigram indexes (full_reference, title, authors, bugs_reference)
- **Note**: View includes WHERE clause `full_reference IS NULL` filter

## Technical Details

### Vector Configuration
- **Dimensions**: 768 (matches nomic-embed-text model)
- **Index Type**: IVFFLAT with cosine distance (`vector_cosine_ops`)
- **Index Parameters**: `lists = 100`
- **Distance Metric**: Cosine distance (`<=>` operator)
- **Similarity Conversion**: `1.0 - (emb <=> qemb)`

### Hybrid Search Algorithm
1. **Trigram Search**: Fetch top `k_trgm` results using `similarity()` and `%` operator
2. **Semantic Search**: Fetch top `k_sem` results using cosine distance on embeddings
3. **Union**: Combine both result sets (preserving individual scores)
4. **Aggregation**: For entities appearing in both, use MAX of each score
5. **Blending**: Calculate final score: `alpha * trgm + (1-alpha) * sem`
6. **Ranking**: Order by blended score DESC, return top `k_final` results

### Default Parameters
- `k_trgm = 30`: Top 30 fuzzy matches
- `k_sem = 30`: Top 30 semantic matches
- `k_final = 20`: Final result set size
- `alpha = 0.5`: Equal weight for trigram and semantic (50/50 blend)

## Next Steps (Phase 2: Embedding Ingestion)

1. **Create Embedding Generation Script**
   - Read entities from each table
   - Call Ollama API with `nomic-embed-text` model
   - Insert 768-dimensional vectors into embeddings tables
   - Handle batch processing (avoid rate limits)

2. **Implement Refresh Logic**
   - Detect updated/new entities (compare `updated` timestamp)
   - Regenerate embeddings for changed records
   - Support incremental updates

3. **Materialized View Refresh**
   - For `sites` and `methods` (materialized views):
     ```sql
     REFRESH MATERIALIZED VIEW authority.site;
     REFRESH MATERIALIZED VIEW authority.method;
     ```

4. **Verification Queries**
   ```sql
   -- Check embedding counts
   SELECT 'sites' as entity, COUNT(*) FROM authority.site_embeddings
   UNION ALL
   SELECT 'locations', COUNT(*) FROM authority.location_embeddings
   UNION ALL
   SELECT 'feature_types', COUNT(*) FROM authority.feature_type_embeddings
   UNION ALL
   SELECT 'methods', COUNT(*) FROM authority.method_embeddings
   UNION ALL
   SELECT 'biblio', COUNT(*) FROM authority.bibliographic_reference_embeddings;
   
   -- Test semantic search
   SELECT * FROM authority.semantic_sites(
     (SELECT emb FROM authority.site_embeddings LIMIT 1),
     10
   );
   
   -- Test hybrid search (requires text + embedding)
   SELECT * FROM authority.search_sites_hybrid(
     'Uppsala',
     (SELECT emb FROM authority.site_embeddings WHERE site_id = 123),
     30, 30, 20, 0.5
   );
   ```

## Performance Considerations

### Index Tuning
- **IVFFLAT lists parameter**: Currently set to 100
- **Recommendation**: Adjust based on table size
  - Small tables (<10k rows): 100 lists
  - Medium (10k-100k): 200-500 lists
  - Large (>100k): 1000+ lists
- **Trade-off**: More lists = better accuracy, slower inserts

### Materialized Views
- `sites` and `methods` use materialized views
- **Pros**: Faster query performance (pre-computed JOIN)
- **Cons**: Must refresh after embedding updates
- **Refresh Strategy**: 
  - Manual: `REFRESH MATERIALIZED VIEW authority.site;`
  - Automatic: Create trigger or cron job
  - Concurrent: `REFRESH MATERIALIZED VIEW CONCURRENTLY` (requires UNIQUE index)

### Query Performance
- **Hybrid search complexity**: O(k_trgm + k_sem) for initial retrieval
- **Expected latency**: <50ms for k_trgm=30, k_sem=30, k_final=20
- **Bottlenecks**: 
  - Trigram search on large tables (use GIN indexes)
  - IVFFLAT index build time (background maintenance)

## Testing Checklist

### Pre-Deployment
- [ ] Run SQL files in order (01_setup → 02_location → 03_site → 04_feature_type → 05_bibliographic_reference → 06_method)
- [ ] Verify all tables created: `\dt authority.*embeddings`
- [ ] Verify all indexes created: `\di authority.*ivfflat*`
- [ ] Verify all functions created: `\df authority.semantic_*` and `\df authority.search_*_hybrid`
- [ ] Check view/MV definitions: `\d+ authority.site` (should include `emb` column)

### Post-Ingestion
- [ ] Verify embedding counts match entity counts
- [ ] Test semantic_* functions with sample embeddings
- [ ] Test hybrid search with text + embeddings
- [ ] Benchmark query performance (target <100ms p95)
- [ ] Check index usage: `EXPLAIN ANALYZE SELECT * FROM authority.semantic_sites(...)`

## Known Issues & Notes

1. **bibliographic_references View Filter**: 
   - Contains `WHERE full_reference IS NULL` clause
   - **Action Required**: Verify this is intentional or should be `IS NOT NULL`

2. **Materialized View Refresh**:
   - `sites` and `methods` require explicit refresh after embedding updates
   - Consider implementing `REFRESH MATERIALIZED VIEW CONCURRENTLY` for zero-downtime updates

3. **Empty Embeddings**:
   - LEFT JOIN means `emb` column can be NULL
   - Semantic and hybrid functions filter `WHERE emb IS NOT NULL`
   - Entities without embeddings only appear in trigram results

4. **Alpha Parameter Tuning**:
   - Default alpha=0.5 (50/50 blend)
   - **Recommendation**: Tune based on evaluation metrics
   - Higher alpha → favor fuzzy matching
   - Lower alpha → favor semantic similarity

## References

- **Architecture Document**: `docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md`
- **Reference Implementation**: `sql/03_site.sql`
- **pgvector Documentation**: https://github.com/pgvector/pgvector
- **PostgreSQL Trigram**: https://www.postgresql.org/docs/current/pgtrgm.html

---

**Completed**: 2025-01-29  
**Phase**: 1 of 8 (SQL Schema Updates)  
**Next Phase**: 2 (Embedding Ingestion)
