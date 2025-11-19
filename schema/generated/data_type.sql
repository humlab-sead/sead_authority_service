/**********************************************************************************************
 ** Table  authority.data_type_embeddings
 ** Note   Embeddings side table for Data Type in schema authority
 **        Used for semantic search with pgvector
 **        Generated from template by generate_entity_schema.py
 **********************************************************************************************/

drop table if exists authority.data_type_embeddings cascade;

create table if not exists authority.data_type_embeddings (
  data_type_id integer primary key references public.tbl_data_types(data_type_id) on delete cascade,
  emb vector(768)
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
create index if not exists data_type_embeddings_ivfflat
  on authority.data_type_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);
/***************************************************************************************************
 ** Procedure  authority.update_data_type_embeddings
 ** What       Updates embeddings in authority.data_type_embeddings table
 ** Usage      SELECT authority.update_data_type_embeddings();        -- Update only missing
 **            SELECT authority.update_data_type_embeddings(true);    -- Force update all
 ** Arguments  p_force_update: If true, regenerate all embeddings; if false (default), only compute missing ones
 ** Returns    Number of rows updated
 ****************************************************************************************************/
 
drop function if exists authority.update_data_type_embeddings(boolean) cascade;

create or replace function authority.update_data_type_embeddings(
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
  raise notice 'Updating data_type embeddings (force_update: %)', p_force_update;
  
  for rec in
    select t.data_type_id,
           t.data_type_name,
           t.definition    from public.tbl_data_types t
    where p_force_update 
       or not exists (
         select 1 from authority.data_type_embeddings e 
         where e.data_type_id = t.data_type_id
       )
  loop
    -- Construct text for embedding (combine label and description if available)
    v_text := rec.data_type_name;    if rec.definition is not null then
      v_text := v_text || ' ' || rec.definition;
    end if;    
    -- Compute embedding (assumes authority.compute_text_embedding exists)
    v_emb := authority.compute_text_embedding(v_text);
    
    -- Upsert into embeddings table
    insert into authority.data_type_embeddings (data_type_id, emb)
    values (rec.data_type_id, v_emb)
    on conflict (data_type_id) do update
      set emb = excluded.emb;
    
    v_rows_updated := v_rows_updated + 1;
    
    -- Progress reporting every 100 rows
    if v_rows_updated % 100 = 0 then
      raise notice '  → Processed % rows', v_rows_updated;
    end if;
  end loop;
  
  raise notice 'Completed: % rows updated for data_type', v_rows_updated;
  return v_rows_updated;
end;
$$;

/**********************************************************************************************
**  Data Type
**********************************************************************************************/
drop view if exists authority.data_type cascade;

create or replace view authority.data_type as  select
    t.data_type_id,
    t.data_type_name as label,
    authority.immutable_unaccent(lower(t.data_type_name)) as norm_label,    t.definition,    e.emb
  from public.tbl_data_types as t  left join authority.data_type_embeddings as e using (data_type_id);
create index if not exists tbl_data_types_norm_trgm
  on public.tbl_data_types
    using gin ( (authority.immutable_unaccent(lower(data_type_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_data_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_data_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_data_type(text, integer) cascade;

create or replace function authority.fuzzy_data_type(
  p_text text,
  p_limit integer default 10) returns table (
  data_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.data_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.data_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_data_type
 ** What       Semantic search function using pgvector embeddings
 ** Usage      SELECT * FROM authority.semantic_data_type(qemb::vector, 10);
 ****************************************************************************************************/

drop function if exists authority.semantic_data_type(vector, integer) cascade;

create or replace function authority.semantic_data_type(
  qemb vector,
  p_limit integer default 10
) returns table (
  data_type_id integer,
  label text,
  sem_sim double precision
) language sql stable
as $$
  select
    e.data_type_id,
    e.label,
    1.0 - (e.emb <=> qemb) as sem_sim
  from authority.data_type as e
  where e.emb is not null
  order by e.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_data_type_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ** Arguments
 **            p_text: raw query text
 **            qemb:  query embedding (same dim as stored vectors)
 **            k_trgm: number of trigram results to return (default 30)
 **            k_sem:  number of semantic results to return (default 30)
 **            k_final: number of final results to return (default 20)
 **            alpha:   blending factor for trigram vs semantic (default 0.5) ****************************************************************************************************/
 
drop function if exists authority.search_data_type_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_data_type_hybrid(
  p_text text,
  qemb vector,
  k_trgm integer default 30,
  k_sem integer default 30,
  k_final integer default 20,
  alpha double precision default 0.5) returns table (
  data_type_id integer,
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
      e.data_type_id,
      e.label,
      greatest(
        case when e.norm_label = pq.q then 1.0
            else similarity(e.norm_label, pq.q)
        end, 0.0001
      ) as trgm_sim
    from authority.data_type as e
    cross join params pq    where e.norm_label % pq.q    order by trgm_sim desc, e.label
    limit k_trgm
  )
  , sem as (
    select
      e.data_type_id,
      e.label,
      (1.0 - (e.emb <=> qemb))::double precision as sem_sim
    from authority.data_type as e    where e.emb is not null    order by e.emb <=> qemb
    limit k_sem
  )
  , u as (
    select data_type_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select data_type_id, label, null::double precision as trgm_sim, sem_sim from sem
  )
  , agg as (
    select
      data_type_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim) as sem_sim
    from u
    group by data_type_id
  )
  select
    data_type_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim, 0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;