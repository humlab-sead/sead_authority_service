
/* Data Type: implemented inline in strategy class for simplicity */

/***************************************************************************************************
 ** Table     authority.data_type_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over data types
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
drop table if exists authority.data_type_embeddings cascade;

create table authority.data_type_embeddings (
  data_type_id integer primary key references public.tbl_data_types(data_type_id) on delete cascade,
  emb          vector(768) not null
);

create index if not exists data_type_embeddings_ivfflat_idx
  on authority.data_type_embeddings
    using ivfflat (emb vector_cosine_ops)
    with (lists = 100);

drop view if exists authority.data_type cascade;
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

drop function if exists authority.fuzzy_data_type(text, integer) cascade;
create or replace function authority.fuzzy_data_type(
  p_text text,
  p_limit integer default 10
) returns table (
  data_type_id integer,
  label text,
  name_sim double precision
) language sql stable
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
drop function if exists authority.semantic_data_type(vector, integer) cascade;

create or replace function authority.semantic_data_type(
  qemb vector,
  p_limit integer default 10
) returns table (
    data_type_id integer,
    label        text,
    sem_sim      double precision
) language sql stable
as $$
  select
    dt.data_type_id,
    dt.label,
    1.0 - (dt.emb <=> qemb) as sem_sim
  from authority.data_type as dt
  where dt.emb is not null
  order by dt.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_data_type_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
drop function if exists authority.search_data_type_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_data_type_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
) returns table (
    data_type_id integer,
    label        text,
    trgm_sim     double precision,
    sem_sim      double precision,
    blend        double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      dt.data_type_id,
      dt.label,
      greatest(
        case when dt.norm_label = pq.q then 1.0
            else similarity(dt.norm_label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.data_type as dt
    cross join params pq
    where dt.norm_label % pq.q
    order by trgm_sim desc, dt.label
    limit k_trgm
  ),
  sem as (
    select
      dt.data_type_id,
      dt.label,
      (1.0 - (dt.emb <=> qemb))::double precision as sem_sim
    from authority.data_type as dt
    where dt.emb is not null
    order by dt.emb <=> qemb
    limit k_sem
  ),
  u as (
    select data_type_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select data_type_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      data_type_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by data_type_id
  )
  select
    data_type_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
 

-- call sead_utility.create_full_text_search_materialized_view();
