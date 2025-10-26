/**********************************************************************************************
 ** Table  authority.site_embeddings
 ** Note   Embeddings side table for sites in schema authority
 **        Used for semantic search with pgvector
 **        Choose the dimension to match the embedding model (example uses 768).
 **          site_id: the primary key of the site this embedding belongs to
 **          emb: the actual embedding vector, stored as a pgvector vector type
 **          active: a boolean flag indicating whether this embedding is active (useful for soft deletes or temporary deactivations)
 **          updated_at: timestamp when the embedding was last updated
 **          language: optional text field to tag the embedding with a language code
 **        The last three columns are metadata helpers for managing and governing the embeddings.
 **        They’re not required by PostgreSQL or pgvector itself, but they make the architecture
 **        easier to maintain and to debug over time.
 **********************************************************************************************/
drop table if exists authority.site_embeddings;

create tale if not exists authority.site_embeddings(
    site_id integer primary key references public.tbl_sites(site_id) on delete cascade,
emb vector(768), -- embedding vector
language text, -- optional, if you tag rows
active boolean default true, -- optional flag
    updated_at timestamptz default now()
);

-- Vector index for fast ANN search (cosine). Tune LISTS for your row count (start 1 per 1 –2k rows).create index if not exists site_embeddings_ivfflat on authority.site_embeddings using ivfflat(emb vector_cosine_ops
)
with (lists = 100);


/**********************************************************************************************
 **  Site
 **********************************************************************************************/
drop view if exists authority.sites;

create
    or replace materialized view authority.sites as
select
    site_id,
    site_name as label,
    authority.immutable_unaccent(lower(site_name)) as norm_label,
    latitude_dd,
    longitude_dd,
    national_site_identifier,
    site_description,
    st_setsrid(st_makepoint(longitude_dd, latitude_dd), 4326) as geom,
    emb
from
    public.tbl_sites
    left join authority.site_embeddings using(site_id) -- to filter only active sites later if needed
where
    public.tbl_sites.active = true;

create unique index sites_uidx on authority.sites(site_id);

create index if not exists tbl_sites_norm_trgm on public.tbl_sites using gin((authority.immutable_unaccent(lower(site_name))) gin_trgm_ops);

-- Vector search(semantic)
create index sites_search_mv_vec
    on authority.sites
    using ivfflat(emb vector_cosine_ops)
            with (lists = 100);


/***************************************************************************************************
 ** Procedure  authority.fuzzy_sites
 ** What       2) A trigram fuzzy search function (takes TEXT + LIMIT)
 **            This returns top-K by trigram similarity using pg_trgm’s similarity().
 **            Adjust pg_trgm.similarity_threshold if you want to tune sensitivity globally.
 **            You can also set it per-session before calling this function.
 ****************************************************************************************************/
drop function if exists authority.fuzzy_sites(text, integer);

create or replace function authority.fuzzy_sites(p_text text, p_limit integer default 10)
    returns table(
        site_id integer,
        label text,
        name_sim double precision)
    language sql
    stable
    as $$
    with params as(
        select
            authority.immutable_unaccent(lower(p_text))::text as q
)
    select
        s.site_id,
        s.label,
        greatest(
            case when s.norm_label =(
                select
                    q
                from params) then
                1.0
            else
                similarity(s.norm_label,(
                        select
                            q
                        from params))
            end, 0.0001) as name_sim
    from
        authority.sites as s
    where
        s.norm_label %(
            select
                q
            from
                params) -- trigram candidate filter
        order by
            name_sim desc,
            s.label
        limit p_limit;
$$;


/***************************************************************************************************
 ** Procedure  authority.semantic_sites
 ** What       3) A semantic search function (takes TEXT + LIMIT)
 **
 **            This returns top-K by cosine similarity using the query embedding passed in.
 **            Because Postgres itself won’t compute embeddings, we accept the query embedding as
 **            a parameter; your application computes it (via Ollama) and passes it to SQL.
 ****************************************************************************************************/
drop function if exists authority.semantic_sites(vector, integer);

create or replace function authority.semantic_sites(qemb vector, p_limit integer default 10)
    returns table(
        site_id integer,
        label text,
        sem_sim double precision)
    language sql
    stable
    as $$
    select
        s.site_id,
        s.label,
        1.0 -(e.emb <=> qemb) as sem_sim -- cosine similarity in [0,1]
    from
        authority.sites s
        join authority.site_embeddings e using(site_id)
    where
        e.emb is not null
    order by
        e.emb <=> qemb -- ascending distance
    limit p_limit;
$$;


/***************************************************************************************************
 ** Procedure  authority.search_sites_hybrid
 ** What       A hybrid function (trigram + semantic union + blend)
 **            Pulls top-K from both channels, de-dups, blends scores,
 **            and returns a compact list for the LLM (or directly for deterministic reconciliation).
 **            Pass qemb from your app (Ollama embeddings) when calling search_sites_hybrid.
 **            Adjust alpha if you want to favor trigram or semantic differently per domain.
 **            You can add language/active filters by joining authority.site_embeddings
 **            (or extending the authority.sites view with flags) and adding WHERE clauses.
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 ****************************************************************************************************/
drop function if exists authority.search_sites_hybrid(text, vector, integer, integer, integer, double precision);

create or replace function authority.search_sites_hybrid(p_text text, -- raw query text
qemb vector, -- query embedding (same dim as table)
k_trgm integer default 30, k_sem integer default 30, k_final integer default 20, alpha double precision default 0.5 -- weight for trigram vs semantic
)
    returns table(
        site_id integer,
        label text,
        trgm_sim double precision,
        sem_sim double precision,
        blend double precision)
    language sql
    stable
    as $$
    with params as(
        select
            authority.immutable_unaccent(lower(p_text))::text as q
),
-- Trigram top-K
trgm as(
    select
        s.site_id,
        s.label,
        greatest(
            case when s.norm_label =(
                select
                    q
                from params) then
                1.0
            else
                similarity(s.norm_label,(
                        select
                            q
                        from params))
            end, 0.0001) as trgm_sim
    from
        authority.sites s
    where
        s.norm_label %(
            select
                q
            from
                params)
        order by
            trgm_sim desc,
            s.label
        limit k_trgm
),
-- Semantic top-K
sem as(
    select
        s.site_id,
        s.label,
(1.0 -(e.emb <=> qemb))::double precision as sem_sim
    from
        authority.sites s
        join authority.site_embeddings e using(site_id)
    where
        e.emb is not null
    order by
        e.emb <=> qemb
    limit k_sem
),
-- Union + de-dup
u as(
    select
        site_id,
        label,
        trgm_sim,
        null::double precision as sem_sim
    from
        trgm
    union
    select
        site_id,
        label,
        null::double precision as trgm_sim,
        sem_sim
    from
        sem
),
agg as(
    select
        site_id,
        any_value(label) as label,
        max(trgm_sim) as trgm_sim,
        max(sem_sim) as sem_sim
    from
        u
    group by
        site_id
)
select
    site_id,
    label,
    coalesce(trgm_sim, 0.0) as trgm_sim,
    coalesce(sem_sim, 0.0) as sem_sim,
(alpha * coalesce(trgm_sim, 0.0) +(1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
from
    agg
order by
    blend desc,
    label
limit k_final;
$$;

