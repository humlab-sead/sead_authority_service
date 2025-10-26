

/**********************************************************************************************
**  Bibliographic Reference
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.bibliographic_reference_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over bibliographic references
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings are based on full_reference field (primary citation text)
 ****************************************************************************************************/
DROP TABLE IF EXISTS authority.bibliographic_reference_embeddings CASCADE;

CREATE TABLE authority.bibliographic_reference_embeddings (
  biblio_id INTEGER PRIMARY KEY REFERENCES public.tbl_biblio(biblio_id) ON DELETE CASCADE,
  emb       VECTOR(768) NOT NULL,
  updated   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS bibliographic_reference_embeddings_ivfflat_idx
  ON authority.bibliographic_reference_embeddings
    USING ivfflat (emb vector_cosine_ops)
    WITH (lists = 100);

drop view if exists authority.bibliographic_references;
create or replace view authority.bibliographic_references as
  select  
    b.biblio_id,
    b.full_reference as label,
    b.bugs_reference,
    b.doi,
    b.isbn,
    b.notes,
    b.title,
    b.year,
    b.authors,
    b.full_reference,
    b.url,
    authority.immutable_unaccent(lower(b.full_reference)) as norm_label,
    authority.immutable_unaccent(lower(b.bugs_reference)) as norm_bugs_reference,
    authority.immutable_unaccent(lower(b.title)) as norm_title,
    authority.immutable_unaccent(lower(b.authors)) as norm_authors,
    e.emb

  from public.tbl_biblio b
  left join authority.bibliographic_reference_embeddings e using (biblio_id)
  where b.full_reference is null
  ;

create index if not exists tbl_bibliographic_references_full_reference_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(full_reference))) gin_trgm_ops );

create index if not exists tbl_bibliographic_references_title_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(title))) gin_trgm_ops );

create index if not exists tbl_bibliographic_references_authors_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(authors))) gin_trgm_ops );

create index if not exists tbl_bibliographic_references_bugs_reference_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(bugs_reference))) gin_trgm_ops );

drop function if exists authority.fuzzy_bibliographic_references(text, integer, text, text, double precision);
drop function if exists authority.fuzzy_bibliographic_references(text, integer, text, text, double precision);

create or replace function authority.fuzzy_bibliographic_references(
  p_text         text,
  p_limit        integer default 10,
  p_target_field text    default 'full_reference',
  p_mode         text    default 'similarity',         -- 'similarity' | 'word' | 'strict_word'
  p_threshold    double precision default null         -- optional per-call operator threshold
) returns table (
  entity_id integer,
  biblio_id integer,
  label     text,
  name_sim  double precision
)
language plpgsql
stable
as $$
declare
  v_q       text;
  v_col     text;
  v_op      text;
  v_score   text;
  v_sql     text;
  v_guc     text;   -- which pg_trgm GUC to SET LOCAL, based on p_mode
begin
  -- validate inputs
  if p_target_field not in ('full_reference','title','authors','bugs_reference') then
    raise exception 'Invalid target field %', p_target_field;
  end if;

  if p_mode not in ('similarity','word','strict_word') then
    raise exception 'Invalid mode % (expected similarity|word|strict_word)', p_mode;
  end if;

  -- normalize query once
  v_q := authority.immutable_unaccent(lower(p_text));

  -- pick normalized column to search
  v_col := case p_target_field
             when 'full_reference' then 'norm_full_reference'
             when 'title'          then 'norm_title'
             when 'authors'        then 'norm_authors'
             when 'bugs_reference' then 'norm_bugs_reference'
           end;

  -- operator, score expression, and which GUC to set
  v_op := case p_mode
             when 'similarity'  then '%'
             when 'word'        then '<%'
             when 'strict_word' then '<<%'
           end;

  v_score := case p_mode
               when 'similarity'  then format('similarity(s.%I, $1)', v_col)
               when 'word'        then format('word_similarity(s.%I, $1)', v_col)
               when 'strict_word' then format('strict_word_similarity(s.%I, $1)', v_col)
             end;

  v_guc := case p_mode
             when 'similarity'  then 'pg_trgm.similarity_threshold'
             when 'word'        then 'pg_trgm.word_similarity_threshold'
             when 'strict_word' then 'pg_trgm.strict_word_similarity_threshold'
           end;

  -- Set a per-call (transaction-local) threshold for the chosen operator, if provided.
  -- This change auto-reverts at transaction end; no manual reset needed.
  if p_threshold is not null then
    execute format('SET LOCAL %s = %L', v_guc, p_threshold);
  end if;

  -- Build one query that uses the chosen operator & score
  v_sql := format($f$
    select
      s.biblio_id as entity_id,
      s.biblio_id,
      s.%2$I::text as label,
      greatest(
        case when s.%1$I = $1 then 1.0
             else %3$s
        end, 0.0001
      )::double precision as name_sim
    from (
      select biblio_id,
             %2$I,
             authority.immutable_unaccent(lower(%2$I)) as norm_%2$I
      from public.tbl_biblio
    ) s
    where s.%1$I %4$s $1       -- operator enforces threshold (uses GUC if set)
    order by name_sim desc, s.%2$I
    limit $2
  $f$, v_col, p_target_field, v_score, v_op);

  -- Execute (2 params if no threshold, 3rd param not used in SQL anymore)
  return query execute v_sql using v_q, p_limit;
