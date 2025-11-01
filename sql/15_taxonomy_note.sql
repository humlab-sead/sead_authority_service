/**********************************************************************************************
**  Taxonomy Notes
**********************************************************************************************/

/***************************************************************************************************
 ** Table     authority.taxonomy_note_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxonomy notes
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 **           Embeddings are based on taxonomy_notes text field (identification issues, references)
 ****************************************************************************************************/
drop table if exists authority.taxonomy_note_embeddings cascade;

create table authority.taxonomy_note_embeddings (
  taxonomy_notes_id integer primary key references public.tbl_taxonomy_notes(taxonomy_notes_id) on delete cascade,
  emb               vector(768) not null,
  updated           timestamptz default now()
);

create index if not exists taxonomy_note_embeddings_ivfflat_idx
  on authority.taxonomy_note_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);

drop view if exists authority.taxonomy_note cascade;
create or replace view authority.taxonomy_note as
  select  
    tn.taxonomy_notes_id,
    tn.taxonomy_notes as label,
    tn.taxon_id,
    tn.biblio_id,
    authority.immutable_unaccent(lower(tn.taxonomy_notes)) as norm_label,
    e.emb
  from public.tbl_taxonomy_notes tn
  left join authority.taxonomy_note_embeddings e using (taxonomy_notes_id);

create index if not exists tbl_taxonomy_notes_norm_trgm
  on public.tbl_taxonomy_notes
    using gin ( (authority.immutable_unaccent(lower(taxonomy_notes))) gin_trgm_ops );

drop function if exists authority.fuzzy_taxonomy_note(text, integer) cascade;
create or replace function authority.fuzzy_taxonomy_note(
  p_text  text,
  p_limit integer default 10
) returns table (
  taxonomy_notes_id integer,
  label             text,
  name_sim          double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    tn.taxonomy_notes_id,
    tn.label,
    greatest(
      case when tn.norm_label = pq.q then 1.0
           else similarity(tn.norm_label, pq.q)
      end,
      0.0001
    ) as name_sim
  from authority.taxonomy_note as tn
  cross join params pq
  where tn.norm_label % pq.q
  order by name_sim desc, tn.label
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxonomy_note
 ** What       Semantic search function using pgvector embeddings
 ** Notes      Particularly useful for finding notes about identification issues or similar taxa
 ****************************************************************************************************/
drop function if exists authority.semantic_taxonomy_note(vector, integer) cascade;

create or replace function authority.semantic_taxonomy_note(
  qemb vector,
  p_limit integer default 10
) returns table (
  taxonomy_notes_id integer,
  label             text,
  sem_sim           double precision
) language sql stable
as $$
  select tn.taxonomy_notes_id, tn.label, 1.0 - (tn.emb <=> qemb) as sem_sim
  from authority.taxonomy_note as tn
  where tn.emb is not null
  order by tn.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxonomy_note_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 **            Useful for finding similar identification issues or taxonomic confusion
 ****************************************************************************************************/
drop function if exists authority.search_taxonomy_note_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_taxonomy_note_hybrid(
  p_text  text,
  qemb    vector,
  k_trgm  integer default 30,
  k_sem   integer default 30,
  k_final integer default 20,
  alpha   double precision default 0.5
) returns table (
  taxonomy_notes_id integer,
  label             text,
  trgm_sim          double precision,
  sem_sim           double precision,
  blend             double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  trgm as (
    select
      tn.taxonomy_notes_id,
      tn.label,
      greatest(
        case when tn.norm_label = pq.q then 1.0
            else similarity(tn.norm_label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.taxonomy_note as tn
    cross join params pq
    where tn.norm_label % pq.q
    order by trgm_sim desc, tn.label
    limit k_trgm
  ),
  sem as (
    select
      tn.taxonomy_notes_id,
      tn.label,
      (1.0 - (tn.emb <=> qemb))::double precision as sem_sim
    from authority.taxonomy_note as tn
    where tn.emb is not null
    order by tn.emb <=> qemb
    limit k_sem
  ),
  u as (
    select taxonomy_notes_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select taxonomy_notes_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      taxonomy_notes_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by taxonomy_notes_id
  )
  select
    taxonomy_notes_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim,  0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;
