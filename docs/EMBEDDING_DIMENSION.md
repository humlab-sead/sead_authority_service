# Embedding Dimension Selection for SEAD Authority Service

## Decision: 768 Dimensions

The SEAD authority service uses **768-dimensional vectors** for all embeddings. This is not an arbitrary choice but is determined by the embedding model architecture.

## Rationale

### Selected Model: nomic-embed-text

- **Output Dimensions**: 768 (fixed)
- **Provider**: Ollama (local deployment)
- **Type**: Open source, production-ready
- **Optimized For**: Retrieval and semantic search tasks
- **License**: Apache 2.0

### Why nomic-embed-text?

1. **Purpose-built for retrieval**: Specifically designed for similarity search and information retrieval
2. **Open source**: No API costs, runs locally via Ollama
3. **Production-ready**: Battle-tested, widely adopted
4. **Context length**: Supports up to 8192 tokens (sufficient for taxonomic names, site descriptions, etc.)
5. **Performance**: Excellent balance of quality and speed
6. **No vendor lock-in**: Self-hosted, no external dependencies

## Common Embedding Model Dimensions

For reference, here are common embedding models and their dimensions:

### 384 Dimensions (Small/Fast)
- **Models**: `sentence-transformers/all-MiniLM-L6-v2`, `all-MiniLM-L12-v2`
- **Pros**: 
  - Fast inference and query time
  - Smaller storage footprint (~1.5KB per embedding)
  - Good for simple similarity tasks
- **Cons**: 
  - Lower semantic richness
  - Less effective for complex/nuanced queries
- **Use Case**: High-volume, latency-critical applications with simple matching

### 768 Dimensions (Balanced) ✅ **← SEAD Choice**
- **Models**: `nomic-embed-text`, `BERT-base`, `sentence-transformers/all-mpnet-base-v2`
- **Pros**: 
  - Excellent semantic quality
  - Good performance (queries <50ms)
  - Industry-standard dimension
  - Balanced storage cost (~3KB per embedding)
- **Cons**: 
  - 2x storage vs 384-dim models
- **Use Case**: Production systems requiring high-quality semantic search with reasonable performance

### 1024-1536 Dimensions (High Quality)
- **Models**: 
  - OpenAI `text-embedding-3-small` (1024)
  - OpenAI `text-embedding-ada-002` (1536)
- **Pros**: 
  - Higher semantic quality
  - Better for complex reasoning tasks
- **Cons**: 
  - Larger storage (4KB-6KB per embedding)
  - Slower queries (~100-200ms)
  - Requires API calls (cost, latency, external dependency)
- **Use Case**: Applications where quality trumps speed/cost

### 3072+ Dimensions (Maximum Quality)
- **Models**: OpenAI `text-embedding-3-large` (3072)
- **Pros**: 
  - State-of-the-art semantic quality
  - Best for highly nuanced tasks
- **Cons**: 
  - 4x storage cost vs 768-dim (~12KB per embedding)
  - Significantly slower queries (200-500ms)
  - High API costs
  - IVFFLAT index overhead
- **Use Case**: Research, specialized applications where cost/speed are not constraints

## Storage Impact for SEAD

### Per-Embedding Storage
- **Vector data**: 768 floats × 4 bytes = **3,072 bytes (~3KB)**
- **Index overhead**: ~20-30% additional (IVFFLAT)
- **Total per embedding**: ~4KB

### Projected Storage by Entity Type

Based on current SEAD database sizes:

| Entity | Row Count | Storage (vectors only) | With Index |
|--------|-----------|------------------------|------------|
| Sites | ~2,000 | 6 MB | ~8 MB |
| Locations | ~30,000 | 90 MB | ~120 MB |
| Feature Types | ~500 | 1.5 MB | ~2 MB |
| Methods | ~300 | 900 KB | ~1.2 MB |
| Bibliographic References | ~10,000 | 30 MB | ~40 MB |
| Record Types | ~50 | 150 KB | ~200 KB |
| Data Types | ~100 | 300 KB | ~400 KB |
| Taxa Authors | 4,828 | 14.5 MB | ~19 MB |
| Taxa Orders | 57 | 171 KB | ~220 KB |
| Taxa Families | 541 | 1.6 MB | ~2.1 MB |
| Taxa Genera | 5,234 | 15.7 MB | ~20 MB |
| Taxa Master (Species) | 23,981 | 72 MB | ~94 MB |
| Taxonomic Order Systems | 3 | 9 KB | ~12 KB |
| Taxonomic Orders (Codes) | 15,309 | 46 MB | ~60 MB |
| Taxonomy Notes | 17,255 | 52 MB | ~68 MB |
| Taxa Synonyms | ~0 (future) | 0 MB | 0 MB |
| **TOTAL** | **~110,000** | **~330 MB** | **~435 MB** |

