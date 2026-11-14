/**********************************************************************************************
**  Ecocode Group - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.ecocode_group cascade;

create or replace view authority.ecocode_group as
  select
    t.ecocode_group_id,
    t.name as label,
    authority.immutable_unaccent(lower(t.name)) as norm_label,
  t.definition as description,
  authority.immutable_unaccent(lower(t.definition)) as norm_description  from public.tbl_ecocode_groups as t;

create index if not exists tbl_ecocode_groups_norm_trgm
  on public.tbl_ecocode_groups
    using gin ( (authority.immutable_unaccent(lower(name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_ecocode_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_ecocode_group('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_ecocode_group(text, integer) cascade;
drop function if exists authority.fuzzy_ecocode_group(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_ecocode_group(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  ecocode_group_id integer,
  label text,
  description text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.ecocode_group_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.ecocode_group as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
