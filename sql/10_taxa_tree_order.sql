/**********************************************************************************************
**  Taxa Tree Orders
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxa_tree_order_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxonomic orders
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
drop table if exists authority.taxa_tree_order_embeddings cascade;

create table authority.taxa_tree_order_embeddings (
  order_id integer primary key references public.tbl_taxa_tree_orders(order_id) on delete cascade,
  emb      vector(768) not null
);

create index if not exists taxa_tree_order_embeddings_ivfflat_idx
  on authority.taxa_tree_order_embeddings
    using ivfflat (emb vector_cosine_ops)
    with (lists = 100);

drop view if exists authority.taxa_tree_order cascade;
create or replace view authority.taxa_tree_order as
  select  
    o.order_id,
    o.order_name as label,
    o.record_type_id,
    o.sort_order,
    authority.immutable_unaccent(lower(o.order_name)) as norm_label,
    e.emb
  from public.tbl_taxa_tree_orders o
  left join authority.taxa_tree_order_embeddings e using (order_id);

create index if not exists tbl_taxa_tree_orders_norm_trgm
  on public.tbl_taxa_tree_orders
    using gin ( (authority.immutable_unaccent(lower(order_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_taxa_tree_order(text, integer) cascade;
create or replace function authority.fuzzy_taxa_tree_order(
  p_text  text,
  p_limit integer default 10
) returns table (
    order_id integer,
    label    text,
    name_sim double precision
  ) language sql stable
as $$
    with params as (
      select authority.immutable_unaccent(lower(p_text))::text as q
    )
    select
      o.order_id,
      o.label,
      greatest(
        case when o.norm_label = (select q from params) then 1.0
            else similarity(o.norm_label, (select q from params))
        end,
        0.0001
      ) as name_sim
    from authority.taxa_tree_order as o
    where o.norm_label % (select q from params)
    order by name_sim desc, o.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_tree_order
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_taxa_tree_order(vector, integer) cascade;

create or replace function authority.semantic_taxa_tree_order(
  qemb    vector,
  p_limit integer default 10
) returns table (
    order_id integer,
    label    text,
    sem_sim  double precision
) language sql stable
as $$
  select o.order_id, o.label, 1.0 - (o.emb <=> qemb) as sem_sim
  from authority.taxa_tree_order as o
  where o.emb is not null
  order by o.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search__hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
drop function if exists authority.search_taxa_tree_order_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_taxa_tree_order_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
) returns table (
  order_id integer,
  label    text,
  trgm_sim double precision,
  sem_sim  double precision,
  blend    double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      o.order_id,
      o.label,
      greatest(
        case when o.norm_label = (select q from params) then 1.0
            else similarity(o.norm_label, (select q from params))
        end,
        0.0001
      ) as trgm_sim
    from authority.taxa_tree_order as o
    where o.norm_label % (select q from params)
    order by trgm_sim desc, o.label
    limit k_trgm
  ),
  sem as (
    select
      o.order_id,
      o.label,
      (1.0 - (o.emb <=> qemb))::double precision as sem_sim
    from authority.taxa_tree_order as o
    where o.emb is not null
    order by o.emb <=> qemb
    limit k_sem
  ),
  u as (
    select order_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select order_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      order_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by order_id
  )
  select
    order_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
