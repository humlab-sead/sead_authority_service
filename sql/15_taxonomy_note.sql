/**********************************************************************************************
**  Taxonomy Notes
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxonomy_note_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxonomy notes
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings are based on taxonomy_notes text field (identification issues, references)
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.taxonomy_note_embeddings CASCADE;

CREATE TABLE authority.taxonomy_note_embeddings (
  taxonomy_notes_id INTEGER PRIMARY KEY REFERENCES public.tbl_taxonomy_notes(taxonomy_notes_id) ON DELETE CASCADE,
  emb               VECTOR(768) NOT NULL,
  updated           TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS taxonomy_note_embeddings_ivfflat_idx
  ON authority.taxonomy_note_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

DROP VIEW IF EXISTS authority.taxonomy_notes;
CREATE OR REPLACE VIEW authority.taxonomy_notes AS
  SELECT  
    tn.taxonomy_notes_id,
    tn.taxonomy_notes AS label,
    tn.taxon_id,
    tn.biblio_id,
    authority.immutable_unaccent(lower(tn.taxonomy_notes)) AS norm_label,
    e.emb
  FROM public.tbl_taxonomy_notes tn
  LEFT JOIN authority.taxonomy_note_embeddings e USING (taxonomy_notes_id);

CREATE INDEX IF NOT EXISTS tbl_taxonomy_notes_norm_trgm
  ON public.tbl_taxonomy_notes
    USING gin ( (authority.immutable_unaccent(lower(taxonomy_notes))) gin_trgm_ops );

DROP FUNCTION IF EXISTS authority.fuzzy_taxonomy_notes(TEXT, INTEGER);
CREATE OR REPLACE FUNCTION authority.fuzzy_taxonomy_notes(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
) RETURNS TABLE (
  taxonomy_notes_id INTEGER,
  label             TEXT,
  name_sim          DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
  WITH params AS (
    SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
  )
  SELECT
    tn.taxonomy_notes_id,
    tn.label,
    GREATEST(
      CASE WHEN tn.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(tn.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS name_sim
  FROM authority.taxonomy_notes AS tn
  WHERE tn.norm_label % (SELECT q FROM params)
  ORDER BY name_sim DESC, tn.label
  LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxonomy_notes
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Particularly useful for finding notes about identification issues or similar taxa
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_taxonomy_notes(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_taxonomy_notes(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  taxonomy_notes_id INTEGER,
  label             TEXT,
  sem_sim           DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  tn.taxonomy_notes_id,
  tn.label,
  1.0 - (tn.emb <=> qemb) AS sem_sim
FROM authority.taxonomy_notes AS tn
WHERE tn.emb IS NOT NULL
ORDER BY tn.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxonomy_notes_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 **            Useful for finding similar identification issues or taxonomic confusion
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_taxonomy_notes_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_taxonomy_notes_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  taxonomy_notes_id INTEGER,
  label             TEXT,
  trgm_sim          DOUBLE PRECISION,
  sem_sim           DOUBLE PRECISION,
  blend             DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
trgm AS (
  SELECT
    tn.taxonomy_notes_id,
    tn.label,
    GREATEST(
      CASE WHEN tn.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(tn.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.taxonomy_notes AS tn
  WHERE tn.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, tn.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    tn.taxonomy_notes_id,
    tn.label,
    (1.0 - (tn.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.taxonomy_notes AS tn
  WHERE tn.emb IS NOT NULL
  ORDER BY tn.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT taxonomy_notes_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT taxonomy_notes_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    taxonomy_notes_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY taxonomy_notes_id
)
SELECT
  taxonomy_notes_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
