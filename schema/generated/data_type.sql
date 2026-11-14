/**********************************************************************************************
**  Data Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.data_type cascade;

create or replace view authority.data_type as
  select
    t.data_type_id,
    t.data_type_name as label,
    authority.immutable_unaccent(lower(t.data_type_name)) as norm_label,
  t.definition as description,
  authority.immutable_unaccent(lower(t.definition)) as norm_description,
    dtg.data_type_group_name as data_type_group_name,
    dtg.description as data_type_group_description  from public.tbl_data_types as t  left join public.tbl_data_type_groups dtg using (data_type_group_id);

create index if not exists tbl_data_types_norm_trgm
  on public.tbl_data_types
    using gin ( (authority.immutable_unaccent(lower(data_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_data_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_data_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_data_type(text, integer) cascade;
drop function if exists authority.fuzzy_data_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_data_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  data_type_id integer,
  label text,
  description text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.data_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.data_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
