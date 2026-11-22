/**********************************************************************************************
**  Site Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.site_type cascade;

create or replace view authority.site_type as
  select
    t.site_type_id,
    t.site_type as label,
    authority.immutable_unaccent(lower(t.site_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description,
    nullif(concat_ws(' / ', scope_1.site_type_group), '') as context,
    authority.immutable_unaccent(lower(nullif(concat_ws(' / ', scope_1.site_type_group), ''))) as norm_context  from public.tbl_site_types as t  left join public.tbl_site_type_groups scope_1 on scope_1.site_type_group_id = t.site_type_group_id;

create index if not exists tbl_site_types_norm_trgm
  on public.tbl_site_types
    using gin ( (authority.immutable_unaccent(lower(site_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_site_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_site_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_site_type(text, integer) cascade;
drop function if exists authority.fuzzy_site_type(text, integer, double precision, double precision) cascade;
drop function if exists authority.fuzzy_site_type(text, integer, double precision, double precision, text) cascade;

create or replace function authority.fuzzy_site_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50,
  p_context text default null) returns table (
  site_type_id integer,
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
      s.site_type_id,
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
    from authority.site_type as s
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
    selected.site_type_id,
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
