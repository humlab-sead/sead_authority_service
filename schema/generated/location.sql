/**********************************************************************************************
 ** Table  authority.location_embeddings
 ** Note   Embeddings side table for Location in schema authority
 **        Used for semantic search with pgvector
 **        Generated from template by generate_entity_schema.py
 **********************************************************************************************/

drop table if exists authority.location_embeddings cascade;

create table if not exists authority.location_embeddings (
  location_id integer primary key references public.tbl_locations(location_id) on delete cascade,
  emb vector(768)
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
create index if not exists location_embeddings_ivfflat
  on authority.location_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);
/***************************************************************************************************
 ** Procedure  authority.update_location_embeddings
 ** What       Updates embeddings in authority.location_embeddings table
 ** Usage      SELECT authority.update_location_embeddings();        -- Update only missing
 **            SELECT authority.update_location_embeddings(true);    -- Force update all
 ** Arguments  p_force_update: If true, regenerate all embeddings; if false (default), only compute missing ones
 ** Returns    Number of rows updated
 ****************************************************************************************************/
 
drop function if exists authority.update_location_embeddings(boolean) cascade;

create or replace function authority.update_location_embeddings(
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
  raise notice 'Updating location embeddings (force_update: %)', p_force_update;
  
  for rec in
    select t.location_id,
           t.location_name    from public.tbl_locations t
    where p_force_update 
       or not exists (
         select 1 from authority.location_embeddings e 
         where e.location_id = t.location_id
       )
  loop
    -- Construct text for embedding (combine label and description if available)
    v_text := rec.location_name;    
    -- Compute embedding (assumes authority.compute_text_embedding exists)
    v_emb := authority.compute_text_embedding(v_text);
    
    -- Upsert into embeddings table
    insert into authority.location_embeddings (location_id, emb)
    values (rec.location_id, v_emb)
    on conflict (location_id) do update
      set emb = excluded.emb;
    
    v_rows_updated := v_rows_updated + 1;
    
    -- Progress reporting every 100 rows
    if v_rows_updated % 100 = 0 then
      raise notice '  → Processed % rows', v_rows_updated;
    end if;
  end loop;
  
  raise notice 'Completed: % rows updated for location', v_rows_updated;
  return v_rows_updated;
end;
$$;

/**********************************************************************************************
**  Location
**********************************************************************************************/
drop view if exists authority.location cascade;

create or replace view authority.location as  select
    t.location_id,
    t.location_name as label,
    authority.immutable_unaccent(lower(t.location_name)) as norm_label,    t.default_lat_dd as latitude,    t.default_long_dd as longitude,    t.location_type_id,    lt.location_type,    st_setsrid(st_makepoint(t.default_long_dd, t.default_lat_dd), 4326) as geom,    e.emb
  from public.tbl_locations as t  join public.tbl_location_types lt using (location_type_id)  left join authority.location_embeddings as e using (location_id);
create index if not exists tbl_locations_norm_trgm
  on public.tbl_locations
    using gin ( (authority.immutable_unaccent(lower(location_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_location
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_location('query text', 10); ** Params     location_type_ids: Filter by location type IDs ****************************************************************************************************/

drop function if exists authority.fuzzy_location(text, integer, integer[]) cascade;

create or replace function authority.fuzzy_location(
  p_text text,
  p_limit integer default 10,
  location_type_ids integer[] default null) returns table (
  location_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  , filter_params as (    select location_type_id
    from tbl_location_types
    where array_length(location_type_ids, 1) is null
       or location_type_id = ANY(location_type_ids)
  )  select
    s.location_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.location as s
  cross join params pq  join filter_params using (location_type_id)  where s.norm_label % pq.q      order by name_sim desc, s.label
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_location
 ** What       Semantic search function using pgvector embeddings
 ** Usage      SELECT * FROM authority.semantic_location(qemb::vector, 10);
 ****************************************************************************************************/

drop function if exists authority.semantic_location(vector, integer) cascade;

create or replace function authority.semantic_location(
  qemb vector,
  p_limit integer default 10
) returns table (
  location_id integer,
  label text,
  sem_sim double precision
) language sql stable
as $$
  select
    e.location_id,
    e.label,
    1.0 - (e.emb <=> qemb) as sem_sim
  from authority.location as e
  where e.emb is not null
  order by e.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_location_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ** Arguments
 **            p_text: raw query text
 **            qemb:  query embedding (same dim as stored vectors)
 **            k_trgm: number of trigram results to return (default 30)
 **            k_sem:  number of semantic results to return (default 30)
 **            k_final: number of final results to return (default 20)
 **            alpha:   blending factor for trigram vs semantic (default 0.5) **            location_type_ids: Filter by location type IDs ****************************************************************************************************/
drop function if exists authority.search_location_hybrid(text, vector, integer, integer, integer, double precision, integer[]) cascade;

create or replace function authority.search_location_hybrid(
  p_text text,
  qemb vector,
  k_trgm integer default 30,
  k_sem integer default 30,
  k_final integer default 20,
  alpha double precision default 0.5,
  location_type_ids integer[] default null) returns table (
  location_id integer,
  label text,
  trgm_sim double precision,
  sem_sim double precision,
  blend double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  , filter_params as (    select location_type_id
    from tbl_location_types
    where array_length(location_type_ids, 1) is null
       or location_type_id = ANY(location_type_ids)
  )  , trgm as (
    select
      e.location_id,
      e.label,
      greatest(
        case when e.norm_label = pq.q then 1.0
            else similarity(e.norm_label, pq.q)
        end, 0.0001
      ) as trgm_sim
    from authority.location as e
    cross join params pq    join filter_params using (location_type_id)    where e.norm_label % pq.q          order by trgm_sim desc, e.label
    limit k_trgm
  )
  , sem as (
    select
      e.location_id,
      e.label,
      (1.0 - (e.emb <=> qemb))::double precision as sem_sim
    from authority.location as e    join filter_params using (location_type_id)    where e.emb is not null          order by e.emb <=> qemb
    limit k_sem
  )
  , u as (
    select location_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select location_id, label, null::double precision as trgm_sim, sem_sim from sem
  )
  , agg as (
    select
      location_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim) as sem_sim
    from u
    group by location_id
  )
  select
    location_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim, 0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;