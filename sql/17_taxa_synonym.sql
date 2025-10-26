/**********************************************************************************************
**  Taxa Synonyms
**********************************************************************************************/

/***************************************************************************************************
 ** Note      Contains alternative scientific names for taxa, along with references
 **           Table is currently empty but structure is ready for future data
 ****************************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxa_synonym_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxa synonyms
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings based on synonym text field
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.taxa_synonym_embeddings CASCADE;

CREATE TABLE authority.taxa_synonym_embeddings (
  synonym_id INTEGER PRIMARY KEY REFERENCES public.tbl_taxa_synonyms(synonym_id) ON DELETE CASCADE,
  emb        VECTOR(768) NOT NULL,
  updated    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS taxa_synonym_embeddings_ivfflat_idx
  ON authority.taxa_synonym_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

DROP VIEW IF EXISTS authority.taxa_synonyms;
CREATE OR REPLACE VIEW authority.taxa_synonyms AS
  SELECT  
    ts.synonym_id,
    ts.synonym AS label,
    ts.taxon_id,
    ts.family_id,
    ts.genus_id,
    ts.author_id,
    ts.biblio_id,
    ts.reference_type,
    ts.notes,
    authority.immutable_unaccent(lower(ts.synonym)) AS norm_label,
    e.emb
  FROM public.tbl_taxa_synonyms ts
  LEFT JOIN authority.taxa_synonym_embeddings e USING (synonym_id);

CREATE INDEX IF NOT EXISTS tbl_taxa_synonyms_norm_trgm
  ON public.tbl_taxa_synonyms
    USING gin ( (authority.immutable_unaccent(lower(synonym))) gin_trgm_ops );

DROP FUNCTION IF EXISTS authority.fuzzy_taxa_synonyms(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION authority.fuzzy_taxa_synonyms(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
  synonym_id INTEGER,
  label      TEXT,
  name_sim   DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
  WITH params AS (
    SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
  )
  SELECT
    ts.synonym_id,
    ts.label,
    GREATEST(
      CASE WHEN ts.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(ts.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS name_sim
  FROM authority.taxa_synonyms AS ts
  WHERE ts.norm_label % (SELECT q FROM params)
  ORDER BY name_sim DESC, ts.label
  LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_synonyms
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Useful for finding alternative names for taxa across different naming systems
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_taxa_synonyms(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_taxa_synonyms(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  synonym_id INTEGER,
  label      TEXT,
  sem_sim    DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  ts.synonym_id,
  ts.label,
  1.0 - (ts.emb <=> qemb) AS sem_sim
FROM authority.taxa_synonyms AS ts
WHERE ts.emb IS NOT NULL
ORDER BY ts.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxa_synonyms_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 **            Particularly useful for historical or alternative taxonomic nomenclature
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_taxa_synonyms_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_taxa_synonyms_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  synonym_id INTEGER,
  label      TEXT,
  trgm_sim   DOUBLE PRECISION,
  sem_sim    DOUBLE PRECISION,
  blend      DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
trgm AS (
  SELECT
    ts.synonym_id,
    ts.label,
    GREATEST(
      CASE WHEN ts.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(ts.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.taxa_synonyms AS ts
  WHERE ts.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, ts.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    ts.synonym_id,
    ts.label,
    (1.0 - (ts.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.taxa_synonyms AS ts
  WHERE ts.emb IS NOT NULL
  ORDER BY ts.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT synonym_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT synonym_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    synonym_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY synonym_id
)
SELECT
  synonym_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
