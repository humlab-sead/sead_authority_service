/**********************************************************************************************
**  Taxonomic Order System - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.taxonomic_order_system cascade;

create or replace view authority.taxonomic_order_system as  select
    t.taxonomic_order_system_id,
    t.system_name as label,
    authority.immutable_unaccent(lower(t.system_name)) as norm_label,
    t.system_description  from public.tbl_taxonomic_order_systems as t;
create index if not exists tbl_taxonomic_order_systems_norm_trgm
  on public.tbl_taxonomic_order_systems
    using gin ( (authority.immutable_unaccent(lower(system_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxonomic_order_system
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxonomic_order_system('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_taxonomic_order_system(text, integer) cascade;

create or replace function authority.fuzzy_taxonomic_order_system(
  p_text text,
  p_limit integer default 10) returns table (
  taxonomic_order_system_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.taxonomic_order_system_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxonomic_order_system as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;