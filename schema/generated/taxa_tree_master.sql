/**********************************************************************************************
**  Taxa - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.taxa_tree_master cascade;

create or replace view authority.taxa_tree_master as  select
    t.taxon_id,
    t.species as label,
    authority.immutable_unaccent(lower(t.species)) as norm_label,
    t.genus_id  from public.tbl_taxa_tree_master as t  join public.tbl_taxa_tree_genera gen using (genus_id);
create index if not exists tbl_taxa_tree_master_norm_trgm
  on public.tbl_taxa_tree_master
    using gin ( (authority.immutable_unaccent(lower(species))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_master
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_master('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_master(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_master(
  p_text text,
  p_limit integer default 10) returns table (
  taxon_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.taxon_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_master as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;