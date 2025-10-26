/**********************************************************************************************
**  Taxa Tree Master (Species Level)
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxa_tree_master_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxa (species level)
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings are based on full taxonomic name (genus + species)
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.taxa_tree_master_embeddings CASCADE;

CREATE TABLE authority.taxa_tree_master_embeddings (
  taxon_id INTEGER PRIMARY KEY REFERENCES public.tbl_taxa_tree_master(taxon_id) ON DELETE CASCADE,
  emb      VECTOR(768) NOT NULL,
  updated  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS taxa_tree_master_embeddings_ivfflat_idx
  ON authority.taxa_tree_master_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

DROP VIEW IF EXISTS authority.taxa_tree_master;
CREATE OR REPLACE VIEW authority.taxa_tree_master AS
  SELECT  
    t.taxon_id,
    CONCAT(g.genus_name, ' ', t.species) AS label,
    t.species,
    t.genus_id,
    t.author_id,
    g.genus_name,
    a.author_name,
    authority.immutable_unaccent(lower(CONCAT(g.genus_name, ' ', t.species))) AS norm_label,
    e.emb
  FROM public.tbl_taxa_tree_master t
  LEFT JOIN public.tbl_taxa_tree_genera g USING (genus_id)
  LEFT JOIN public.tbl_taxa_tree_authors a USING (author_id)
  LEFT JOIN authority.taxa_tree_master_embeddings e USING (taxon_id);

CREATE INDEX IF NOT EXISTS tbl_taxa_tree_master_norm_trgm
  ON public.tbl_taxa_tree_master
    USING gin ( (authority.immutable_unaccent(lower(species))) gin_trgm_ops );

DROP FUNCTION IF EXISTS authority.fuzzy_taxa_tree_master(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION authority.fuzzy_taxa_tree_master(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
  taxon_id INTEGER,
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
    t.taxon_id,
    t.label,
    GREATEST(
      CASE WHEN t.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(t.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS name_sim
  FROM authority.taxa_tree_master AS t
  WHERE t.norm_label % (SELECT q FROM params)
  ORDER BY name_sim DESC, t.label
  LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_tree_master
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Searches based on full taxonomic name (genus + species)
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_taxa_tree_master(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_taxa_tree_master(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  taxon_id INTEGER,
  label    TEXT,
  sem_sim  DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  t.taxon_id,
  t.label,
  1.0 - (t.emb <=> qemb) AS sem_sim
FROM authority.taxa_tree_master AS t
WHERE t.emb IS NOT NULL
ORDER BY t.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxa_tree_master_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 **            Searches full taxonomic name (genus + species)
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_taxa_tree_master_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_taxa_tree_master_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  taxon_id INTEGER,
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
    t.taxon_id,
    t.label,
    GREATEST(
      CASE WHEN t.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(t.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.taxa_tree_master AS t
  WHERE t.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, t.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    t.taxon_id,
    t.label,
    (1.0 - (t.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.taxa_tree_master AS t
  WHERE t.emb IS NOT NULL
  ORDER BY t.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT taxon_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT taxon_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    taxon_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY taxon_id
)
SELECT
  taxon_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
