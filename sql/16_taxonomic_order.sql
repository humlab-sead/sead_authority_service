/**********************************************************************************************
**  Taxonomic Order (Code Mappings)
**********************************************************************************************/

/***************************************************************************************************
 ** Note      This table contains taxonomic codes for organizing species within hierarchies
 **           and referencing external systems (GBIF, Artdatabanken, etc.)
 **           Search is primarily by code rather than text, so embeddings have limited utility
 **           but are included for consistency with other authority tables
 ****************************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxonomic_order_embeddings
 ** What      Stores 768-dimensional embeddings for taxonomic order codes
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings based on string representation of taxonomic_code
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.taxonomic_order_embeddings CASCADE;

CREATE TABLE authority.taxonomic_order_embeddings (
  taxonomic_order_id INTEGER PRIMARY KEY REFERENCES public.tbl_taxonomic_order(taxonomic_order_id) ON DELETE CASCADE,
  emb                VECTOR(768) NOT NULL,
  updated            TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS taxonomic_order_embeddings_ivfflat_idx
  ON authority.taxonomic_order_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

DROP VIEW IF EXISTS authority.taxonomic_orders;
CREATE OR REPLACE VIEW authority.taxonomic_orders AS
  SELECT  
    to_.taxonomic_order_id,
    to_.taxonomic_code::TEXT AS label,
    to_.taxon_id,
    to_.taxonomic_code,
    to_.taxonomic_order_system_id,
    e.emb
  FROM public.tbl_taxonomic_order to_
  LEFT JOIN authority.taxonomic_order_embeddings e USING (taxonomic_order_id);

CREATE INDEX IF NOT EXISTS tbl_taxonomic_order_code_trgm
  ON public.tbl_taxonomic_order
    USING gin ( (taxonomic_code::TEXT) gin_trgm_ops );

DROP FUNCTION IF EXISTS authority.fuzzy_taxonomic_orders(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION authority.fuzzy_taxonomic_orders(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
  taxonomic_order_id INTEGER,
  label              TEXT,
  name_sim           DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
  WITH params AS (
    SELECT p_text::TEXT AS q
  )
  SELECT
    to_.taxonomic_order_id,
    to_.label,
    GREATEST(
      CASE WHEN to_.label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(to_.label, (SELECT q FROM params))
      END,
      0.0001
    ) AS name_sim
  FROM authority.taxonomic_orders AS to_
  WHERE to_.label % (SELECT q FROM params)
  ORDER BY name_sim DESC, to_.label
  LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxonomic_orders
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Limited utility for numeric codes but included for API consistency
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_taxonomic_orders(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_taxonomic_orders(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  taxonomic_order_id INTEGER,
  label              TEXT,
  sem_sim            DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  to_.taxonomic_order_id,
  to_.label,
  1.0 - (to_.emb <=> qemb) AS sem_sim
FROM authority.taxonomic_orders AS to_
WHERE to_.emb IS NOT NULL
ORDER BY to_.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxonomic_orders_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      Primarily useful for exact or near-exact code matching
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_taxonomic_orders_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_taxonomic_orders_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  taxonomic_order_id INTEGER,
  label              TEXT,
  trgm_sim           DOUBLE PRECISION,
  sem_sim            DOUBLE PRECISION,
  blend              DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT p_text::TEXT AS q
),
trgm AS (
  SELECT
    to_.taxonomic_order_id,
    to_.label,
    GREATEST(
      CASE WHEN to_.label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(to_.label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.taxonomic_orders AS to_
  WHERE to_.label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, to_.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    to_.taxonomic_order_id,
    to_.label,
    (1.0 - (to_.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.taxonomic_orders AS to_
  WHERE to_.emb IS NOT NULL
  ORDER BY to_.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT taxonomic_order_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT taxonomic_order_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    taxonomic_order_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY taxonomic_order_id
)
SELECT
  taxonomic_order_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
