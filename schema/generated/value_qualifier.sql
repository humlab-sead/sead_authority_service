/**********************************************************************************************
**  Value Qualifier - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.value_qualifier cascade;

create or replace view authority.value_qualifier as
  select
    t.qualifier_id,
    t.symbol as label,
    authority.immutable_unaccent(lower(t.symbol)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_value_qualifiers as t;

create index if not exists tbl_value_qualifiers_norm_trgm
  on public.tbl_value_qualifiers
    using gin ( (authority.immutable_unaccent(lower(symbol))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_value_qualifier
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_value_qualifier('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_value_qualifier(text, integer) cascade;
drop function if exists authority.fuzzy_value_qualifier(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_value_qualifier(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  qualifier_id integer,
  label text,
  description text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.qualifier_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.value_qualifier as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
