/**********************************************************************************************
 ** Table  authority.bibliographic_reference_embeddings
 ** Note   Embeddings side table for Bibliographic Reference in schema authority
 **        Used for semantic search with pgvector
 **        Generated from template by generate_entity_schema.py
 **********************************************************************************************/

drop table if exists authority.bibliographic_reference_embeddings cascade;

create table if not exists authority.bibliographic_reference_embeddings (
  biblio_id integer primary key references public.tbl_biblio(biblio_id) on delete cascade,
  emb vector(768)
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
create index if not exists bibliographic_reference_embeddings_ivfflat
  on authority.bibliographic_reference_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);
/***************************************************************************************************
 ** Procedure  authority.update_bibliographic_reference_embeddings
 ** What       Updates embeddings in authority.bibliographic_reference_embeddings table
 ** Usage      SELECT authority.update_bibliographic_reference_embeddings();        -- Update only missing
 **            SELECT authority.update_bibliographic_reference_embeddings(true);    -- Force update all
 ** Arguments  p_force_update: If true, regenerate all embeddings; if false (default), only compute missing ones
 ** Returns    Number of rows updated
 ****************************************************************************************************/
 
drop function if exists authority.update_bibliographic_reference_embeddings(boolean) cascade;

create or replace function authority.update_bibliographic_reference_embeddings(
  p_force_update boolean default false
) returns integer
language plpgsql volatile
as $$
declare
  rec record;
  v_emb vector(768);
  v_text text;
  v_rows_updated integer := 0;
begin
  raise notice 'Updating bibliographic_reference embeddings (force_update: %)', p_force_update;
  
  for rec in
    select t.biblio_id,
           t.full_reference,
           t.title    from public.tbl_biblio t
    where p_force_update 
       or not exists (
         select 1 from authority.bibliographic_reference_embeddings e 
         where e.biblio_id = t.biblio_id
       )
  loop
    -- Construct text for embedding (combine label and description if available)
    v_text := rec.full_reference;    if rec.title is not null then
      v_text := v_text || ' ' || rec.title;
    end if;    
    -- Compute embedding (assumes authority.compute_text_embedding exists)
    v_emb := authority.compute_text_embedding(v_text);
    
    -- Upsert into embeddings table
    insert into authority.bibliographic_reference_embeddings (biblio_id, emb)
    values (rec.biblio_id, v_emb)
    on conflict (biblio_id) do update
      set emb = excluded.emb;
    
    v_rows_updated := v_rows_updated + 1;
    
    -- Progress reporting every 100 rows
    if v_rows_updated % 100 = 0 then
      raise notice '  → Processed % rows', v_rows_updated;
    end if;
  end loop;
  
  raise notice 'Completed: % rows updated for bibliographic_reference', v_rows_updated;
  return v_rows_updated;
end;
$$;

/**********************************************************************************************
**  Bibliographic Reference - Semantic Search Objects (Vector Embeddings)
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file does NOT modify authority.bibliographic_reference view.
**        It creates a separate embeddings table that can be joined with the view when needed.
**        Semantic search functions perform the join internally.
**********************************************************************************************/

/***************************************************************************************************
 ** Procedure  authority.semantic_bibliographic_reference
 ** What       Semantic search function using pgvector embeddings
 ** Usage      SELECT * FROM authority.semantic_bibliographic_reference(qemb::vector, 10);
 ** Note       Joins authority.bibliographic_reference view with authority.bibliographic_reference_embeddings table
 ****************************************************************************************************/

drop function if exists authority.semantic_bibliographic_reference(vector, integer) cascade;

create or replace function authority.semantic_bibliographic_reference(
  qemb vector,
  p_limit integer default 10
) returns table (
  biblio_id integer,
  label text,
  sem_sim double precision
) language sql stable
as $$
  select
    v.biblio_id,
    v.label,
    1.0 - (e.emb <=> qemb) as sem_sim
  from authority.bibliographic_reference as v
  inner join authority.bibliographic_reference_embeddings as e using (biblio_id)
  where e.emb is not null
  order by e.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_bibliographic_reference_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ** Arguments
 **            p_text: raw query text
 **            qemb:  query embedding (same dim as stored vectors)
 **            k_trgm: number of trigram results to return (default 30)
 **            k_sem:  number of semantic results to return (default 30)
 **            k_final: number of final results to return (default 20)
 **            alpha:   blending factor for trigram vs semantic (default 0.5) ****************************************************************************************************/
 
drop function if exists authority.search_bibliographic_reference_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_bibliographic_reference_hybrid(
  p_text text,
  qemb vector,
  k_trgm integer default 30,
  k_sem integer default 30,
  k_final integer default 20,
  alpha double precision default 0.5) returns table (
  biblio_id integer,
  label text,
  trgm_sim double precision,
  sem_sim double precision,
  blend double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  , trgm as (
    select
      e.biblio_id,
      e.label,
      greatest(
        case when e.norm_label = pq.q then 1.0
            else similarity(e.norm_label, pq.q)
        end, 0.0001
      ) as trgm_sim
    from authority.bibliographic_reference as e
    cross join params pq    where e.norm_label % pq.q    order by trgm_sim desc, e.label
    limit k_trgm
  )
  , sem as (
    select
      v.biblio_id,
      v.label,
      (1.0 - (emb.emb <=> qemb))::double precision as sem_sim
    from authority.bibliographic_reference as v
    inner join authority.bibliographic_reference_embeddings as emb using (biblio_id)    where emb.emb is not null    order by emb.emb <=> qemb
    limit k_sem
  )
  , u as (
    select biblio_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select biblio_id, label, null::double precision as trgm_sim, sem_sim from sem
  )
  , agg as (
    select
      biblio_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim) as sem_sim
    from u
    group by biblio_id
  )
  select
    biblio_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim, 0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;