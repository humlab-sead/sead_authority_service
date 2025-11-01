/**********************************************************************************************
**  Taxa Tree Master (Species Level)
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxa_tree_master_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxa (species level)
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings are based on full taxonomic name (genus + species)
 ****************************************************************************************************/
drop table if exists authority.taxa_tree_master_embeddings cascade;

create table authority.taxa_tree_master_embeddings (
  taxon_id integer primary key references public.tbl_taxa_tree_master(taxon_id) on delete cascade,
  emb      vector(768) not null,
  updated  timestamptz default now()
);

create index if not exists taxa_tree_master_embeddings_ivfflat_idx
  on authority.taxa_tree_master_embeddings
    using ivfflat (emb vector_cosine_ops)
    with (lists = 100);

drop view if exists authority.taxa_tree_master;
create or replace view authority.taxa_tree_master as
  select  
    t.taxon_id,
    concat(g.genus_name, ' ', t.species) as label,
    t.species,
    t.genus_id,
    t.author_id,
    g.genus_name,
    a.author_name,
    authority.immutable_unaccent(lower(concat(g.genus_name, ' ', t.species))) as norm_label,
    e.emb
  from public.tbl_taxa_tree_master t
  left join public.tbl_taxa_tree_genera g using (genus_id)
  left join public.tbl_taxa_tree_authors a using (author_id)
  left join authority.taxa_tree_master_embeddings e using (taxon_id);

create index if not exists tbl_taxa_tree_master_norm_trgm
  on public.tbl_taxa_tree_master
    using gin ( (authority.immutable_unaccent(lower(species))) gin_trgm_ops );

drop function if exists authority.fuzzy_taxa_tree_master(text, integer);
create or replace function authority.fuzzy_taxa_tree_master(
  p_text  text,
  p_limit integer default 10
) returns table (
  taxon_id integer,
  label    text,
  name_sim double precision
) language sql
stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    t.taxon_id,
    t.label,
    greatest(
      case when t.norm_label = (select q from params) then 1.0
           else similarity(t.norm_label, (select q from params))
      end,
      0.0001
    ) as name_sim
  from authority.taxa_tree_master as t
  where t.norm_label % (select q from params)
  order by name_sim desc, t.label
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_tree_master
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Searches based on full taxonomic name (genus + species)
 ****************************************************************************************************/
drop function if exists authority.semantic_taxa_tree_master(vector, integer);

create or replace function authority.semantic_taxa_tree_master(
  qemb    vector,
  p_limit integer default 10
) returns table (
  taxon_id integer,
  label    text,
  sem_sim  double precision
) language sql stable
as $$
  select t.taxon_id, t.label, 1.0 - (t.emb <=> qemb) as sem_sim
  from authority.taxa_tree_master as t
  where t.emb is not null
  order by t.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxa_tree_master_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 **            Searches full taxonomic name (genus + species)
 ****************************************************************************************************/
drop function if exists authority.search_taxa_tree_master_hybrid(text, vector, integer, integer, integer, double precision);

create or replace function authority.search_taxa_tree_master_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
) returns table (
  taxon_id integer,
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
      t.taxon_id,
      t.label,
      greatest(
        case when t.norm_label = pq.q then 1.0
            else similarity(t.norm_label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.taxa_tree_master as t
    cross join params pq
    where t.norm_label % pq.q
    order by trgm_sim desc, t.label
    limit k_trgm
  ),
  sem as (
    select
      t.taxon_id,
      t.label,
      (1.0 - (t.emb <=> qemb))::double precision as sem_sim
    from authority.taxa_tree_master as t
    where t.emb is not null
    order by t.emb <=> qemb
    limit k_sem
  ),
  u as (
    select taxon_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select taxon_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      taxon_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by taxon_id
  )
  select
    taxon_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
