/**********************************************************************************************
**  Record Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.record_type cascade;

create or replace view authority.record_type as  select
    t.record_type_id,
    t.record_type_name as label,
    authority.immutable_unaccent(lower(t.record_type_name)) as norm_label,
    t.record_type_description  from public.tbl_record_types as t;
create index if not exists tbl_record_types_norm_trgm
  on public.tbl_record_types
    using gin ( (authority.immutable_unaccent(lower(record_type_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_record_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_record_type('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_record_type(text, integer) cascade;

create or replace function authority.fuzzy_record_type(
  p_text text,
  p_limit integer default 10) returns table (
  record_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.record_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.record_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;