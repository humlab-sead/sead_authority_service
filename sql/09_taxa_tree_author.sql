/**********************************************************************************************
 **  Taxa Tree Authors
 **********************************************************************************************/
/***************************************************************************************************
 ** Table     authority.taxa_tree_author_embeddings
 ** What      Stores 768-dimensional embeddings for semantic search over taxa authors
 ** Notes     Side table pattern: LEFT JOIN to main view, indexed with IVFFLAT
 ****************************************************************************************************/
drop table if exists authority.taxa_tree_author_embeddings cascade;

create table authority.taxa_tree_author_embeddings(
    author_id integer primary key references public.tbl_taxa_tree_authors(author_id) on delete cascade,
    emb VECTOR(768) not null
);

create index if not exists taxa_tree_author_embeddings_ivfflat_idx on authority.taxa_tree_author_embeddings using ivfflat(emb
    vector_cosine_ops) with (lists = 100);

drop view if exists authority.taxa_tree_author cascade;

create or replace view authority.taxa_tree_author as
    select
        a.author_id,
        a.author_name as label,
        authority.immutable_unaccent(lower(a.author_name)) as norm_label,
        e.emb
    from public.tbl_taxa_tree_authors a
    left join authority.taxa_tree_author_embeddings e using (author_id);

create index if not exists tbl_taxa_tree_authors_norm_trgm
    on public.tbl_taxa_tree_authors using
        gin((authority.immutable_unaccent(lower(author_name))) gin_trgm_ops);

drop function if exists authority.fuzzy_taxa_tree_author(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_author(
    p_text text,
    p_limit integer default 10
) returns table (
    author_id integer,
    label text,
    name_sim double precision
) language sql stable
as $$
    with params as(
        select authority.immutable_unaccent(lower(p_text))::text as q
    )
    select
        a.author_id,
        a.label,
        greatest(
            case when a.norm_label = pq.q then 1.0 else similarity(a.norm_label, pq.q) end,
            0.0001
        ) as name_sim
    from authority.taxa_tree_author as a
    cross join params pq
    where a.norm_label % pq.q
    order by name_sim desc, a.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_taxa_tree_author
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_taxa_tree_author(VECTOR, INTEGER);

create or replace function authority.semantic_taxa_tree_author(
    qemb VECTOR,
    p_limit integer default 10
) returns table (
    author_id integer,
    label text,
    sem_sim double precision
) language sql stable
as $$
    select a.author_id, a.label, 1.0 -(a.emb <=> qemb) as sem_sim
    from authority.taxa_tree_author as a
    where a.emb is not null
    order by a.emb <=> qemb
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_taxa_tree_author_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
drop function if exists authority.search_taxa_tree_author_hybrid(TEXT, VECTOR, INTEGER, INTEGER, INTEGER, DOUBLE PRECISION);

create or replace function authority.search_taxa_tree_author_hybrid(
    p_text text,
    qemb VECTOR,
    k_trgm integer default 30,
    k_sem integer default 30,
    k_final integer default 20,
    alpha double precision default 0.5
) returns table (
    author_id integer,
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
            a.author_id,
            a.label,
            greatest(
                case when a.norm_label = pq.q then 1.0 else similarity(a.norm_label, pq.q) end,
                0.0001
            ) as trgm_sim
        from authority.taxa_tree_author as a
        cross join params pq
        where a.norm_label % pq.q
        order by trgm_sim desc, a.label
        limit k_trgm
    ),
    sem as(
        select a.author_id, a.label, (1.0 -(a.emb <=> qemb))::double precision as sem_sim
        from authority.taxa_tree_author as a
        where a.emb is not null
        order by a.emb <=> qemb
        limit k_sem
    ),
    u as(
        select author_id, label, trgm_sim, null::double precision as sem_sim
        from trgm
        union
        select author_id, label, null::double precision as trgm_sim, sem_sim
        from sem
    ),
    agg as (
        select author_id, max(label) as label, max(trgm_sim) as trgm_sim, max(sem_sim) as sem_sim
        from u
        group by author_id
    )
        select
            author_id,
            label,
            coalesce(trgm_sim, 0.0) as trgm_sim,
            coalesce(sem_sim, 0.0) as sem_sim,
            (alpha * coalesce(trgm_sim, 0.0) +(1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
        from agg
        order by blend desc, label
        limit k_final;
$$;
