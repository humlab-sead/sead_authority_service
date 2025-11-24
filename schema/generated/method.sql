/**********************************************************************************************
**  Method - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.method cascade;

create or replace view authority.method as  select
    t.method_id,
    t.method_name as label,
    authority.immutable_unaccent(lower(t.method_name)) as norm_label,
    t.description,
    t.method_abbrev_or_alt_name  from public.tbl_methods as t;
create index if not exists tbl_methods_norm_trgm
  on public.tbl_methods
    using gin ( (authority.immutable_unaccent(lower(method_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_method
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_method('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_method(text, integer) cascade;

create or replace function authority.fuzzy_method(
  p_text text,
  p_limit integer default 10) returns table (
  method_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.method_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.method as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;