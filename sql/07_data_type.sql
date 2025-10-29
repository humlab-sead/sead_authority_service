
/* Data Type: implemented inline in strategy class for simplicity */

/***************************************************************************************************
 ** Table     authority.data_type_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over data types
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.data_type_embeddings CASCADE;

CREATE TABLE authority.data_type_embeddings (
  data_type_id INTEGER PRIMARY KEY REFERENCES public.tbl_data_types(data_type_id) ON DELETE CASCADE,
  emb          VECTOR(768) NOT NULL,
  updated      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS data_type_embeddings_ivfflat_idx
  ON authority.data_type_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

drop view if exists authority.data_type;
create or replace view authority.data_type as
  select  dt.data_type_id,
          dt.data_type_name as label,
          dt.definition as description,
          authority.immutable_unaccent(lower(dt.data_type_name)) as norm_label,
          e.emb
  from public.tbl_data_types dt
  left join authority.data_type_embeddings e using (data_type_id);

create index if not exists tbl_data_types_norm_trgm
  on public.tbl_data_types
    using gin ( (authority.immutable_unaccent(lower(data_type_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_data_type(text, integer);
create or replace function authority.fuzzy_data_type(
	p_text text,
	p_limit integer default 10
) returns table (
	data_type_id integer,
	label text,
	name_sim double precision
)
language sql
stable
as $$
    select
      s.data_type_id,
      s.label,
      greatest(
          case when s.norm_label = pq.q then 1.0
              else similarity(s.norm_label, pq.q)
          end, 0.0001
      ) as name_sim
    from authority.data_type as s
      cross join (
      select authority.immutable_unaccent(lower('year'))::text as q
    ) as pq
    where s.norm_label % pq.q       -- trigram candidate filter
    order by name_sim desc, s.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_data_type
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_data_type(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_data_type(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  data_type_id INTEGER,
  label        TEXT,
  sem_sim      DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  dt.data_type_id,
  dt.label,
  1.0 - (dt.emb <=> qemb) AS sem_sim
FROM authority.data_type AS dt
WHERE dt.emb IS NOT NULL
ORDER BY dt.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_data_type_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_data_type_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_data_type_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  data_type_id INTEGER,
  label        TEXT,
  trgm_sim     DOUBLE PRECISION,
  sem_sim      DOUBLE PRECISION,
  blend        DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
trgm AS (
  SELECT
    dt.data_type_id,
    dt.label,
    GREATEST(
      CASE WHEN dt.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(dt.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.data_type AS dt
  WHERE dt.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, dt.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    dt.data_type_id,
    dt.label,
    (1.0 - (dt.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.data_type AS dt
  WHERE dt.emb IS NOT NULL
  ORDER BY dt.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT data_type_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT data_type_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    data_type_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY data_type_id
)
SELECT
  data_type_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
 

-- call sead_utility.create_full_text_search_materialized_view();
