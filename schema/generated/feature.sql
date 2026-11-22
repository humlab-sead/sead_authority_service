/**********************************************************************************************
**  Feature - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.feature cascade;

create or replace view authority.feature as
  select
    t.feature_id,
    t.feature_name as label,
    authority.immutable_unaccent(lower(t.feature_name)) as norm_label,
  t.feature_description as description,
  authority.immutable_unaccent(lower(t.feature_description)) as norm_description,
    nullif(concat_ws(' / ', scope_1.feature_type_name), '') as context,
    authority.immutable_unaccent(lower(nullif(concat_ws(' / ', scope_1.feature_type_name), ''))) as norm_context  from public.tbl_features as t  left join public.tbl_feature_types scope_1 on scope_1.feature_type_id = t.feature_type_id;

create index if not exists tbl_features_norm_trgm
  on public.tbl_features
    using gin ( (authority.immutable_unaccent(lower(feature_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_feature
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_feature('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_feature(text, integer) cascade;
drop function if exists authority.fuzzy_feature(text, integer, double precision, double precision) cascade;
drop function if exists authority.fuzzy_feature(text, integer, double precision, double precision, text) cascade;

create or replace function authority.fuzzy_feature(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50,
  p_context text default null) returns table (
  feature_id integer,
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
      s.feature_id,
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
    from authority.feature as s
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
    selected.feature_id,
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
