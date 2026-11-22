/**********************************************************************************************
**  Value Class - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.value_class cascade;

create or replace view authority.value_class as
  select
    t.value_class_id,
    t.name as label,
    authority.immutable_unaccent(lower(t.name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description,
    nullif(concat_ws(' / ', scope_1.name, scope_2.method_name), '') as context,
    authority.immutable_unaccent(lower(nullif(concat_ws(' / ', scope_1.name, scope_2.method_name), ''))) as norm_context  from public.tbl_value_classes as t  left join public.tbl_value_types scope_1 on scope_1.value_type_id = t.value_type_id  left join public.tbl_methods scope_2 on scope_2.method_id = t.method_id;

create index if not exists tbl_value_classes_norm_trgm
  on public.tbl_value_classes
    using gin ( (authority.immutable_unaccent(lower(name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_value_class
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_value_class('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_value_class(text, integer) cascade;
drop function if exists authority.fuzzy_value_class(text, integer, double precision, double precision) cascade;
drop function if exists authority.fuzzy_value_class(text, integer, double precision, double precision, text) cascade;

create or replace function authority.fuzzy_value_class(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50,
  p_context text default null) returns table (
  value_class_id integer,
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
      s.value_class_id,
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
    from authority.value_class as s
    cross join params pq
    where case when s.norm_label = pq.q then 1.0
               else similarity(s.norm_label, pq.q) end >= p_label_threshold
  )
  , matched as (
    select scored.*
    from scored
    cross join params pq
    where pq.ctx is null
       or position(pq.ctx in coalesce(scored.norm_context, '')) > 0
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
    selected.value_class_id,
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
