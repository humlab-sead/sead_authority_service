/**********************************************************************************************
 **  Method
 **********************************************************************************************/
/***************************************************************************************************
 ** Table     authority.method_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over methods
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
drop table if exists authority."method_embeddings" cascade;

create table authority."method_embeddings"(
    method_id integer primary key references public.tbl_methods(method_id), -- on delete cascade,
    emb VECTOR(768) not null
);

create index if not exists method_embeddings_ivfflat_idx
  on authority."method_embeddings"
    using ivfflat(emb vector_cosine_ops)
      with (lists = 100);

analyze authority."method_embeddings";

drop view if exists authority."method" cascade;

create or replace view authority."method" as
  select
      m.method_id,
      m.method_name as label,
      m.description,
      authority.immutable_unaccent(lower(m.method_name)) as norm_label,
      e.emb
  from public.tbl_methods m
  left join authority."method_embeddings" e using (method_id);

create index if not exists tbl_methods_norm_trgm
  on public.tbl_methods
    using gin((authority.immutable_unaccent(lower(method_name))) gin_trgm_ops);

drop function if exists authority.fuzzy_method(text, integer) cascade;

create or replace function authority.fuzzy_method(
  p_text text,
  p_limit integer default 10
) returns table (
  method_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
      select authority.immutable_unaccent(lower(p_text))::text as q
  )
    select
        s.method_id,
        s.label,
        greatest(
            case when s.norm_label = pq.q
                then 1.0
                else similarity(s.norm_label, pq.q)
            end, 0.0001
        ) as name_sim
    from authority.method as s
    cross join params pq
    where s.norm_label % pq.q
    order by name_sim desc, s.label
    limit p_limit;
$$;


/***************************************************************************************************
 ** Procedure  authority.semantic_method
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_method(VECTOR, INTEGER) cascade;

create or replace function authority.semantic_method(
  qemb VECTOR,
  p_limit integer default 10
) returns table(
  method_id integer,
  label text,
  sem_sim double precision
)
  language sql stable
as $$
    select m.method_id, m.label, 1.0 - (m.emb <=> qemb) as sem_sim
    from authority.method as m
    where m.emb is not null
    order by m.emb <=> qemb
    limit p_limit;
$$;


/***************************************************************************************************
 ** Procedure  authority.search_method_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/

drop function if exists authority.search_method_hybrid(text, vector, integer, integer, integer, double precision) cascade;

create or replace function authority.search_method_hybrid(
  p_text text,
  qemb vector,
  k_trgm integer default 30,
  k_sem integer default 30,
  k_final integer default 20,
  alpha double precision default 0.5
) returns table (
  method_id integer,
  label text,
  trgm_sim double precision,
  sem_sim double precision,
  blend double precision
) language sql stable
as $$
    with params as (
        select authority.immutable_unaccent(lower(p_text))::text as q
    ),
    trgm as(
        select
            m.method_id,
            m.label,
            greatest(
                case when m.norm_label = pq.q then 1.0
                else similarity(m.norm_label, pq.q)
                end, 0.0001
            ) as trgm_sim
        from authority.method as m
        cross join params pq
        where m.norm_label % pq.q
        order by trgm_sim desc, m.label
        limit k_trgm
    ),
    sem as (
        select m.method_id, m.label, (1.0 -(m.emb <=> qemb))::double precision as sem_sim
        from authority.method as m
        where m.emb is not null
        order by m.emb <=> qemb
        limit k_sem
    ),
    u as (
        select method_id, label, trgm_sim, null::double precision as sem_sim
        from trgm
        union
        select method_id, label, null::double precision as trgm_sim, sem_sim
        from sem
    ),
    agg as (
        select method_id, max(label) as label, max(trgm_sim) as trgm_sim, max(sem_sim) as sem_sim
        from u
        group by method_id
    )
        select
            method_id,
            label,
            coalesce(trgm_sim, 0.0) as trgm_sim,
            coalesce(sem_sim, 0.0) as sem_sim,
            (alpha * coalesce(trgm_sim, 0.0) +(1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
        from agg
        order by blend desc, label
        limit k_final;
$$;
