/**********************************************************************************************
**  Taxa Tree Genera
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxa_tree_genus_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxonomic genera
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.taxa_tree_genus_embeddings CASCADE;

CREATE TABLE authority.taxa_tree_genus_embeddings (
  genus_id INTEGER PRIMARY KEY REFERENCES public.tbl_taxa_tree_genera(genus_id) ON DELETE CASCADE,
  emb      VECTOR(768) NOT NULL,
  updated  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS taxa_tree_genus_embeddings_ivfflat_idx
  ON authority.taxa_tree_genus_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

DROP VIEW IF EXISTS authority.taxa_tree_genera;
CREATE OR REPLACE VIEW authority.taxa_tree_genera AS
  SELECT  
    g.genus_id,
    g.genus_name AS label,
    g.family_id,
    authority.immutable_unaccent(lower(g.genus_name)) AS norm_label,
    e.emb
  FROM public.tbl_taxa_tree_genera g
  LEFT JOIN authority.taxa_tree_genus_embeddings e USING (genus_id);

CREATE INDEX IF NOT EXISTS tbl_taxa_tree_genera_norm_trgm
  ON public.tbl_taxa_tree_genera
    USING gin ( (authority.immutable_unaccent(lower(genus_name))) gin_trgm_ops );

DROP FUNCTION IF EXISTS authority.fuzzy_taxa_tree_genera(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION authority.fuzzy_taxa_tree_genera(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
  genus_id INTEGER,
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
    g.genus_id,
    g.label,
    GREATEST(
      CASE WHEN g.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(g.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS name_sim
  FROM authority.taxa_tree_genera AS g
  WHERE g.norm_label % (SELECT q FROM params)
  ORDER BY name_sim DESC, g.label
  LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_tree_genera
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_taxa_tree_genera(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_taxa_tree_genera(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  genus_id INTEGER,
  label    TEXT,
  sem_sim  DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  g.genus_id,
  g.label,
  1.0 - (g.emb <=> qemb) AS sem_sim
FROM authority.taxa_tree_genera AS g
WHERE g.emb IS NOT NULL
ORDER BY g.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxa_tree_genera_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_taxa_tree_genera_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_taxa_tree_genera_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  genus_id INTEGER,
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
    g.genus_id,
    g.label,
    GREATEST(
      CASE WHEN g.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(g.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.taxa_tree_genera AS g
  WHERE g.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, g.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    g.genus_id,
    g.label,
    (1.0 - (g.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.taxa_tree_genera AS g
  WHERE g.emb IS NOT NULL
  ORDER BY g.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT genus_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT genus_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    genus_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY genus_id
)
SELECT
  genus_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
