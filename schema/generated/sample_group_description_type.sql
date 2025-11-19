/**********************************************************************************************
**  Sample Group Description Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.sample_group_description_type cascade;

create or replace view authority.sample_group_description_type as  select
    t.sample_group_description_type_id,
    t.type_name as label,
    authority.immutable_unaccent(lower(t.type_name)) as norm_label,
    t.type_description  from public.tbl_sample_group_description_types as t;
create index if not exists tbl_sample_group_description_types_norm_trgm
  on public.tbl_sample_group_description_types
    using gin ( (authority.immutable_unaccent(lower(type_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_group_description_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_group_description_type('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_group_description_type(text, integer) cascade;

create or replace function authority.fuzzy_sample_group_description_type(
  p_text text,
  p_limit integer default 10) returns table (
  sample_group_description_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.sample_group_description_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_group_description_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;