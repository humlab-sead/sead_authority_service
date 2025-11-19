/**********************************************************************************************
**  Taxa Family - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.taxa_tree_family cascade;

create or replace view authority.taxa_tree_family as  select
    t.family_id,
    t.family_name as label,
    authority.immutable_unaccent(lower(t.family_name)) as norm_label,
    t.order_id  from public.tbl_taxa_tree_families as t  join public.tbl_taxa_tree_orders ord using (order_id);
create index if not exists tbl_taxa_tree_families_norm_trgm
  on public.tbl_taxa_tree_families
    using gin ( (authority.immutable_unaccent(lower(family_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_family
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_family('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_family(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_family(
  p_text text,
  p_limit integer default 10) returns table (
  family_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.family_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_family as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;