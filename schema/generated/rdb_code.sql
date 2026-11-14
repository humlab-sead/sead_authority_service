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
  authority.immutable_unaccent(lower(t.rdb_definition)) as norm_description  from public.tbl_rdb_codes as t;

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

create or replace function authority.fuzzy_rdb_code(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  rdb_code_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  , scored as (
    select
      s.rdb_code_id,
      s.label,
      s.description,
      case when s.norm_label = pq.q then 1.0
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
  select
    filtered.rdb_code_id,
    filtered.label,
    filtered.description,
    filtered.label_sim,
    least(1.0, filtered.label_sim + 0.15 * filtered.description_sim) as name_sim
  from filtered
  order by name_sim desc, filtered.label_sim desc, filtered.label
  limit p_limit;
$$;
