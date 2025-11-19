/**********************************************************************************************
**  Taxonomy Note - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.taxonomy_note cascade;

create or replace view authority.taxonomy_note as  select
    t.taxonomy_notes_id,
    t.taxonomy_notes as label,
    authority.immutable_unaccent(lower(t.taxonomy_notes)) as norm_label  from public.tbl_taxonomy_notes as t;
create index if not exists tbl_taxonomy_notes_norm_trgm
  on public.tbl_taxonomy_notes
    using gin ( (authority.immutable_unaccent(lower(taxonomy_notes))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxonomy_note
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxonomy_note('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_taxonomy_note(text, integer) cascade;

create or replace function authority.fuzzy_taxonomy_note(
  p_text text,
  p_limit integer default 10) returns table (
  taxonomy_notes_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.taxonomy_notes_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxonomy_note as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;