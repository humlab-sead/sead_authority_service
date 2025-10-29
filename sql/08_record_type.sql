/**********************************************************************************************
**  Record Type
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.record_type_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over record types
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.record_type_embeddings CASCADE;

CREATE TABLE authority.record_type_embeddings (
  record_type_id INTEGER PRIMARY KEY REFERENCES public.tbl_record_types(record_type_id) ON DELETE CASCADE,
  emb            VECTOR(768) NOT NULL,
  updated        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS record_type_embeddings_ivfflat_idx
  ON authority.record_type_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

DROP VIEW IF EXISTS authority.record_type;
CREATE OR REPLACE VIEW authority.record_type AS
  SELECT  
    rt.record_type_id,
    rt.record_type_name AS label,
    rt.record_type_description AS description,
    authority.immutable_unaccent(lower(rt.record_type_name)) AS norm_label,
    e.emb
  FROM public.tbl_record_types rt
  LEFT JOIN authority.record_type_embeddings e USING (record_type_id);

CREATE INDEX IF NOT EXISTS tbl_record_types_norm_trgm
  ON public.tbl_record_types
    USING gin ( (authority.immutable_unaccent(lower(record_type_name))) gin_trgm_ops );

DROP FUNCTION IF EXISTS authority.fuzzy_record_type(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION authority.fuzzy_record_type(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
  record_type_id INTEGER,
  label          TEXT,
  name_sim       DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
  WITH params AS (
    SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
  )
  SELECT
    rt.record_type_id,
    rt.label,
    GREATEST(
      CASE WHEN rt.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(rt.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS name_sim
  FROM authority.record_type AS rt
  WHERE rt.norm_label % (SELECT q FROM params)
  ORDER BY name_sim DESC, rt.label
  LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_record_type
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_record_type(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_record_type(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  record_type_id INTEGER,
  label          TEXT,
  sem_sim        DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  rt.record_type_id,
  rt.label,
  1.0 - (rt.emb <=> qemb) AS sem_sim
FROM authority.record_type AS rt
WHERE rt.emb IS NOT NULL
ORDER BY rt.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_record_type_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_record_type_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_record_type_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  record_type_id INTEGER,
  label          TEXT,
  trgm_sim       DOUBLE PRECISION,
  sem_sim        DOUBLE PRECISION,
  blend          DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
trgm AS (
  SELECT
    rt.record_type_id,
    rt.label,
    GREATEST(
      CASE WHEN rt.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(rt.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.record_type AS rt
  WHERE rt.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, rt.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    rt.record_type_id,
    rt.label,
    (1.0 - (rt.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.record_type AS rt
  WHERE rt.emb IS NOT NULL
  ORDER BY rt.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT record_type_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT record_type_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    record_type_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY record_type_id
)
SELECT
  record_type_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
