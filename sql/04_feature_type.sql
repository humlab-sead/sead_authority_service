/**********************************************************************************************
 ** Table  authority.feature_type_embeddings
 ** Note   Embeddings side table for feature types in schema authority
 **        Used for semantic search with pgvector
 **********************************************************************************************/

drop table if exists authority.feature_type_embeddings;

create table if not exists authority.feature_type_embeddings (
  feature_type_id integer primary key references public.tbl_feature_types(feature_type_id) on delete cascade,
  emb             vector(768),             -- embedding vector
  language        text,                    -- optional language tag
  active          boolean default true,    -- optional soft-deactivation flag
  updated_at      timestamptz default now()
);

-- vector index for fast ann search (cosine). tune lists to your row count.
create index if not exists feature_type_embeddings_ivfflat
  on authority.feature_type_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);


/**********************************************************************************************
**  Feature Type
**********************************************************************************************/

drop view if exists authority.feature_type;
create or replace view authority.feature_type as
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

drop function if exists authority.fuzzy_feature_type(text, integer);
create or replace function authority.fuzzy_feature_type(
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
        case when s.norm_label = pq.q then 1.0 else similarity(s.norm_label, pq.q) end,
        0.0001
      ) as name_sim
    from authority.feature_type as s
    cross join params pq
    where s.norm_label % pq.q       -- trigram candidate filter
    order by name_sim desc, s.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_feature_type
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_feature_type(vector, integer);

create or replace function authority.semantic_feature_type(
  qemb    vector,
  p_limit integer default 10
)
returns table (
  feature_type_id integer,
  label           text,
  sem_sim         double precision
)
language sql stable as $$
  select
    ft.feature_type_id,
    ft.label,
    1.0 - (ft.emb <=> qemb) as sem_sim
  from authority.feature_type as ft
  where ft.emb is not null
  order by ft.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_feature_type_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
drop function if exists authority.search_feature_type_hybrid(text, vector, integer, integer, integer, double precision);

create or replace function authority.search_feature_type_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
)
returns table (
  feature_type_id integer,
  label           text,
  trgm_sim        double precision,
  sem_sim         double precision,
  blend           double precision
)
  language sql stable as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      ft.feature_type_id,
      ft.label,
      greatest(
        case when ft.norm_label = pq.q then 1.0 else similarity(ft.norm_label, pq.q) end,
        0.0001
      ) as trgm_sim
    from authority.feature_type as ft
    cross join params pq
    where ft.norm_label % pq.q
    order by trgm_sim desc, ft.label
    limit k_trgm
  ),
  sem as (
    select
      ft.feature_type_id,
      ft.label,
      (1.0 - (ft.emb <=> qemb))::double precision as sem_sim
    from authority.feature_type as ft
    where ft.emb is not null
    order by ft.emb <=> qemb
    limit k_sem
  ),
  u as (
    select feature_type_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select feature_type_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      feature_type_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by feature_type_id
  )
  select
    feature_type_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
 