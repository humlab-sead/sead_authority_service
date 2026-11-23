/**********************************************************************************************
**  Dating Material - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.dating_material cascade;

create or replace view authority.dating_material as
  select
    t.dating_material_id,
    t.material_dated as label,
    authority.immutable_unaccent(lower(t.material_dated)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_dating_material as t;

create index if not exists tbl_dating_material_norm_trgm
  on public.tbl_dating_material
    using gin ( (authority.immutable_unaccent(lower(material_dated))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_dating_material
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_dating_material('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_dating_material(text, integer) cascade;
drop function if exists authority.fuzzy_dating_material(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_dating_material(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  dating_material_id integer,
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
    s.dating_material_id,
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
  from authority.dating_material as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
