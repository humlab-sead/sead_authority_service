/**********************************************************************************************
**  Relative Age Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.relative_age_type cascade;

create or replace view authority.relative_age_type as
  select
    t.relative_age_type_id,
    t.age_type as label,
    authority.immutable_unaccent(lower(t.age_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_relative_age_types as t;

create index if not exists tbl_relative_age_types_norm_trgm
  on public.tbl_relative_age_types
    using gin ( (authority.immutable_unaccent(lower(age_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_relative_age_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_relative_age_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_relative_age_type(text, integer) cascade;
drop function if exists authority.fuzzy_relative_age_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_relative_age_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  relative_age_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.relative_age_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.relative_age_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
