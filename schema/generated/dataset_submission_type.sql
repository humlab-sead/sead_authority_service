/**********************************************************************************************
**  Dataset Submission Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.dataset_submission_type cascade;

create or replace view authority.dataset_submission_type as
  select
    t.submission_type_id,
    t.submission_type as label,
    authority.immutable_unaccent(lower(t.submission_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_dataset_submission_types as t;

create index if not exists tbl_dataset_submission_types_norm_trgm
  on public.tbl_dataset_submission_types
    using gin ( (authority.immutable_unaccent(lower(submission_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_dataset_submission_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_dataset_submission_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_dataset_submission_type(text, integer) cascade;
drop function if exists authority.fuzzy_dataset_submission_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_dataset_submission_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  submission_type_id integer,
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
    s.submission_type_id,
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
  from authority.dataset_submission_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;
