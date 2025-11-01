/**********************************************************************************************
**  Taxa Tree Families
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxa_tree_family_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxonomic families
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
drop table if exists authority.taxa_tree_family_embeddings cascade;

create table authority.taxa_tree_family_embeddings (
  family_id integer primary key references public.tbl_taxa_tree_families(family_id) on delete cascade,
  emb       vector(768) not null,
  updated   timestamptz default now()
);

create index if not exists taxa_tree_family_embeddings_ivfflat_idx
  on authority.taxa_tree_family_embeddings
    using ivfflat (emb vector_cosine_ops)
    with (lists = 100);

drop view if exists authority.taxa_tree_family cascade;
create or replace view authority.taxa_tree_family as
  select  
    f.family_id,
    f.family_name as label,
    f.order_id,
    authority.immutable_unaccent(lower(f.family_name)) as norm_label,
    e.emb
  from public.tbl_taxa_tree_families f
  left join authority.taxa_tree_family_embeddings e using (family_id);

create index if not exists tbl_taxa_tree_families_norm_trgm
  on public.tbl_taxa_tree_families
    using gin ( (authority.immutable_unaccent(lower(family_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_taxa_tree_family(text, integer) cascade;
create or replace function authority.fuzzy_taxa_tree_family(
  p_text  text,
  p_limit integer default 10
) returns table (
  family_id integer,
  label     text,
  name_sim  double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    f.family_id,
    f.label,
    greatest(
      case when f.norm_label = (select q from params) then 1.0
           else similarity(f.norm_label, (select q from params))
      end,
      0.0001
    ) as name_sim
  from authority.taxa_tree_family as f
  where f.norm_label % (select q from params)
  order by name_sim desc, f.label
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_tree_family
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_taxa_tree_family(vector, integer) cascade;

create or replace function authority.semantic_taxa_tree_family(
  qemb    vector,
  p_limit integer default 10
) returns table (
  family_id integer,
  label     text,
  sem_sim   double precision
) language sql stable
as $$
  select
    f.family_id,
    f.label,
    1.0 - (f.emb <=> qemb) as sem_sim
  from authority.taxa_tree_family as f
  where f.emb is not null
  order by f.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxa_tree_family_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
drop function if exists authority.search_taxa_tree_family_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_taxa_tree_family_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
) returns table (
  family_id integer,
  label     text,
  trgm_sim  double precision,
  sem_sim   double precision,
  blend     double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      f.family_id,
      f.label,
      greatest(
        case when f.norm_label = pq.q then 1.0
            else similarity(f.norm_label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.taxa_tree_family as f
    cross join params pq
    where f.norm_label % pq.q
    order by trgm_sim desc, f.label
    limit k_trgm
  ),
  sem as (
    select
      f.family_id,
      f.label,
      (1.0 - (f.emb <=> qemb))::double precision as sem_sim
    from authority.taxa_tree_family as f
    where f.emb is not null
    order by f.emb <=> qemb
    limit k_sem
  ),
  u as (
    select family_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select family_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      family_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by family_id
  )
  select
    family_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
