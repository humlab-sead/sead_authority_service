/**********************************************************************************************
**  Taxa Synonym - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxa_synonym cascade;

create or replace view authority.taxa_synonym as
  select
    t.synonym_id,
    t.synonym as label,
    authority.immutable_unaccent(lower(t.synonym)) as norm_label,
  null::text as description,
  null::text as norm_description,
    t.taxon_id  from public.tbl_taxa_synonyms as t  join public.tbl_taxa_tree_master ttm using (taxon_id);

create index if not exists tbl_taxa_synonyms_norm_trgm
  on public.tbl_taxa_synonyms
    using gin ( (authority.immutable_unaccent(lower(synonym))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_synonym
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_synonym('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_synonym(text, integer) cascade;
drop function if exists authority.fuzzy_taxa_synonym(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_taxa_synonym(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  synonym_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision,
  label_ambiguous boolean
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q  )
  select
    s.synonym_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim,
    count(*) over (partition by s.norm_label) > 1 as label_ambiguous
  from authority.taxa_synonym as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
