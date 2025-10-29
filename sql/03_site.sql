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
DROP MATERIALIZED VIEW IF EXISTS authority.site;

CREATE MATERIALIZED VIEW authority.site AS
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
CREATE UNIQUE INDEX IF NOT EXISTS site_uidx
  ON authority.site (site_id);

-- Trigram index must be on the MV column we filter with (%), not on base table.
CREATE INDEX IF NOT EXISTS site_norm_trgm
  ON authority.site
  USING gin (norm_label gin_trgm_ops);

-- Vector search (semantic) on the MV
CREATE INDEX IF NOT EXISTS site_vec_ivfflat
  ON authority.site
  USING ivfflat (emb vector_cosine_ops)
  WITH (lists = 100);

-- (First-time populate)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY authority.site;
-- ANALYZE authority.site;

/***************************************************************************************************
 ** Procedure  authority.fuzzy_site
 ** What       2) A trigram fuzzy search function (takes TEXT + LIMIT)
 **            This returns top-K by trigram similarity using pg_trgm's similarity().
 **            Adjust pg_trgm.similarity_threshold if you want to tune sensitivity globally.
 **            You can also set it per-session before calling this function.
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.fuzzy_site(TEXT, INTEGER);

CREATE OR REPLACE FUNCTION authority.fuzzy_site(
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
FROM authority.site AS s
WHERE s.norm_label % (SELECT q FROM params)
ORDER BY name_sim DESC, s.label
LIMIT p_limit;

$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_site
 ** What       3) A semantic search function (takes TEXT + LIMIT)
 **            Note: cosine similarity = 1 - cosine distance. Range is [-1,1] unless vectors are unit-normalized.
 **            This returns top-K by cosine similarity using the query embedding passed in.
 **            Because Postgres itself won't compute embeddings, we accept the query embedding as
 **            a parameter; your application computes it (via Ollama) and passes it to SQL.
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_site(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_site(
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
FROM authority.site AS s
WHERE s.emb IS NOT NULL
ORDER BY s.emb <=> qemb
LIMIT p_limit;
$$;
-- If you prefer to read from the side table instead of MV, use the original JOIN:
-- SELECT s.site_id, s.label, 1.0 - (e.emb <=> qemb) AS sem_sim
-- FROM authority.site s
-- JOIN authority.site_embeddings e USING (site_id)
-- WHERE e.emb IS NOT NULL
-- ORDER BY e.emb <=> qemb
-- LIMIT p_limit;

/***************************************************************************************************
 ** Procedure  authority.search_site_hybrid
 ** What       A hybrid function (trigram + semantic union + blend)
 **            Pulls top-K from both channels, de-dups, blends scores,
 **            and returns a compact list for the LLM (or directly for deterministic reconciliation).
 **            Pass qemb from your app (Ollama embeddings) when calling search_site_hybrid.
 **            Adjust alpha if you want to favor trigram or semantic differently per domain.
 **            You can add language/active filters by joining authority.site_embeddings
 **            (or extending the authority.site view with flags) and adding WHERE clauses.
  ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 **            Uses full_reference field for both trigram and semantic matching
 ** Arguments
 **            p_text: raw query text
 **            qemb:  query embedding (same dim as stored vectors)
 **            k_trgm: number of trigram results to return
 **            k_sem:  number of semantic results to return
 **            k_final: number of final results to return
 **            alpha:   blending factor for hybrid search
****************************************************************************************************/
drop function if exists authority.search_site_hybrid(text, vector, integer, integer, integer, double precision);

create or replace function authority.search_site_hybrid(
  p_text  text,               -- raw query text
  qemb    vector,             -- query embedding (same dim as stored vectors)
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5  -- weight for trigram vs semantic
)
returns table (
  site_id  integer,
  label    text,
  trgm_sim double precision,
  sem_sim  double precision,
  blend    double precision
)
language sql stable as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      s.site_id,
      s.label,
      greatest(
        case when s.norm_label = (select q from params) then 1.0
            else similarity(s.norm_label, (select q from params))
        end,
        0.0001
      ) as trgm_sim
    from authority.site as s
    where s.norm_label % (select q from params)
    order by trgm_sim desc, s.label
    limit k_trgm
  ),
  sem as (
    select
      s.site_id,
      s.label,
      (1.0 - (s.emb <=> qemb))::double precision as sem_sim
    from authority.site as s
    where s.emb is not null
    order by s.emb <=> qemb
    limit k_sem
  ),
  u as (
    select site_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select site_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      site_id,
      max(label) as label,       -- labels are identical per site_id; max is safe & portable
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by site_id
  )
  select
    site_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;