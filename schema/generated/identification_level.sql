/**********************************************************************************************
**  Identification Level - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.identification_level cascade;

create or replace view authority.identification_level as
  select
    t.identification_level_id,
    t.identification_level_name as label,
    authority.immutable_unaccent(lower(t.identification_level_name)) as norm_label,
  t.notes as description,
  authority.immutable_unaccent(lower(t.notes)) as norm_description  from public.tbl_identification_levels as t;

create index if not exists tbl_identification_levels_norm_trgm
  on public.tbl_identification_levels
    using gin ( (authority.immutable_unaccent(lower(identification_level_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_identification_level
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_identification_level('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_identification_level(text, integer) cascade;
drop function if exists authority.fuzzy_identification_level(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_identification_level(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  identification_level_id integer,
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
    s.identification_level_id,
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
  from authority.identification_level as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
