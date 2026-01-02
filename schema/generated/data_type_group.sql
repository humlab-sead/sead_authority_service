/**********************************************************************************************
**  Data Type Group - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.data_type_group cascade;

create or replace view authority.data_type_group as  select
    t.data_type_group_id,
    t.data_type_group_name as label,
    authority.immutable_unaccent(lower(t.data_type_group_name)) as norm_label,
    t.description  from public.tbl_data_type_groups as t;
create index if not exists tbl_data_type_groups_norm_trgm
  on public.tbl_data_type_groups
    using gin ( (authority.immutable_unaccent(lower(data_type_group_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_data_type_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_data_type_group('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_data_type_group(text, integer) cascade;

create or replace function authority.fuzzy_data_type_group(
  p_text text,
  p_limit integer default 10) returns table (
  data_type_group_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.data_type_group_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.data_type_group as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;