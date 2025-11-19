/**********************************************************************************************
 ** Table  authority.taxa_tree_genus_embeddings
 ** Note   Embeddings side table for Taxa Genus in schema authority
 **        Used for semantic search with pgvector
 **        Generated from template by generate_entity_schema.py
 **********************************************************************************************/

drop table if exists authority.taxa_tree_genus_embeddings cascade;

create table if not exists authority.taxa_tree_genus_embeddings (
  genus_id integer primary key references public.tbl_taxa_tree_genera(genus_id) on delete cascade,
  emb vector(768)
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
create index if not exists taxa_tree_genus_embeddings_ivfflat
  on authority.taxa_tree_genus_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);
/***************************************************************************************************
 ** Procedure  authority.update_taxa_tree_genus_embeddings
 ** What       Updates embeddings in authority.taxa_tree_genus_embeddings table
 ** Usage      SELECT authority.update_taxa_tree_genus_embeddings();        -- Update only missing
 **            SELECT authority.update_taxa_tree_genus_embeddings(true);    -- Force update all
 ** Arguments  p_force_update: If true, regenerate all embeddings; if false (default), only compute missing ones
 ** Returns    Number of rows updated
 ****************************************************************************************************/
 
drop function if exists authority.update_taxa_tree_genus_embeddings(boolean) cascade;

create or replace function authority.update_taxa_tree_genus_embeddings(
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
  raise notice 'Updating taxa_tree_genus embeddings (force_update: %)', p_force_update;
  
  for rec in
    select t.genus_id,
           t.genus_name    from public.tbl_taxa_tree_genera t
    where p_force_update 
       or not exists (
         select 1 from authority.taxa_tree_genus_embeddings e 
         where e.genus_id = t.genus_id
       )
  loop
    -- Construct text for embedding (combine label and description if available)
    v_text := rec.genus_name;    
    -- Compute embedding (assumes authority.compute_text_embedding exists)
    v_emb := authority.compute_text_embedding(v_text);
    
    -- Upsert into embeddings table
    insert into authority.taxa_tree_genus_embeddings (genus_id, emb)
    values (rec.genus_id, v_emb)
    on conflict (genus_id) do update
      set emb = excluded.emb;
    
    v_rows_updated := v_rows_updated + 1;
    
    -- Progress reporting every 100 rows
    if v_rows_updated % 100 = 0 then
      raise notice '  → Processed % rows', v_rows_updated;
    end if;
  end loop;
  
  raise notice 'Completed: % rows updated for taxa_tree_genus', v_rows_updated;
  return v_rows_updated;
end;
$$;

/**********************************************************************************************
**  Taxa Genus
**********************************************************************************************/
drop view if exists authority.taxa_tree_genus cascade;

create or replace view authority.taxa_tree_genus as  select
    t.genus_id,
    t.genus_name as label,
    authority.immutable_unaccent(lower(t.genus_name)) as norm_label,    t.family_id,    e.emb
  from public.tbl_taxa_tree_genera as t  join public.tbl_taxa_tree_families fam using (family_id)  left join authority.taxa_tree_genus_embeddings as e using (genus_id);
create index if not exists tbl_taxa_tree_genera_norm_trgm
  on public.tbl_taxa_tree_genera
    using gin ( (authority.immutable_unaccent(lower(genus_name))) gin_trgm_ops );
/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_genus
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_genus('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_genus(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_genus(
  p_text text,
  p_limit integer default 10) returns table (
  genus_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.genus_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_genus as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_tree_genus
 ** What       Semantic search function using pgvector embeddings
 ** Usage      SELECT * FROM authority.semantic_taxa_tree_genus(qemb::vector, 10);
 ****************************************************************************************************/

drop function if exists authority.semantic_taxa_tree_genus(vector, integer) cascade;

create or replace function authority.semantic_taxa_tree_genus(
  qemb vector,
  p_limit integer default 10
) returns table (
  genus_id integer,
  label text,
  sem_sim double precision
) language sql stable
as $$
  select
    e.genus_id,
    e.label,
    1.0 - (e.emb <=> qemb) as sem_sim
  from authority.taxa_tree_genus as e
  where e.emb is not null
  order by e.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxa_tree_genus_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ** Arguments
 **            p_text: raw query text
 **            qemb:  query embedding (same dim as stored vectors)
 **            k_trgm: number of trigram results to return (default 30)
 **            k_sem:  number of semantic results to return (default 30)
 **            k_final: number of final results to return (default 20)
 **            alpha:   blending factor for trigram vs semantic (default 0.5) ****************************************************************************************************/
 
drop function if exists authority.search_taxa_tree_genus_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_taxa_tree_genus_hybrid(
  p_text text,
  qemb vector,
  k_trgm integer default 30,
  k_sem integer default 30,
  k_final integer default 20,
  alpha double precision default 0.5) returns table (
  genus_id integer,
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
      e.genus_id,
      e.label,
      greatest(
        case when e.norm_label = pq.q then 1.0
            else similarity(e.norm_label, pq.q)
        end, 0.0001
      ) as trgm_sim
    from authority.taxa_tree_genus as e
    cross join params pq    where e.norm_label % pq.q    order by trgm_sim desc, e.label
    limit k_trgm
  )
  , sem as (
    select
      e.genus_id,
      e.label,
      (1.0 - (e.emb <=> qemb))::double precision as sem_sim
    from authority.taxa_tree_genus as e    where e.emb is not null    order by e.emb <=> qemb
    limit k_sem
  )
  , u as (
    select genus_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select genus_id, label, null::double precision as trgm_sim, sem_sim from sem
  )
  , agg as (
    select
      genus_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim) as sem_sim
    from u
    group by genus_id
  )
  select
    genus_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim, 0.0) as sem_sim,
    (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
  from agg
  order by blend desc, label
  limit k_final;
$$;