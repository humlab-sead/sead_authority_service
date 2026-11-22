/**********************************************************************************************
**  RDB Code - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.rdb_code cascade;

create or replace view authority.rdb_code as
  select
    t.rdb_code_id,
    t.rdb_category as label,
    authority.immutable_unaccent(lower(t.rdb_category)) as norm_label,
  t.rdb_definition as description,
  authority.immutable_unaccent(lower(t.rdb_definition)) as norm_description,
    nullif(concat_ws(' / ', scope_1.rdb_system), '') as context,
    authority.immutable_unaccent(lower(nullif(concat_ws(' / ', scope_1.rdb_system), ''))) as norm_context  from public.tbl_rdb_codes as t  left join public.tbl_rdb_systems scope_1 on scope_1.rdb_system_id = t.rdb_system_id;

create index if not exists tbl_rdb_codes_norm_trgm
  on public.tbl_rdb_codes
    using gin ( (authority.immutable_unaccent(lower(rdb_category))) gin_trgm_ops );

create index if not exists tbl_rdb_codes_norm_desc_trgm
  on public.tbl_rdb_codes
    using gin ( (authority.immutable_unaccent(lower(rdb_definition))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_rdb_code
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_rdb_code('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_rdb_code(text, integer) cascade;
drop function if exists authority.fuzzy_rdb_code(text, integer, double precision, double precision) cascade;
drop function if exists authority.fuzzy_rdb_code(text, integer, double precision, double precision, text) cascade;

create or replace function authority.fuzzy_rdb_code(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50,
  p_context text default null) returns table (
  rdb_code_id integer,
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
      s.rdb_code_id,
      s.label,
      s.description,
      s.norm_label,      s.context,
      s.norm_context,      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q) end as label_sim,
      coalesce(strict_word_similarity(pq.q, s.norm_description), 0) as description_sim
    from authority.rdb_code as s
    cross join params pq
  )
  , filtered as (
    select *
    from scored
    where scored.label_sim >= p_label_threshold
       or scored.description_sim >= p_description_threshold
  )
  , matched as (
    select filtered.*
    from filtered
    cross join params pq
    where pq.ctx is null
       or position(pq.ctx in coalesce(filtered.norm_context, '')) > 0
  )
  , selected as (
    select matched.*, params.ctx is not null as context_match
    from matched
    cross join params
    union all
    select filtered.*, false as context_match
    from filtered
    cross join params
    where params.ctx is not null
      and not exists (select 1 from matched)
  )
  select
    selected.rdb_code_id,
    selected.label,
    selected.description,
    selected.label_sim,
    least(1.0, selected.label_sim + 0.15 * selected.description_sim) as name_sim,
    count(*) over (partition by selected.norm_label) > 1 as label_ambiguous,
    selected.context,
    selected.context_match
  from selected
  order by name_sim desc, selected.label_sim desc, selected.label
  limit p_limit;
$$;
