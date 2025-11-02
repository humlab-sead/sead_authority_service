/**********************************************************************************************
**  Record Type
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.record_type_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over record types
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
drop table if exists authority.record_type_embeddings cascade;

create table authority.record_type_embeddings (
  record_type_id integer primary key references public.tbl_record_types(record_type_id) on delete cascade,
  emb            vector(768) not null
);

create index if not exists record_type_embeddings_ivfflat_idx
  on authority.record_type_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);

drop view if exists authority.record_type cascade;
create or replace view authority.record_type as
  select  
    rt.record_type_id,
    rt.record_type_name as label,
    rt.record_type_description as description,
    authority.immutable_unaccent(lower(rt.record_type_name)) as norm_label,
    e.emb
  from public.tbl_record_types rt
  left join authority.record_type_embeddings e using (record_type_id);

create index if not exists tbl_record_types_norm_trgm
  on public.tbl_record_types
    using gin ( (authority.immutable_unaccent(lower(record_type_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_record_type(text, integer) cascade;
create or replace function authority.fuzzy_record_type(
  p_text  text,
  p_limit integer default 10
) returns table (
  record_type_id integer,
  label          text,
  name_sim       double precision
) language sql stable
as $$
    with params as (
      select authority.immutable_unaccent(lower(p_text))::text as q
    )
    select
      rt.record_type_id,
      rt.label,
      greatest(
        case when rt.norm_label = pq.q then 1.0
            else similarity(rt.norm_label, pq.q)
        end,
        0.0001
      ) as name_sim
    from authority.record_type as rt
    cross join params pq
    where rt.norm_label % pq.q
    order by name_sim desc, rt.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_record_type
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_record_type(vector, integer) cascade;

create or replace function authority.semantic_record_type(
  qemb vector,
  p_limit integer default 10
) returns table (
  record_type_id integer,
  label          text,
  sem_sim        double precision
) language sql stable
as $$
  select rt.record_type_id, rt.label, 1.0 - (rt.emb <=> qemb) as sem_sim
  from authority.record_type as rt
  where rt.emb is not null
  order by rt.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_record_type_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
drop function if exists authority.search_record_type_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_record_type_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
) returns table (
  record_type_id integer,
  label          text,
  trgm_sim       double precision,
  sem_sim        double precision,
  blend          double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      rt.record_type_id,
      rt.label,
      greatest(
        case when rt.norm_label = pq.q then 1.0
            else similarity(rt.norm_label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.record_type as rt
    cross join params pq
    where rt.norm_label % pq.q
    order by trgm_sim desc, rt.label
    limit k_trgm
  ),
  sem as (
    select
      rt.record_type_id,
      rt.label,
      (1.0 - (rt.emb <=> qemb))::double precision as sem_sim
    from authority.record_type as rt
    where rt.emb is not null
    order by rt.emb <=> qemb
    limit k_sem
  ),
  u as (
    select record_type_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select record_type_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      record_type_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by record_type_id
  )
  select
    record_type_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
