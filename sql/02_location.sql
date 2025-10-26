/**********************************************************************************************
 ** Table  authority.location_embeddings
 ** Note   Embeddings side table for locations in schema authority
 **        Used for semantic search with pgvector
 **********************************************************************************************/

DROP TABLE IF EXISTS authority.location_embeddings;

CREATE TABLE IF NOT EXISTS authority.location_embeddings (
  location_id INTEGER PRIMARY KEY REFERENCES public.tbl_locations(location_id) ON DELETE CASCADE,
  emb         VECTOR(768),             -- embedding vector
  language    TEXT,                    -- optional language tag
  active      BOOLEAN DEFAULT TRUE,    -- optional soft-deactivation flag
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
CREATE INDEX IF NOT EXISTS location_embeddings_ivfflat
  ON authority.location_embeddings
  USING ivfflat (emb vector_cosine_ops)
  WITH (lists = 100);


/**********************************************************************************************
**  Location
**********************************************************************************************/

drop view if exists authority.locations;
create or replace view authority.locations as
  select  l.location_id,
          l.location_name as label,
          authority.immutable_unaccent(lower(l.location_name)) as norm_label,
          l.default_lat_dd as latitude,
          l.default_long_dd as longitude,
          l.location_type_id,
          lt.location_type,
          l.description,
          st_setsrid(st_makepoint(l.default_long_dd, l.default_lat_dd), 4326) as geom,
          e.emb
  from public.tbl_locations l
  join public.tbl_location_types lt using (location_type_id)
  left join authority.location_embeddings e using (location_id);

create index if not exists tbl_locations_norm_trgm
  on public.tbl_locations
    using gin ( (authority.immutable_unaccent(lower(location_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_locations(text, integer);
create or replace function authority.fuzzy_locations(
	p_text text,
	p_limit integer default 10,
	variadic location_type_ids integer[] default null)
returns table (
	location_id integer,
	label text,
	name_sim double precision
)
language sql
stable
as $$
  with params as (
        select authority.immutable_unaccent(lower(p_text))::text as q
  ), location_types as (
		select location_type_id
		from tbl_location_types
		where array_length(location_type_ids, 1) is null
		 or location_type_id = ANY(location_type_ids)
	)
    select
      s.location_id,
      s.label,
      greatest(
          case when s.norm_label = (select q from params) then 1.0
              else similarity(s.norm_label, (select q from params))
          end, 0.0001
      ) as name_sim
    from authority.locations as s
    join location_types using (location_type_id)
    where s.norm_label % (select q from params)       -- trigram candidate filter
    order by name_sim desc, s.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_locations
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_locations(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_locations(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  location_id INTEGER,
  label       TEXT,
  sem_sim     DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  l.location_id,
  l.label,
  1.0 - (l.emb <=> qemb) AS sem_sim
FROM authority.locations AS l
WHERE l.emb IS NOT NULL
ORDER BY l.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_locations_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_locations_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION, INTEGER[]);

CREATE OR REPLACE FUNCTION authority.search_locations_hybrid(
  p_text             TEXT,
  qemb               VECTOR,
  k_trgm             INTEGER DEFAULT 30,
  k_sem              INTEGER DEFAULT 30,
  k_final            INTEGER DEFAULT 20,
  alpha              DOUBLE PRECISION DEFAULT 0.5,
  location_type_ids  INTEGER[] DEFAULT NULL
)
RETURNS TABLE (
  location_id INTEGER,
  label       TEXT,
  trgm_sim    DOUBLE PRECISION,
  sem_sim     DOUBLE PRECISION,
  blend       DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
location_types AS (
  SELECT location_type_id
  FROM tbl_location_types
  WHERE array_length(location_type_ids, 1) IS NULL
     OR location_type_id = ANY(location_type_ids)
),
trgm AS (
  SELECT
    l.location_id,
    l.label,
    GREATEST(
      CASE WHEN l.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(l.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.locations AS l
  JOIN location_types USING (location_type_id)
  WHERE l.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, l.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    l.location_id,
    l.label,
    (1.0 - (l.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.locations AS l
  JOIN location_types USING (location_type_id)
  WHERE l.emb IS NOT NULL
  ORDER BY l.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT location_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT location_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    location_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY location_id
)
SELECT
  location_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