end;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_bibliographic_references
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Searches based on full_reference field embeddings
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.semantic_bibliographic_references(VECTOR, INTEGER);

CREATE OR REPLACE FUNCTION authority.semantic_bibliographic_references(
  qemb    VECTOR,
  p_limit INTEGER DEFAULT 10
)
RETURNS TABLE (
  biblio_id INTEGER,
  label     TEXT,
  sem_sim   DOUBLE PRECISION
)
LANGUAGE sql
STABLE
AS $$
SELECT
  b.biblio_id,
  b.label,
  1.0 - (b.emb <=> qemb) AS sem_sim
FROM authority.bibliographic_references AS b
WHERE b.emb IS NOT NULL
ORDER BY b.emb <=> qemb
LIMIT p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_bibliographic_references_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 **            Uses full_reference field for both trigram and semantic matching
 ****************************************************************************************************/
DROP FUNCTION IF EXISTS authority.search_bibliographic_references_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

CREATE OR REPLACE FUNCTION authority.search_bibliographic_references_hybrid(
  p_text  TEXT,
  qemb    VECTOR,
  k_trgm  INTEGER DEFAULT 30,
  k_sem   INTEGER DEFAULT 30,
  k_final INTEGER DEFAULT 20,
  alpha   DOUBLE PRECISION DEFAULT 0.5
)
RETURNS TABLE (
  biblio_id INTEGER,
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
    b.biblio_id,
    b.label,
    GREATEST(
      CASE WHEN b.norm_label = (SELECT q FROM params) THEN 1.0
           ELSE similarity(b.norm_label, (SELECT q FROM params))
      END,
      0.0001
    ) AS trgm_sim
  FROM authority.bibliographic_references AS b
  WHERE b.norm_label % (SELECT q FROM params)
  ORDER BY trgm_sim DESC, b.label
  LIMIT k_trgm
),
sem AS (
  SELECT
    b.biblio_id,
    b.label,
    (1.0 - (b.emb <=> qemb))::DOUBLE PRECISION AS sem_sim
  FROM authority.bibliographic_references AS b
  WHERE b.emb IS NOT NULL
  ORDER BY b.emb <=> qemb
  LIMIT k_sem
),
u AS (
  SELECT biblio_id, label, trgm_sim, NULL::DOUBLE PRECISION AS sem_sim FROM trgm
  UNION
  SELECT biblio_id, label, NULL::DOUBLE PRECISION AS trgm_sim, sem_sim FROM sem
),
agg AS (
  SELECT
    biblio_id,
    MAX(label) AS label,
    MAX(trgm_sim) AS trgm_sim,
    MAX(sem_sim)  AS sem_sim
  FROM u
  GROUP BY biblio_id
)
SELECT
  biblio_id,
  label,
  COALESCE(trgm_sim, 0.0) AS trgm_sim,
  COALESCE(sem_sim,  0.0) AS sem_sim,
  (alpha * COALESCE(trgm_sim, 0.0) + (1.0 - alpha) * COALESCE(sem_sim, 0.0)) AS blend
FROM agg
ORDER BY blend DESC, label
LIMIT k_final;
$$;
