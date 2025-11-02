/**********************************************************************************************
 ** Table  authority.location_embeddings
 ** Note   Embeddings side table for locations in schema authority
 **        Used for semantic search with pgvector
 **********************************************************************************************/

drop table if exists authority.location_embeddings cascade;

create table if not exists authority.location_embeddings (
  location_id integer primary key references public.tbl_locations(location_id) on delete cascade,
  emb         vector(768)
);

-- Vector index for fast ANN search (cosine). Tune lists to your row count.
create index if not exists location_embeddings_ivfflat
  on authority.location_embeddings
    using ivfflat (emb vector_cosine_ops)
      with (lists = 100);

/**********************************************************************************************
**  Location
**********************************************************************************************/

drop view if exists authority.location;
create or replace view authority.location as
  select  l.location_id,
          l.location_name as label,
          authority.immutable_unaccent(lower(l.location_name)) as norm_label,
          l.default_lat_dd as latitude,
          l.default_long_dd as longitude,
          l.location_type_id,
          lt.location_type,
          lt.description,
          st_setsrid(st_makepoint(l.default_long_dd, l.default_lat_dd), 4326) as geom,
          e.emb
  from public.tbl_locations l
  join public.tbl_location_types lt using (location_type_id)
  left join authority.location_embeddings e using (location_id);

create index if not exists tbl_locations_norm_trgm
  on public.tbl_locations
    using gin ( (authority.immutable_unaccent(lower(location_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_location(text, integer);
create or replace function authority.fuzzy_location(
	p_text text,
	p_limit integer default 10,
	variadic location_type_ids integer[] default null
) returns table (
	location_id integer,
	label text,
	name_sim double precision
) language sql stable
as $$
  with params as (
        select authority.immutable_unaccent(lower(p_text))::text as q
  ), location_types as (
		select location_type_id
		from tbl_location_types
		where array_length(location_type_ids, 1) is null
		 or location_type_id = ANY(location_type_ids)
	)
    select
      s.location_id,
      s.label,
      greatest(
          case when s.norm_label = pq.q then 1.0
              else similarity(s.norm_label, pq.q)
          end, 0.0001
      ) as name_sim
    from authority.location as s
    cross join params pq
    join location_types using (location_type_id)
    where s.norm_label % pq.q       -- trigram candidate filter
    order by name_sim desc, s.label
    limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.semantic_location
 ** What       Semantic search function using pgvector embeddings
 ****************************************************************************************************/
drop function if exists authority.semantic_location(vector, integer);

create or replace function authority.semantic_location(
  qemb vector,
  p_limit integer default 10
) returns table (
  location_id integer,
  label       text,
  sem_sim     double precision
) language sql stable
as $$
  select
    l.location_id,
    l.label,
    1.0 - (l.emb <=> qemb) as sem_sim
  from authority.location as l
  where l.emb is not null
  order by l.emb <=> qemb
  limit p_limit;
$$;

/***************************************************************************************************
 ** Procedure  authority.search_location_hybrid
 ** What       Hybrid search combining trigram and semantic search
 ** Notes      See docs/MCP Server/SEAD Reconciliation via MCP — Architecture Doc (Outline).md
 **            Uses full_reference field for both trigram and semantic matching
 ** Arguments
 **            p_text: raw query text
 **            qemb:  query embedding (same dim as stored vectors)
 **            k_trgm: number of trigram results to return
 **            k_sem:  number of semantic results to return
 **            k_final: number of final results to return
 **            alpha:   blending factor for hybrid search
****************************************************************************************************/
drop function if exists authority.search_location_hybrid(text, vector, integer, integer, integer, double precision, integer[]);

create or replace function authority.search_location_hybrid(
  p_text             text,
  qemb               vector,
  k_trgm             integer default 30,
  k_sem              integer default 30,
  k_final            integer default 20,
  alpha              double precision default 0.5,
  location_type_ids  integer[] default null
) returns table (
  location_id integer,
  label       text,
  trgm_sim    double precision,
  sem_sim     double precision,
  blend       double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  ),
  location_types as (
    select location_type_id
    from tbl_location_types
    where array_length(location_type_ids, 1) is null
      or location_type_id = any(location_type_ids)
  ),
  trgm as (
    select
      l.location_id,
      l.label,
      greatest(
        case when l.norm_label = pq.q then 1.0
            else similarity(l.norm_label, pq.q)
        end,
        0.0001
      ) as trgm_sim
    from authority.location as l
    join location_types using (location_type_id)
    cross join params pq
    where l.norm_label % pq.q
    order by trgm_sim desc, l.label
    limit k_trgm
  ),
  sem as (
    select
      l.location_id,
      l.label,
      (1.0 - (l.emb <=> qemb))::double precision as sem_sim
    from authority.location as l
    join location_types using (location_type_id)
    where l.emb is not null
    order by l.emb <=> qemb
    limit k_sem
  ),
  u as (
    select location_id, label, trgm_sim, null::double precision as sem_sim from trgm
    union
    select location_id, label, null::double precision as trgm_sim, sem_sim from sem
  ),
  agg as (
    select
      location_id,
      max(label) as label,
      max(trgm_sim) as trgm_sim,
      max(sem_sim)  as sem_sim
    from u
    group by location_id
  )
    select
      location_id,
      label,
      coalesce(trgm_sim, 0.0) as trgm_sim,
      coalesce(sem_sim,  0.0) as sem_sim,
      (alpha * coalesce(trgm_sim, 0.0) + (1.0 - alpha) * coalesce(sem_sim, 0.0)) as blend
    from agg
    order by blend desc, label
    limit k_final;
    $$;