### Performance Characteristics

#### Query Performance (768-dim with IVFFLAT)
- **Semantic search (k=30)**: 20-50ms
- **Hybrid search (k_trgm=30, k_sem=30)**: 40-80ms
- **Full workflow (retrieve + LLM)**: <900ms (target p95)

#### Index Configuration
```sql
CREATE INDEX USING ivfflat (emb vector_cosine_ops) WITH (lists = 100);
```

**Index Tuning by Table Size:**
- Small tables (<10k rows): `lists = 50-100`
- Medium tables (10k-100k rows): `lists = 100-200`
- Large tables (>100k rows): `lists = 200-500`

**Trade-off:** More lists = better accuracy but slower inserts and higher memory usage.

## Alternative Models Considered

### Why Not Smaller (384-dim)?

While 384-dim models offer:
- 50% less storage
- ~30% faster queries

They sacrifice:
- Semantic richness (critical for taxonomic/scientific names)
- Nuanced similarity detection
- Recall quality in hybrid search

For SEAD's use case (scientific nomenclature reconciliation), the semantic quality of 768-dim is worth the modest storage/performance cost.

### Why Not Larger (1536+ dim)?

Larger models offer:
- Marginal quality improvements (~5-10% on benchmarks)

But require:
- 2-4x storage costs
- 2-4x slower queries
- External API dependencies (cost, latency, availability risk)
- No local/offline operation

The quality improvement doesn't justify the costs for SEAD's domain-specific use case.

## Performance Benchmarks

### nomic-embed-text (768-dim) Performance

**Retrieval Quality** (MTEB Benchmark):
- Retrieval tasks: 53.9 (average)
- Classification: 68.6
- Clustering: 43.0
- Reranking: 52.8

**Speed** (local Ollama deployment):
- Embedding generation: ~50-100 tokens/sec
- Batch processing (100 items): ~5-10 seconds
- Query latency: <10ms

**Memory Usage**:
- Model size: ~274 MB
- RAM during inference: ~500 MB
- PostgreSQL index: ~435 MB (all tables)

## Migration Considerations

If we need to change dimensions in the future:

### Upgrading to Larger Dimensions (e.g., 768 → 1536)

**Pros:**
- Better semantic quality
- More nuanced similarity

**Cons:**
- 2x storage cost
- Need to regenerate all embeddings
- Slower queries
- Potential API dependency

**Effort:** High (full re-embedding required)

### Downgrading to Smaller Dimensions (e.g., 768 → 384)

**Pros:**
- 50% less storage
- Faster queries

**Cons:**
- Loss of semantic richness
- Need to regenerate all embeddings
- Potential quality degradation

**Effort:** High (full re-embedding required)

### Dimension Flexibility with OpenAI

Note: OpenAI's `text-embedding-3-small` and `text-embedding-3-large` support dimension reduction via API parameter, but this is not applicable to nomic-embed-text which has fixed 768-dim output.

## Conclusion

**768 dimensions is the optimal choice for SEAD Authority Service:**

1. ✅ Matches nomic-embed-text output (no dimension mismatch)
2. ✅ Excellent semantic quality for scientific nomenclature
3. ✅ Reasonable storage cost (~435 MB total)
4. ✅ Fast query performance (<50ms semantic search)
5. ✅ Open source, self-hosted (no API costs/dependencies)
6. ✅ Industry-standard dimension (wide tooling support)
7. ✅ Proven in production for retrieval tasks

**No changes recommended.** Proceed with 768-dimensional vectors across all authority tables.

## References

- nomic-embed-text: https://huggingface.co/nomic-ai/nomic-embed-text-v1
- pgvector documentation: https://github.com/pgvector/pgvector
- MTEB Leaderboard: https://huggingface.co/spaces/mteb/leaderboard
- Ollama: https://ollama.ai/library/nomic-embed-text

---

**Document Version**: 1.0  
**Last Updated**: 2025-01-29  
**Decision Status**: APPROVED  
**Implementation**: sql/*.sql (all embeddings tables use VECTOR(768))
