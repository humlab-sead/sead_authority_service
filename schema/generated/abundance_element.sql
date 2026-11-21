/**********************************************************************************************
**  Abundance Element - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.abundance_element cascade;

create or replace view authority.abundance_element as
  select
    t.abundance_element_id,
    t.element_name as label,
    authority.immutable_unaccent(lower(t.element_name)) as norm_label,
  t.element_description as description,
  authority.immutable_unaccent(lower(t.element_description)) as norm_description  from public.tbl_abundance_elements as t;

create index if not exists tbl_abundance_elements_norm_trgm
  on public.tbl_abundance_elements
    using gin ( (authority.immutable_unaccent(lower(element_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_abundance_element
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_abundance_element('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_abundance_element(text, integer) cascade;
drop function if exists authority.fuzzy_abundance_element(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_abundance_element(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  abundance_element_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.abundance_element_id,
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
    ) as name_sim
  from authority.abundance_element as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
