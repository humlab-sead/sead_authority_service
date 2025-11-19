/**********************************************************************************************
 ** Table  authority.site_embeddings
 ** Note   Embeddings side table for Site in schema authority
 **        Used for semantic search with pgvector
 **        Generated from template by generate_entity_schema.py
 **********************************************************************************************/

drop table if exists authority.site_embeddings cascade;

create table if not exists authority.site_embeddings (
  site_id integer primary key references public.tbl_sites(site_id) on delete cascade,
  emb vector(768)
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
create index if not exists site_embeddings_ivfflat
  on authority.site_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);
/***************************************************************************************************
 ** Procedure  authority.update_site_embeddings
 ** What       Updates embeddings in authority.site_embeddings table
 ** Usage      SELECT authority.update_site_embeddings();        -- Update only missing
 **            SELECT authority.update_site_embeddings(true);    -- Force update all
 ** Arguments  p_force_update: If true, regenerate all embeddings; if false (default), only compute missing ones
 ** Returns    Number of rows updated
 ****************************************************************************************************/
 
drop function if exists authority.update_site_embeddings(boolean) cascade;

create or replace function authority.update_site_embeddings(
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
  raise notice 'Updating site embeddings (force_update: %)', p_force_update;
  
  for rec in
    select t.site_id,
           t.site_name,
           t.site_description    from public.tbl_sites t
    where p_force_update 
       or not exists (
         select 1 from authority.site_embeddings e 
         where e.site_id = t.site_id
       )
  loop
    -- Construct text for embedding (combine label and description if available)
    v_text := rec.site_name;    if rec.site_description is not null then
      v_text := v_text || ' ' || rec.site_description;
    end if;    
    -- Compute embedding (assumes authority.compute_text_embedding exists)
    v_emb := authority.compute_text_embedding(v_text);
    
    -- Upsert into embeddings table
    insert into authority.site_embeddings (site_id, emb)
    values (rec.site_id, v_emb)
    on conflict (site_id) do update
      set emb = excluded.emb;
    
    v_rows_updated := v_rows_updated + 1;
    
    -- Progress reporting every 100 rows
    if v_rows_updated % 100 = 0 then
      raise notice '  → Processed % rows', v_rows_updated;
    end if;
  end loop;
  
  raise notice 'Completed: % rows updated for site', v_rows_updated;
  return v_rows_updated;
end;
$$;

/**********************************************************************************************
**  Site
**********************************************************************************************/
drop materialized view if exists authority.site cascade;

create materialized view authority.site as  select
    t.site_id,
    t.site_name as label,
    authority.immutable_unaccent(lower(t.site_name)) as norm_label,    t.site_description,    t.national_site_identifier,    t.latitude_dd,    t.longitude_dd,    ST_SetSRID(ST_MakePoint(t.longitude_dd, t.latitude_dd), 4326) AS geom,    e.emb
  from public.tbl_sites as t  left join authority.site_embeddings as e using (site_id);
-- Required to allow REFRESH MATERIALIZED VIEW CONCURRENTLY
create unique index if not exists site_uidx
  on authority.site (site_id);

-- Trigram index must be on the MV column we filter with (%), not on base table.
create index if not exists site_norm_trgm
  on authority.site
    using gin (norm_label gin_trgm_ops);

-- Vector search (semantic) on the MV
create index if not exists site_vec_ivfflat
  on authority.site
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);

-- (First-time populate)
-- REFRESH MATERIALIZED VIEW CONCURRENTLY authority.site;
-- ANALYZE authority.site;
/***************************************************************************************************
 ** Procedure  authority.fuzzy_site
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_site('query text', 10); ****************************************************************************************************/

drop function if exists authority.fuzzy_site(text, integer) cascade;

create or replace function authority.fuzzy_site(
  p_text text,
  p_limit integer default 10) returns table (
  site_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.site_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.site as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_site
 ** What       Semantic search function using pgvector embeddings
 ** Usage      SELECT * FROM authority.semantic_site(qemb::vector, 10);
 ****************************************************************************************************/

drop function if exists authority.semantic_site(vector, integer) cascade;

create or replace function authority.semantic_site(
  qemb vector,
  p_limit integer default 10
) returns table (
  site_id integer,
  label text,
  sem_sim double precision
) language sql stable
as $$
  select
    e.site_id,
    e.label,
    1.0 - (e.emb <=> qemb) as sem_sim
  from authority.site as e
  where e.emb is not null
  order by e.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_site_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ** Arguments
 **            p_text: raw query text
 **            qemb:  query embedding (same dim as stored vectors)
 **            k_trgm: number of trigram results to return (default 30)
 **            k_sem:  number of semantic results to return (default 30)
 **            k_final: number of final results to return (default 20)
 **            alpha:   blending factor for trigram vs semantic (default 0.5) ****************************************************************************************************/
drop function if exists authority.search_site_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_site_hybrid(
  p_text text,
  qemb vector,
  k_trgm integer default 30,
  k_sem integer default 30,
  k_final integer default 20,
  alpha double precision default 0.5) returns table (
  site_id integer,
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
      e.site_id,
      e.label,
      greatest(
        case when e.norm_label = pq.q then 1.0
            else similarity(e.norm_label, pq.q)
        end, 0.0001
      ) as trgm_sim
    from authority.site as e
    cross join params pq    where e.norm_label % pq.q    order by trgm_sim desc, e.label
    limit k_trgm
  )
  , sem as (
    select
      e.site_id,
      e.label,
      (1.0 - (e.emb <=> qemb))::double precision as sem_sim
    from authority.site as e    where e.emb is not null    order by e.emb <=> qemb
    limit k_sem
  )
  , u as (
    select site_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select site_id, label, null::double precision as trgm_sim, sem_sim from sem
  )
  , agg as (
    select
      site_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim) as sem_sim
    from u
    group by site_id
  )
  select
    site_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim, 0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;