/**********************************************************************************************
**  Data Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.data_type cascade;

create or replace view authority.data_type as
  select
    t.data_type_id,
    t.data_type_name as label,
    authority.immutable_unaccent(lower(t.data_type_name)) as norm_label,
  t.definition as description,
  authority.immutable_unaccent(lower(t.definition)) as norm_description,
    dtg.data_type_group_name as data_type_group_name,
    dtg.description as data_type_group_description,
    nullif(concat_ws(' / ', scope_1.data_type_group_name), '') as context,
    authority.immutable_unaccent(lower(nullif(concat_ws(' / ', scope_1.data_type_group_name), ''))) as norm_context  from public.tbl_data_types as t  left join public.tbl_data_type_groups dtg using (data_type_group_id)  left join public.tbl_data_type_groups scope_1 on scope_1.data_type_group_id = t.data_type_group_id;

create index if not exists tbl_data_types_norm_trgm
  on public.tbl_data_types
    using gin ( (authority.immutable_unaccent(lower(data_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_data_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_data_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_data_type(text, integer) cascade;
drop function if exists authority.fuzzy_data_type(text, integer, double precision, double precision) cascade;
drop function if exists authority.fuzzy_data_type(text, integer, double precision, double precision, text) cascade;

create or replace function authority.fuzzy_data_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50,
  p_context text default null) returns table (
  data_type_id integer,
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
      s.data_type_id,
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
    from authority.data_type as s
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
    selected.data_type_id,
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
