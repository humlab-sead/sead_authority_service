/**********************************************************************************************
**  Taxa Order - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.taxa_tree_order cascade;

create or replace view authority.taxa_tree_order as  select
    t.order_id,
    t.order_name as label,
    authority.immutable_unaccent(lower(t.order_name)) as norm_label,
    t.record_type_id  from public.tbl_taxa_tree_orders as t  join public.tbl_record_types rt using (record_type_id);
create index if not exists tbl_taxa_tree_orders_norm_trgm
  on public.tbl_taxa_tree_orders
    using gin ( (authority.immutable_unaccent(lower(order_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_order
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_order('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_order(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_order(
  p_text text,
  p_limit integer default 10) returns table (
  order_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.order_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_order as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;