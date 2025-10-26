/**********************************************************************************************
**  Taxa Tree Orders
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxa_tree_order_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxonomic orders
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.taxa_tree_order_embeddings CASCADE;

CREATE TABLE authority.taxa_tree_order_embeddings (
  order_id INTEGER PRIMARY KEY REFERENCES public.tbl_taxa_tree_orders(order_id) ON DELETE CASCADE,
  emb      VECTOR(768) NOT NULL,
  updated  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS taxa_tree_order_embeddings_ivfflat_idx
  ON authority.taxa_tree_order_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

DROP VIEW IF EXISTS authority.taxa_tree_orders;
CREATE OR REPLACE VIEW authority.taxa_tree_orders AS
  SELECT  
    o.order_id,
    o.order_name AS label,
    o.record_type_id,
    o.sort_order,
    authority.immutable_unaccent(lower(o.order_name)) AS norm_label,
    e.emb
  FROM public.tbl_taxa_tree_orders o
  LEFT JOIN authority.taxa_tree_order_embeddings e USING (order_id);

CREATE INDEX IF NOT EXISTS tbl_taxa_tree_orders_norm_trgm
  ON public.tbl_taxa_tree_orders
    USING gin ( (authority.immutable_unaccent(lower(order_name))) gin_trgm_ops );

DROP FUNCTION IF EXISTS authority.fuzzy_taxa_tree_orders(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION authority.fuzzy_taxa_tree_orders(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
  order_id INTEGER,
  label    TEXT,
  name_sim DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
  WITH params AS (
    SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
  )
  SELECT
    o.order_id,
    o.label,
    GREATEST(
      CASE WHEN o.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(o.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS name_sim
  FROM authority.taxa_tree_orders AS o
  WHERE o.norm_label % (SELECT q FROM params)
  ORDER BY name_sim DESC, o.label
  LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_tree_orders
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_taxa_tree_orders(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_taxa_tree_orders(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  order_id INTEGER,
  label    TEXT,
  sem_sim  DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  o.order_id,
  o.label,
  1.0 - (o.emb <=> qemb) AS sem_sim
FROM authority.taxa_tree_orders AS o
WHERE o.emb IS NOT NULL
ORDER BY o.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxa_tree_orders_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_taxa_tree_orders_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_taxa_tree_orders_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  order_id INTEGER,
  label    TEXT,
  trgm_sim DOUBLE PRECISION,
  sem_sim  DOUBLE PRECISION,
  blend    DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
trgm AS (
  SELECT
    o.order_id,
    o.label,
    GREATEST(
      CASE WHEN o.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(o.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.taxa_tree_orders AS o
  WHERE o.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, o.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    o.order_id,
    o.label,
    (1.0 - (o.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.taxa_tree_orders AS o
  WHERE o.emb IS NOT NULL
  ORDER BY o.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT order_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT order_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    order_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY order_id
)
SELECT
  order_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
