/**********************************************************************************************
**  Season Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.season_type cascade;

create or replace view authority.season_type as
  select
    t.season_type_id,
    t.season_type as label,
    authority.immutable_unaccent(lower(t.season_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_season_types as t;

create index if not exists tbl_season_types_norm_trgm
  on public.tbl_season_types
    using gin ( (authority.immutable_unaccent(lower(season_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_season_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_season_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_season_type(text, integer) cascade;
drop function if exists authority.fuzzy_season_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_season_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  season_type_id integer,
  label text,
  description text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.season_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.season_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
