/**********************************************************************************************
**  Taxa Genus - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxa_tree_genus cascade;

create or replace view authority.taxa_tree_genus as
  select
    t.genus_id,
    t.genus_name as label,
    authority.immutable_unaccent(lower(t.genus_name)) as norm_label,
  null::text as description,
  null::text as norm_description,
    t.family_id,
    nullif(concat_ws(' / ', scope_1.family_name), '') as context,
    authority.immutable_unaccent(lower(nullif(concat_ws(' / ', scope_1.family_name), ''))) as norm_context  from public.tbl_taxa_tree_genera as t  join public.tbl_taxa_tree_families fam using (family_id)  left join public.tbl_taxa_tree_families scope_1 on scope_1.family_id = t.family_id;

create index if not exists tbl_taxa_tree_genera_norm_trgm
  on public.tbl_taxa_tree_genera
    using gin ( (authority.immutable_unaccent(lower(genus_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_genus
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_genus('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_genus(text, integer) cascade;
drop function if exists authority.fuzzy_taxa_tree_genus(text, integer, double precision, double precision) cascade;
drop function if exists authority.fuzzy_taxa_tree_genus(text, integer, double precision, double precision, text) cascade;

create or replace function authority.fuzzy_taxa_tree_genus(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50,
  p_context text default null) returns table (
  genus_id integer,
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
      s.genus_id,
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
    from authority.taxa_tree_genus as s
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
    selected.genus_id,
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
