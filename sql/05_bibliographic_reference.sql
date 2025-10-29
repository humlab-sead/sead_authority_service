

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

drop view if exists authority.bibliographic_reference;
create or replace view authority.bibliographic_reference as
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

drop function if exists authority.fuzzy_bibliographic_reference(text, integer, text, text, double precision);
drop function if exists authority.fuzzy_bibliographic_reference(text, integer, text, text, double precision);

create or replace function authority.fuzzy_bibliographic_reference(
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
 ** Procedure  authority.semantic_bibliographic_reference
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Searches based on full_reference field embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_bibliographic_reference(vector, integer);

create or replace function authority.semantic_bibliographic_reference(qemb vector, p_limit integer default 10)
returns table (
  biblio_id integer,
  label     text,
  sem_sim   double precision
)
  language sql stable as $$
  select
    b.biblio_id,
    b.label,
    1.0 - (b.emb <=> qemb) as sem_sim
  from authority.bibliographic_reference as b
  where b.emb is not null
  order by b.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
  ** Procedure  authority.search_bibliographic_reference_hybrid
  ** What       Hybrid search combining trigram and semantic search
  ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
  **            Uses full_reference field for both trigram and semantic matching
  **            p_text: raw query text
  **            qemb:  query embedding (same dim as stored vectors)
  **            k_trgm: number of trigram results to return
  **            k_sem:  number of semantic results to return
  **            k_final: number of final results to return
  **            alpha:   blending factor for hybrid search
 ****************************************************************************************************/
drop function if exists authority.search_bibliographic_reference_hybrid(text, vector, integer, integer, integer, double precision);

create or replace function authority.search_bibliographic_reference_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30, 
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
)
returns table (
  biblio_id integer,
  label     text,
  trgm_sim  double precision,
  sem_sim   double precision,
  blend     double precision
)
language sql stable as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      b.biblio_id,
      b.label,
      greatest(
        case when b.norm_label = pq.q then 1.0
            else similarity(b.norm_label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.bibliographic_reference as b
    cross join params pq
    where b.norm_label % pq.q
    order by trgm_sim desc, b.label
    limit k_trgm
  ),
  sem as (
    select
      b.biblio_id,
      b.label,
      (1.0 - (b.emb <=> qemb))::double precision as sem_sim
    from authority.bibliographic_reference as b
    where b.emb is not null
    order by b.emb <=> qemb
    limit k_sem
  ),
  u as (
    select biblio_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select biblio_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      biblio_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by biblio_id
  )
  select
    biblio_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
