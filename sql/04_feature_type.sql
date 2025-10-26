/**********************************************************************************************
 ** Table  authority.feature_type_embeddings
 ** Note   Embeddings side table for feature types in schema authority
 **        Used for semantic search with pgvector
 **********************************************************************************************/

DROP TABLE IF EXISTS authority.feature_type_embeddings;

CREATE TABLE IF NOT EXISTS authority.feature_type_embeddings (
  feature_type_id INTEGER PRIMARY KEY REFERENCES public.tbl_feature_types(feature_type_id) ON DELETE CASCADE,
  emb             VECTOR(768),             -- embedding vector
  language        TEXT,                    -- optional language tag
  active          BOOLEAN DEFAULT TRUE,    -- optional soft-deactivation flag
  updated_at      TIMESTAMPTZ DEFAULT now()
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
CREATE INDEX IF NOT EXISTS feature_type_embeddings_ivfflat
  ON authority.feature_type_embeddings
  USING ivfflat (emb vector_cosine_ops)
  WITH (lists = 100);


/**********************************************************************************************
**  Feature Type
**********************************************************************************************/

drop view if exists authority.feature_types;
create or replace view authority.feature_types as
  select  ft.feature_type_id,
          ft.feature_type_name as label,
          ft.feature_type_description as description,
          authority.immutable_unaccent(lower(ft.feature_type_name)) as norm_label,
          e.emb
  from public.tbl_feature_types ft
  left join authority.feature_type_embeddings e using (feature_type_id);

create index if not exists tbl_feature_types_norm_trgm
  on public.tbl_feature_types
    using gin ( (authority.immutable_unaccent(lower(feature_type_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_feature_types(text, integer);
create or replace function authority.fuzzy_feature_types(
	p_text text,
	p_limit integer default 10
) returns table (
	feature_type_id integer,
	label text,
	name_sim double precision
)
language sql
stable
as $$
  with params as (
        select authority.immutable_unaccent(lower(p_text))::text as q
  )
    select
      s.feature_type_id,
      s.label,
      greatest(
          case when s.norm_label = (select q from params) then 1.0
              else similarity(s.norm_label, (select q from params))
          end, 0.0001
      ) as name_sim
    from authority.feature_types as s
    where s.norm_label % (select q from params)       -- trigram candidate filter
    order by name_sim desc, s.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_feature_types
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_feature_types(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_feature_types(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  feature_type_id INTEGER,
  label           TEXT,
  sem_sim         DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  ft.feature_type_id,
  ft.label,
  1.0 - (ft.emb <=> qemb) AS sem_sim
FROM authority.feature_types AS ft
WHERE ft.emb IS NOT NULL
ORDER BY ft.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_feature_types_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_feature_types_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_feature_types_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  feature_type_id INTEGER,
  label           TEXT,
  trgm_sim        DOUBLE PRECISION,
  sem_sim         DOUBLE PRECISION,
  blend           DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
trgm AS (
  SELECT
    ft.feature_type_id,
    ft.label,
    GREATEST(
      CASE WHEN ft.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(ft.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.feature_types AS ft
  WHERE ft.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, ft.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    ft.feature_type_id,
    ft.label,
    (1.0 - (ft.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.feature_types AS ft
  WHERE ft.emb IS NOT NULL
  ORDER BY ft.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT feature_type_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT feature_type_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    feature_type_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY feature_type_id
)
SELECT
  feature_type_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
 