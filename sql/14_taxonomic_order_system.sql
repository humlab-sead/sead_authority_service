/**********************************************************************************************
**  Taxonomic Order Systems
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxonomic_order_system_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxonomic order systems
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings combine system name and description for richer semantic matching
 ****************************************************************************************************/
drop table if exists authority.taxonomic_order_system_embeddings cascade;

create table authority.taxonomic_order_system_embeddings (
  taxonomic_order_system_id integer primary key references public.tbl_taxonomic_order_systems(taxonomic_order_system_id) on delete cascade,
  emb                       vector(768) not null,
  updated                   timestamptz default now()
);

create index if not exists taxonomic_order_system_embeddings_ivfflat_idx
  on authority.taxonomic_order_system_embeddings
    using ivfflat (emb vector_cosine_ops)
    with (lists = 100);

drop view if exists authority.taxonomic_order_system cascade;
create or replace view authority.taxonomic_order_system as
  select  
    tos.taxonomic_order_system_id,
    tos.system_name as label,
    tos.system_description as description,
    authority.immutable_unaccent(lower(tos.system_name)) as norm_label,
    e.emb
  from public.tbl_taxonomic_order_systems tos
  left join authority.taxonomic_order_system_embeddings e using (taxonomic_order_system_id);

create index if not exists tbl_taxonomic_order_systems_norm_trgm
  on public.tbl_taxonomic_order_systems
    using gin ( (authority.immutable_unaccent(lower(system_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_taxonomic_order_system(text, integer) cascade;
create or replace function authority.fuzzy_taxonomic_order_system(
  p_text  text,
  p_limit integer default 10
) returns table (
  taxonomic_order_system_id integer,
  label                     text,
  name_sim                  double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    tos.taxonomic_order_system_id,
    tos.label,
    greatest(
      case when tos.norm_label = pq.q then 1.0
           else similarity(tos.norm_label, pq.q)
      end,
      0.0001
    ) as name_sim
  from authority.taxonomic_order_system as tos
  cross join params pq
  where tos.norm_label % pq.q
  order by name_sim desc, tos.label
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxonomic_order_system
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_taxonomic_order_system(vector, integer) cascade;

create or replace function authority.semantic_taxonomic_order_system(
  qemb    vector,
  p_limit integer default 10
) returns table (
  taxonomic_order_system_id integer,
  label                     text,
  sem_sim                   double precision
) language sql stable
as $$
  select
    tos.taxonomic_order_system_id,
    tos.label,
    1.0 - (tos.emb <=> qemb) as sem_sim
  from authority.taxonomic_order_system as tos
  where tos.emb is not null
  order by tos.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxonomic_order_system_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
drop function if exists authority.search_taxonomic_order_system_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_taxonomic_order_system_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
) returns table (
  taxonomic_order_system_id integer,
  label                     text,
  trgm_sim                  double precision,
  sem_sim                   double precision,
  blend                     double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      tos.taxonomic_order_system_id,
      tos.label,
      greatest(
        case when tos.norm_label = pq.q then 1.0
            else similarity(tos.norm_label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.taxonomic_order_system as tos
    cross join params pq
    where tos.norm_label % pq.q
    order by trgm_sim desc, tos.label
    limit k_trgm
  ),
  sem as (
    select
      tos.taxonomic_order_system_id,
      tos.label,
      (1.0 - (tos.emb <=> qemb))::double precision as sem_sim
    from authority.taxonomic_order_system as tos
    where tos.emb is not null
    order by tos.emb <=> qemb
    limit k_sem
  ),
  u as (
    select taxonomic_order_system_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select taxonomic_order_system_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      taxonomic_order_system_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by taxonomic_order_system_id
  )
  select
    taxonomic_order_system_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
