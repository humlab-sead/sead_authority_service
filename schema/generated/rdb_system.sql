/**********************************************************************************************
**  RDB System - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.rdb_system cascade;

create or replace view authority.rdb_system as
  select
    t.rdb_system_id,
    t.rdb_system as label,
    authority.immutable_unaccent(lower(t.rdb_system)) as norm_label,
  null::text as description,
  null::text as norm_description  from public.tbl_rdb_systems as t;

create index if not exists tbl_rdb_systems_norm_trgm
  on public.tbl_rdb_systems
    using gin ( (authority.immutable_unaccent(lower(rdb_system))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_rdb_system
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_rdb_system('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_rdb_system(text, integer) cascade;
drop function if exists authority.fuzzy_rdb_system(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_rdb_system(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  rdb_system_id integer,
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
    s.rdb_system_id,
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
  from authority.rdb_system as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
