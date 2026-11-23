/**********************************************************************************************
**  Relative Age - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.relative_age cascade;

create or replace view authority.relative_age as
  select
    t.relative_age_id,
    t.relative_age_name as label,
    authority.immutable_unaccent(lower(t.relative_age_name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_relative_ages as t;

create index if not exists tbl_relative_ages_norm_trgm
  on public.tbl_relative_ages
    using gin ( (authority.immutable_unaccent(lower(relative_age_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_relative_age
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_relative_age('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_relative_age(text, integer) cascade;
drop function if exists authority.fuzzy_relative_age(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_relative_age(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  relative_age_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision,
  label_ambiguous boolean
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q  )
  select
    s.relative_age_id,
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
    ) as name_sim,
    count(*) over (partition by s.norm_label) > 1 as label_ambiguous
  from authority.relative_age as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
