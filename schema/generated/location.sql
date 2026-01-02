/**********************************************************************************************
**  Location - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.location cascade;

create or replace view authority.location as  select
    t.location_id,
    t.location_name as label,
    authority.immutable_unaccent(lower(t.location_name)) as norm_label,
    t.default_lat_dd as latitude,
    t.default_long_dd as longitude,
    t.location_type_id,
    lt.location_type,
    st_setsrid(st_makepoint(t.default_long_dd, t.default_lat_dd), 4326) as geom  from public.tbl_locations as t  join public.tbl_location_types lt using (location_type_id);
create index if not exists tbl_locations_norm_trgm
  on public.tbl_locations
    using gin ( (authority.immutable_unaccent(lower(location_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_location
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_location('query text', 10); ** Params     location_type_ids: Filter by location type IDs ****************************************************************************************************/

drop function if exists authority.fuzzy_location(text, integer, integer[]) cascade;

create or replace function authority.fuzzy_location(
  p_text text,
  p_limit integer default 10,
  location_type_ids integer[] default null) returns table (
  location_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  , filter_params as (    select location_type_id
    from tbl_location_types
    where array_length(location_type_ids, 1) is null
       or location_type_id = ANY(location_type_ids)
  )  select
    s.location_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.location as s
  cross join params pq  join filter_params using (location_type_id)  where s.norm_label % pq.q      order by name_sim desc, s.label
  limit p_limit;
$$;