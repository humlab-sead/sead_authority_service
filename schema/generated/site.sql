/**********************************************************************************************
**  Site - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop materialized view if exists authority.site cascade;

create materialized view authority.site as  select
    t.site_id,
    t.site_name as label,
    authority.immutable_unaccent(lower(t.site_name)) as norm_label,
    t.site_description,
    t.national_site_identifier,
    t.latitude_dd,
    t.longitude_dd,
    ST_SetSRID(ST_MakePoint(t.longitude_dd, t.latitude_dd), 4326) AS geom  from public.tbl_sites as t;
-- Required to allow REFRESH MATERIALIZED VIEW CONCURRENTLY
create unique index if not exists site_uidx
  on authority.site (site_id);

-- Trigram index must be on the MV column we filter with (%), not on base table.
create index if not exists site_norm_trgm
  on authority.site
    using gin (norm_label gin_trgm_ops);

-- (First-time populate)
-- refresh materialized view concurrently authority.site;
-- analyze authority.site;
/***************************************************************************************************
 ** Procedure  authority.fuzzy_site
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_site('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_site(text, integer) cascade;

create or replace function authority.fuzzy_site(
  p_text text,
  p_limit integer default 10) returns table (
  site_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.site_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.site as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;