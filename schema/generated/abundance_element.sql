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
  authority.immutable_unaccent(lower(t.element_description)) as norm_description,
    nullif(concat_ws(' / ', scope_1.record_type_name), '') as context,
    authority.immutable_unaccent(lower(nullif(concat_ws(' / ', scope_1.record_type_name), ''))) as norm_context  from public.tbl_abundance_elements as t  left join public.tbl_record_types scope_1 on scope_1.record_type_id = t.record_type_id;

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
drop function if exists authority.fuzzy_abundance_element(text, integer, double precision, double precision, text) cascade;

create or replace function authority.fuzzy_abundance_element(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50,
  p_context text default null) returns table (
  abundance_element_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision,
  label_ambiguous boolean,
  context text,
  context_match boolean
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q,
           authority.immutable_unaccent(lower(nullif(p_context, '')))::text as ctx  )
  , scored as (
    select
      s.abundance_element_id,
      s.label,
      s.description,
      s.norm_label,
      s.context,
      s.norm_context,
      greatest(
        case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q)
        end, 0.0001
      ) as name_sim
    from authority.abundance_element as s
    cross join params pq
    where case when s.norm_label = pq.q then 1.0
               else similarity(s.norm_label, pq.q) end >= p_label_threshold
  )
  , matched as (
    select scored.*
    from scored
    cross join params pq
    where pq.ctx is null
       or pq.ctx = scored.norm_context
       or pq.ctx = any(string_to_array(scored.norm_context, ' / '))
  )
  , selected as (
    select matched.*, params.ctx is not null as context_match
    from matched
    cross join params
    union all
    select scored.*, false as context_match
    from scored
    cross join params
    where params.ctx is not null
      and not exists (select 1 from matched)
  )
  select
    selected.abundance_element_id,
    selected.label,
    selected.description,
    selected.name_sim as label_sim,
    selected.name_sim as name_sim,
    count(*) over (partition by selected.norm_label) > 1 as label_ambiguous,
    selected.context,
    selected.context_match
  from selected
  order by name_sim desc, selected.label
  limit p_limit;
$$;
