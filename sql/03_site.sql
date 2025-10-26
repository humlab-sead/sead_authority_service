/**********************************************************************************************
 ** Table  authority.site_embeddings
 ** Note   Embeddings side table for sites in schema authority
 **        Used for semantic search with pgvector
 **        Choose the dimension to match the embedding model (example uses 768).
 **          site_id: the primary key of the site this embedding belongs to
 **          emb: the actual embedding vector, stored as a pgvector vector type
 **          active: a boolean flag indicating whether this embedding is active (useful for soft deletes or temporary deactivations)
 **          updated_at: timestamp when the embedding was last updated
 **          language: optional text field to tag the embedding with a language code
 **        The last three columns are metadata helpers for managing and governing the embeddings.
 **        They’re not required by PostgreSQL or pgvector itself, but they make the architecture
 **        easier to maintain and to debug over time.
 **********************************************************************************************/

DROP TABLE IF EXISTS authority.site_embeddings;

CREATE TABLE IF NOT EXISTS authority.site_embeddings (
  site_id    INTEGER PRIMARY KEY REFERENCES public.tbl_sites(site_id) ON DELETE CASCADE,
  emb        VECTOR(768),             -- embedding vector
  language   TEXT,                    -- optional language tag
  active     BOOLEAN DEFAULT TRUE,    -- optional soft-deactivation flag
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
CREATE INDEX IF NOT EXISTS site_embeddings_ivfflat
  ON authority.site_embeddings
  USING ivfflat (emb vector_cosine_ops)
  WITH (lists = 100);


/**********************************************************************************************
 **  Site
 **********************************************************************************************/
DROP MATERIALIZED VIEW IF EXISTS authority.sites;

CREATE MATERIALIZED VIEW authority.sites AS
SELECT
  t.site_id,
  t.site_name AS label,
  authority.immutable_unaccent(lower(t.site_name)) AS norm_label,
  t.latitude_dd,
  t.longitude_dd,
  t.national_site_identifier,
  t.site_description,
  ST_SetSRID(ST_MakePoint(t.longitude_dd, t.latitude_dd), 4326) AS geom,
  e.emb
FROM public.tbl_sites AS t
LEFT JOIN authority.site_embeddings AS e USING (site_id)
WHERE t.active = TRUE;  -- keep only active sites from base table

-- Required to allow REFRESH MATERIALIZED VIEW CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS sites_uidx
  ON authority.sites (site_id);

-- Trigram index must be on the MV column we filter with (%), not on base table.
CREATE INDEX IF NOT EXISTS sites_norm_trgm
  ON authority.sites
  USING gin (norm_label gin_trgm_ops);

-- Vector search (semantic) on the MV
CREATE INDEX IF NOT EXISTS sites_vec_ivfflat
  ON authority.sites
  USING ivfflat (emb vector_cosine_ops)
  WITH (lists = 100);

-- (First-time populate)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY authority.sites;
-- ANALYZE authority.sites;

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sites
 ** What       2) A trigram fuzzy search function (takes TEXT + LIMIT)
 **            This returns top-K by trigram similarity using pg_trgm’s similarity().
 **            Adjust pg_trgm.similarity_threshold if you want to tune sensitivity globally.
 **            You can also set it per-session before calling this function.
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.fuzzy_sites(TEXT, INTEGER);

CREATE OR REPLACE FUNCTION authority.fuzzy_sites(
  p_text  TEXT,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  site_id  INTEGER,
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
  s.site_id,
  s.label,
  GREATEST(
    CASE WHEN s.norm_label = (SELECT q FROM params) THEN 1.0
         ELSE similarity(s.norm_label, (SELECT q FROM params))
    END,
    0.0001
  ) AS name_sim
FROM authority.sites AS s
WHERE s.norm_label % (SELECT q FROM params)
ORDER BY name_sim DESC, s.label
LIMIT p_limit;

$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_sites
 ** What       3) A semantic search function (takes TEXT + LIMIT)
 **            Note: cosine similarity = 1 - cosine distance. Range is [-1,1] unless vectors are unit-normalized.
 **            This returns top-K by cosine similarity using the query embedding passed in.
 **            Because Postgres itself won’t compute embeddings, we accept the query embedding as
 **            a parameter; your application computes it (via Ollama) and passes it to SQL.
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_sites(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_sites(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  site_id INTEGER,
  label   TEXT,
  sem_sim DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  s.site_id,
  s.label,
  1.0 - (s.emb <=> qemb) AS sem_sim
FROM authority.sites AS s
WHERE s.emb IS NOT NULL
ORDER BY s.emb <=> qemb
LIMIT p_limit;
$$;
-- If you prefer to read from the side table instead of MV, use the original JOIN:
-- SELECT s.site_id, s.label, 1.0 - (e.emb <=> qemb) AS sem_sim
-- FROM authority.sites s
-- JOIN authority.site_embeddings e USING (site_id)
-- WHERE e.emb IS NOT NULL
-- ORDER BY e.emb <=> qemb
-- LIMIT p_limit;

/***************************************************************************************************
 ** Procedure  authority.search_sites_hybrid
 ** What       A hybrid function (trigram + semantic union + blend)
 **            Pulls top-K from both channels, de-dups, blends scores,
 **            and returns a compact list for the LLM (or directly for deterministic reconciliation).
 **            Pass qemb from your app (Ollama embeddings) when calling search_sites_hybrid.
 **            Adjust alpha if you want to favor trigram or semantic differently per domain.
 **            You can add language/active filters by joining authority.site_embeddings
 **            (or extending the authority.sites view with flags) and adding WHERE clauses.
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_sites_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_sites_hybrid(
  p_text  TEXT,               -- raw query text
  qemb    VECTOR,             -- query embedding (same dim as stored vectors)
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5  -- weight for trigram vs semantic
)
RETURNS TABLE (
  site_id  INTEGER,
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
    s.site_id,
    s.label,
    GREATEST(
      CASE WHEN s.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(s.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.sites AS s
  WHERE s.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, s.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    s.site_id,
    s.label,
    (1.0 - (s.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.sites AS s
  WHERE s.emb IS NOT NULL
  ORDER BY s.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT site_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT site_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    site_id,
    MAX(label) AS label,       -- labels are identical per site_id; MAX is safe & portable
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY site_id
)
SELECT
  site_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;