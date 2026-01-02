/**********************************************************************************************
**  Bibliographic Reference - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/
drop view if exists authority.bibliographic_reference cascade;

create or replace view authority.bibliographic_reference as  select
    t.biblio_id,
    t.full_reference as label,
    authority.immutable_unaccent(lower(t.full_reference)) as norm_label,
    t.title,
    t.doi,
    t.bugs_reference,
    t.isbn,
    t.notes,
    t.year,
    t.authors,
    t.url,
    authority.immutable_unaccent(lower(t.bugs_reference)) as norm_bugs_reference,
    authority.immutable_unaccent(lower(t.title)) as norm_title,
    authority.immutable_unaccent(lower(t.authors)) as norm_authors  from public.tbl_biblio as t;
create index if not exists tbl_biblio_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(full_reference))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_bibliographic_reference
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_bibliographic_reference('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_bibliographic_reference(text, integer) cascade;

create or replace function authority.fuzzy_bibliographic_reference(
  p_text text,
  p_limit integer default 10) returns table (
  biblio_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.biblio_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.bibliographic_reference as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;