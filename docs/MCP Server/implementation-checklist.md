

# SEAD Reconciliation (RAG + MCP) — Implementation Checklist

## Phase 0 — Objectives & Switch Strategy

* [ ] Define goals: small prompts, canonical IDs, SEAD cleanliness, <900 ms p95.
* [x] Decide initial rollout tables (e.g., `methods`, `modification_type`, …).
* [ ] Add feature flag to toggle **RAGHybrid** vs current **LLM** strategy.

  * **Accept:** Flag present and switchable per table/strategy via config.

---

## Phase 1 — Database Prep (authority schema)

* [x] Verify `pg_trgm` is enabled and current fuzzy functions work.
* [x] Install `pgvector` on PostgreSQL 17+.
* [x] Add `emb VECTOR(<dim>)` column in **authority** for each targeted lookup view/table.
* [x] Create IVFFLAT index on `emb` (choose sensible `lists`).
* [x] Ensure `norm_label` (unaccent+lower) exists and is indexed via trigram.

  * **Accept:** `SELECT id, label, norm_label, emb FROM authority.<entity>` returns and is index-backed.

---

## Phase 2 — Embedding Ingestion (one-time + incremental)

* [ ] Select embedding model (e.g., `nomic-embed-text` / `bge-small`); record `dim`.
* [ ] Backfill `emb` for all rows in chosen tables (batched).
* [ ] Store embedding metadata (model name, dim, timestamp) per row or side-table.
* [ ] Configure a scheduled job to re-embed changed/new rows (nightly or on demand).

  * **Accept:** Random label → query embedding → `ORDER BY emb <=> qemb` returns reasonable neighbors.

---

## Phase 3 — Hybrid Retrieval (DB layer)

* [ ] Keep existing `authority.fuzzy_*` (trigram) functions.
* [ ] Add semantic helper (e.g., `authority.semantic_methods(text, limit)`).
* [ ] Add hybrid function (e.g., `authority.search_methods_hybrid(text, k_trgm, k_sem, k_final, language?, active_only?)`) to:

  * Retrieve K from fuzzy + K from semantic,
  * UNION + de-dup by id,
  * Compute `blend` (e.g., 0.5×trgm + 0.5×sem),
  * Apply filters (language/active),
  * LIMIT to `k_final` (≈15–20).
  * **Accept:** One SQL call yields ≤20 candidates with `{id,label, scores:{trgm,sem,blend}}` sorted by `blend`.

---

## Phase 4 — (Optional) Cross-Encoder Reranker

* [ ] Decide whether reranking is needed (evaluate later—skip for first cut).
* [ ] If yes: host a small reranker (ONNX/Torch), CPU-OK.
* [ ] Define a service endpoint or tool call: `(query, [id,label]) → top-k with scores`.

  * **Accept:** On a 100–200 example gold set, R@1/MRR improves vs `blend`.

---

## Phase 5 — MCP Server (retrieval facade)

* [ ] Stand up minimal MCP server (HTTP) with read-only DB role.
* [ ] Implement tools:

  * [ ] `search_lookup(table, query, k_trgm, k_sem, k_final, language?, active_only?)`
  * [ ] `get_by_id(table, id)`
  * [ ] *(Optional)* `rerank(query, candidates, k)`
* [ ] Add auth (bearer token or mTLS), rate limits, 200–300 ms tool timeouts.
* [ ] Add structured logs per call `{table, query_hash, counts, elapsed_ms}`.

  * **Accept:** External client can call `search_lookup` and receive ≤20 candidates with raw scores.

---

## Phase 6 — FastAPI Service Changes

* [ ] Add new `RAGHybridReconciliationStrategy` alongside existing LLM strategy.
* [ ] Wire config to select strategy per entity/table (via `Strategies.register`).
* [ ] In RAG strategy:

  * [ ] Call MCP `search_lookup` (and `rerank` if enabled) instead of loading full lookup.
  * [ ] Cap final candidate list to **5–10**.
  * [ ] Render your existing prompt with **only** those candidates (id, label[, short description]).
  * [ ] Temperature 0.0; strict JSON validation (keep existing validators).
  * **Accept:** End-to-end request returns valid JSON, ≤5 candidates per input, no full-table prompts.

---

## Phase 7 — Scoring, Thresholds, and Caching

* [ ] Map `blend`/rerank scores → `[0,1]` (min-max or Platt) centrally in FastAPI.
* [ ] Set default **no-match cutoff** (e.g., 0.60); per-table overrides allowed.
* [ ] Add Redis cache for candidate sets (keyed by table|normalized_query|K|filters; TTL 24h).
* [ ] *(Optional)* Cache final LLM JSON for exact repeats.

  * **Accept:** Repeated queries show reduced latency; cutoff respected (returns `[]` below threshold).

---

## Phase 8 — Evaluation & Tuning

* [ ] Assemble a 100–200 example gold set across chosen tables.
* [ ] Create batch eval script (offline is fine) computing Recall@1/5, MRR, nDCG for:

  * trigram, semantic, **blend**, *(optional)* rerank.
* [ ] Tune K values (e.g., 30/30→20) and blend weights.
* [ ] Record chosen defaults in config.

  * **Accept:** Target KPIs met (e.g., R@5 ≥ 0.95) with acceptable latency.

---

## Phase 9 — Observability & SLOs

* [ ] Structured logging: input, candidate IDs, raw scores, final picks, token count, MCP/LLM timings.
* [ ] Metrics dashboards (p50/p95 latency per stage; cache hit rate).
* [ ] Alerts for: MCP error rate, LLM JSON parse failures, latency SLO breach.

  * **Accept:** Dashboards show separate MCP vs LLM timings; alerts fire on synthetic failures.

---

## Phase 10 — Rollout

* [ ] **Shadow mode:** run RAG path alongside current path; log both results for comparison.
* [ ] Adjust thresholds/weights based on shadow logs.
* [ ] Flip feature flag to enable RAG strategy for selected tables.
* [ ] Keep rollback switch handy.

  * **Accept:** Production traffic uses RAG for chosen tables; rollback tested.

---

## Phase 11 — Optional Enhancements

* [ ] Add MCP `rerank` tool if adopted.
* [ ] Implement OpenRefine `/suggest` and `/preview` for improved UX.
* [ ] Small LoRA (behavior only) for JSON fidelity/conciseness (retrieval unchanged).
* [ ] Language-aware defaults (per-table language filters/weights).

  * **Accept:** Enhancements deployed without changing core RAG flow.

---

### Operational Defaults (for quick reference)

* Retrieval: **K_trgm=30 + K_sem=30 → K_final=15–20**
* Final prompt: **5–10** candidates; temp=**0.0**; max_tokens ≤ **500**
* Threshold: **0.60** (tune by table)
* Latency SLO (p95): MCP ≤ **150 ms**, rerank ≤ **120 ms**, LLM ≤ **400 ms**, end-to-end ≤ **900 ms**

