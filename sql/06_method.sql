
/**********************************************************************************************
**  Method
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.method_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over methods
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.method_embeddings CASCADE;

CREATE TABLE authority.method_embeddings (
  method_id INTEGER PRIMARY KEY REFERENCES public.tbl_methods(method_id) ON DELETE CASCADE,
  emb       VECTOR(768) NOT NULL,
  updated   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS method_embeddings_ivfflat_idx
  ON authority.method_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

drop view if exists authority.methods;
create or replace materialized view authority.methods as
  select  m.method_id,
          m.method_name as label,
          m.description,
          authority.immutable_unaccent(lower(m.method_name)) as norm_label,
          e.emb
  from public.tbl_methods m
  left join authority.method_embeddings e using (method_id);

create index if not exists tbl_methods_norm_trgm
  on public.tbl_methods
    using gin ( (authority.immutable_unaccent(lower(method_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_methods(text, integer);
create or replace function authority.fuzzy_methods(
	p_text text,
	p_limit integer default 10
) returns table (
	method_id integer,
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
      s.method_id,
      s.label,
      greatest(
          case when s.norm_label = (select q from params) then 1.0
              else similarity(s.norm_label, (select q from params))
          end, 0.0001
      ) as name_sim
    from authority.methods as s
    where s.norm_label % (select q from params)
    order by name_sim desc, s.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_methods
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_methods(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_methods(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  method_id INTEGER,
  label     TEXT,
  sem_sim   DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  m.method_id,
  m.label,
  1.0 - (m.emb <=> qemb) AS sem_sim
FROM authority.methods AS m
WHERE m.emb IS NOT NULL
ORDER BY m.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_methods_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_methods_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_methods_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  method_id INTEGER,
  label     TEXT,
  trgm_sim  DOUBLE PRECISION,
  sem_sim   DOUBLE PRECISION,
  blend     DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
WITH params AS (
  SELECT authority.immutable_unaccent(lower(p_text))::TEXT AS q
),
trgm AS (
  SELECT
    m.method_id,
    m.label,
    GREATEST(
      CASE WHEN m.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(m.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.methods AS m
  WHERE m.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, m.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    m.method_id,
    m.label,
    (1.0 - (m.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.methods AS m
  WHERE m.emb IS NOT NULL
  ORDER BY m.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT method_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT method_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    method_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY method_id
)
SELECT
  method_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
