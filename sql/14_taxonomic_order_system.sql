/**********************************************************************************************
**  Taxonomic Order Systems
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxonomic_order_system_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxonomic order systems
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings combine system name and description for richer semantic matching
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.taxonomic_order_system_embeddings CASCADE;

CREATE TABLE authority.taxonomic_order_system_embeddings (
  taxonomic_order_system_id INTEGER PRIMARY KEY REFERENCES public.tbl_taxonomic_order_systems(taxonomic_order_system_id) ON DELETE CASCADE,
  emb                       VECTOR(768) NOT NULL,
  updated                   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS taxonomic_order_system_embeddings_ivfflat_idx
  ON authority.taxonomic_order_system_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

DROP VIEW IF EXISTS authority.taxonomic_order_systems;
CREATE OR REPLACE VIEW authority.taxonomic_order_systems AS
  SELECT  
    tos.taxonomic_order_system_id,
    tos.system_name AS label,
    tos.system_description AS description,
    authority.immutable_unaccent(lower(tos.system_name)) AS norm_label,
    e.emb
  FROM public.tbl_taxonomic_order_systems tos
  LEFT JOIN authority.taxonomic_order_system_embeddings e USING (taxonomic_order_system_id);

CREATE INDEX IF NOT EXISTS tbl_taxonomic_order_systems_norm_trgm
  ON public.tbl_taxonomic_order_systems
    USING gin ( (authority.immutable_unaccent(lower(system_name))) gin_trgm_ops );

DROP FUNCTION IF EXISTS authority.fuzzy_taxonomic_order_systems(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION authority.fuzzy_taxonomic_order_systems(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
  taxonomic_order_system_id INTEGER,
  label                     TEXT,
  name_sim                  DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
  WITH params AS (
    SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
  )
  SELECT
    tos.taxonomic_order_system_id,
    tos.label,
    GREATEST(
      CASE WHEN tos.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(tos.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS name_sim
  FROM authority.taxonomic_order_systems AS tos
  WHERE tos.norm_label % (SELECT q FROM params)
  ORDER BY name_sim DESC, tos.label
  LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxonomic_order_systems
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_taxonomic_order_systems(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_taxonomic_order_systems(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  taxonomic_order_system_id INTEGER,
  label                     TEXT,
  sem_sim                   DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  tos.taxonomic_order_system_id,
  tos.label,
  1.0 - (tos.emb <=> qemb) AS sem_sim
FROM authority.taxonomic_order_systems AS tos
WHERE tos.emb IS NOT NULL
ORDER BY tos.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxonomic_order_systems_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_taxonomic_order_systems_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_taxonomic_order_systems_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  taxonomic_order_system_id INTEGER,
  label                     TEXT,
  trgm_sim                  DOUBLE PRECISION,
  sem_sim                   DOUBLE PRECISION,
  blend                     DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
trgm AS (
  SELECT
    tos.taxonomic_order_system_id,
    tos.label,
    GREATEST(
      CASE WHEN tos.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(tos.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.taxonomic_order_systems AS tos
  WHERE tos.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, tos.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    tos.taxonomic_order_system_id,
    tos.label,
    (1.0 - (tos.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.taxonomic_order_systems AS tos
  WHERE tos.emb IS NOT NULL
  ORDER BY tos.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT taxonomic_order_system_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT taxonomic_order_system_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    taxonomic_order_system_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY taxonomic_order_system_id
)
SELECT
  taxonomic_order_system_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
