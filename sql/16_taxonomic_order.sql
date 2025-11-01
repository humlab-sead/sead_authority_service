/**********************************************************************************************
**  Taxonomic Order (Code Mappings)
**********************************************************************************************/

/***************************************************************************************************
 ** Note      This table contains taxonomic codes for organizing species within hierarchies
 **           and referencing external systems (GBIF, Artdatabanken, etc.)
 **           Search is primarily by code rather than text, so embeddings have limited utility
 **           but are included for consistency with other authority tables
 ****************************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxonomic_order_embeddings
 ** What      Stores 768-dimensional embeddings for taxonomic order codes
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings based on string representation of taxonomic_code
 ****************************************************************************************************/
drop table if exists authority.taxonomic_order_embeddings cascade;

create table authority.taxonomic_order_embeddings (
  taxonomic_order_id integer primary key references public.tbl_taxonomic_order(taxonomic_order_id) on delete cascade,
  emb                vector(768) not null,
  updated            timestamptz default now()
);

create index if not exists taxonomic_order_embeddings_ivfflat_idx
  on authority.taxonomic_order_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);

drop view if exists authority.taxonomic_order cascade;
create or replace view authority.taxonomic_order as
  select  
    txo.taxonomic_order_id,
    txo.taxonomic_code::text as label,
    txo.taxon_id,
    txo.taxonomic_code,
    txo.taxonomic_order_system_id,
    e.emb
  from public.tbl_taxonomic_order txo
  left join authority.taxonomic_order_embeddings e using (taxonomic_order_id);

create index if not exists tbl_taxonomic_order_code_trgm
  on public.tbl_taxonomic_order
    using gin ( (taxonomic_code::text) gin_trgm_ops );

drop function if exists authority.fuzzy_taxonomic_order(text, integer) cascade;
create or replace function authority.fuzzy_taxonomic_order(
  p_text text,
  p_limit integer default 10
) returns table (
  taxonomic_order_id integer,
  label              text,
  name_sim           double precision
) language sql stable
as $$
  with params as (
    select p_text::text as q
  )
    select
      txo.taxonomic_order_id,
      txo.label,
      greatest(
        case when txo.label = pq.q then 1.0
            else similarity(txo.label, pq.q)
        end,
        0.0001
      ) as name_sim
    from authority.taxonomic_order as txo
    cross join params pq
    where txo.label % pq.q
    order by name_sim desc, txo.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxonomic_order
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Limited utility for numeric codes but included for API consistency
 ****************************************************************************************************/
drop function if exists authority.semantic_taxonomic_order(vector, integer) cascade;

create or replace function authority.semantic_taxonomic_order(
  qemb vector,
  p_limit integer default 10
) returns table ( 
  taxonomic_order_id integer,
  label              text,
  sem_sim            double precision
) language sql stable
as $$
  select txo.taxonomic_order_id, txo.label, 1.0 - (txo.emb <=> qemb) as sem_sim
  from authority.taxonomic_order as txo
  where txo.emb is not null
  order by txo.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxonomic_order_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      Primarily useful for exact or near-exact code matching
 ****************************************************************************************************/
drop function if exists authority.search_taxonomic_order_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_taxonomic_order_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
) returns table (
  taxonomic_order_id integer,
  label              text,
  trgm_sim           double precision,
  sem_sim            double precision,
  blend              double precision
) language sql stable
as $$
  with params as (
    select p_text::text as q
  ),
  trgm as (
    select
      txo.taxonomic_order_id,
      txo.label,
      greatest(
        case when txo.label = pq.q then 1.0
            else similarity(txo.label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.taxonomic_order as txo
    cross join params pq
    where txo.label % pq.q
    order by trgm_sim desc, txo.label
    limit k_trgm
  ),
  sem as (
    select
      txo.taxonomic_order_id,
      txo.label,
      (1.0 - (txo.emb <=> qemb))::double precision as sem_sim
    from authority.taxonomic_order as txo
    where txo.emb is not null
    order by txo.emb <=> qemb
    limit k_sem
  ),
  u as (
    select taxonomic_order_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select taxonomic_order_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      taxonomic_order_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by taxonomic_order_id
  )
  select
    taxonomic_order_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
