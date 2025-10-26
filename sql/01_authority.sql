
create schema if not exists authority;

create extension if not exists unaccent;
create extension if not exists pg_trgm;
create extension if not exists postgis;
create extension if not exists vector; -- apt install -y postgresql-16-pgvector

select version();

-- Immutable wrapper around unaccent using a fixed dictionary
create or replace function authority.immutable_unaccent(p_value text)
returns text language sql immutable parallel safe
as $$
  select unaccent('public.unaccent'::regdictionary, p_value)
$$;

create schema if not exists authority;

-- Immutable wrapper around unaccent using a fixed dictionary
create or replace function authority.immutable_unaccent(p_value text)
returns text language sql immutable parallel safe
as $$
  select unaccent('public.unaccent'::regdictionary, p_value)
$$;


/**********************************************************************************************
**  Location
**********************************************************************************************/

drop view if exists authority.locations;
create or replace view authority.locations as
  select  location_id,
          location_name as label,
          authority.immutable_unaccent(lower(location_name)) as norm_label,
          default_lat_dd as latitude,
          default_long_dd as longitude,
          location_type_id,
          location_type,
          description,
          st_setsrid(st_makepoint(default_long_dd, default_lat_dd), 4326) as geom
  from public.tbl_locations
  join public.tbl_location_types using (location_type_id);

create index if not exists tbl_locations_norm_trgm
  on public.tbl_locations
    using gin ( (authority.immutable_unaccent(lower(location_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_locations(text, integer);
create or replace function authority.fuzzy_locations(
	p_text text,
	p_limit integer default 10,
	variadic location_type_ids integer[] default null)
returns table (
	location_id integer,
	label text,
	name_sim double precision
)
language sql
stable
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
          case when s.norm_label = (select q from params) then 1.0
              else similarity(s.norm_label, (select q from params))
          end, 0.0001
      ) as name_sim
    from authority.locations as s
    join location_types using (location_type_id)
    where s.norm_label % (select q from params)       -- trigram candidate filter
    order by name_sim desc, s.label
    limit p_limit;
$$;


/**********************************************************************************************
**  Feature Type
**********************************************************************************************/

drop view if exists authority.feature_types;
create or replace view authority.feature_types as
  select  feature_type_id,
          feature_type_name as label,
          feature_type_description as description,
          authority.immutable_unaccent(lower(feature_type_name)) as norm_label
  from public.tbl_feature_types;

create index if not exists tbl_feature_types_norm_trgm
  on public.tbl_feature_types
    using gin ( (authority.immutable_unaccent(lower(feature_type_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_feature_types(text, integer);
create or replace function authority.fuzzy_feature_types(
	p_text text,
	p_limit integer default 10
) returns table (
	feature_type_id integer,
	label text,
	name_sim double precision
)
language sql
stable
as $$
  with params as (
        select authority.immutable_unaccent(lower(p_text))::text as q
  )
    select
      s.feature_type_id,
      s.label,
      greatest(
          case when s.norm_label = (select q from params) then 1.0
              else similarity(s.norm_label, (select q from params))
          end, 0.0001
      ) as name_sim
    from authority.feature_types as s
    where s.norm_label % (select q from params)       -- trigram candidate filter
    order by name_sim desc, s.label
    limit p_limit;
$$;
 
 
/**********************************************************************************************
**  Bibliographic Reference
**********************************************************************************************/

drop view if exists authority.bibliographic_references;
create or replace view authority.bibliographic_references as
  select  
    biblio_id,
    full_reference as label,
    bugs_reference,
    doi,
    isbn,
    notes,
    title,
    year,
    authors,
    full_reference,
    url,
    authority.immutable_unaccent(lower(full_reference)) as norm_label,
    authority.immutable_unaccent(lower(bugs_reference)) as norm_bugs_reference,
    authority.immutable_unaccent(lower(title)) as norm_title,
    authority.immutable_unaccent(lower(authors)) as norm_authors

  from public.tbl_biblio
  where full_reference is null
  ;

create index if not exists tbl_bibliographic_references_full_reference_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(full_reference))) gin_trgm_ops );

create index if not exists tbl_bibliographic_references_title_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(title))) gin_trgm_ops );

create index if not exists tbl_bibliographic_references_authors_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(authors))) gin_trgm_ops );

create index if not exists tbl_bibliographic_references_bugs_reference_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(bugs_reference))) gin_trgm_ops );

drop function if exists authority.fuzzy_bibliographic_references(text, integer, text, text, double precision);
drop function if exists authority.fuzzy_bibliographic_references(text, integer, text, text, double precision);

create or replace function authority.fuzzy_bibliographic_references(
  p_text         text,
  p_limit        integer default 10,
  p_target_field text    default 'full_reference',
  p_mode         text    default 'similarity',         -- 'similarity' | 'word' | 'strict_word'
  p_threshold    double precision default null         -- optional per-call operator threshold
) returns table (
  entity_id integer,
  biblio_id integer,
  label     text,
  name_sim  double precision
)
language plpgsql
stable
as $$
declare
  v_q       text;
  v_col     text;
  v_op      text;
  v_score   text;
  v_sql     text;
  v_guc     text;   -- which pg_trgm GUC to SET LOCAL, based on p_mode
begin
  -- validate inputs
  if p_target_field not in ('full_reference','title','authors','bugs_reference') then
    raise exception 'Invalid target field %', p_target_field;
  end if;

  if p_mode not in ('similarity','word','strict_word') then
    raise exception 'Invalid mode % (expected similarity|word|strict_word)', p_mode;
  end if;

  -- normalize query once
  v_q := authority.immutable_unaccent(lower(p_text));

  -- pick normalized column to search
  v_col := case p_target_field
             when 'full_reference' then 'norm_full_reference'
             when 'title'          then 'norm_title'
             when 'authors'        then 'norm_authors'
             when 'bugs_reference' then 'norm_bugs_reference'
           end;

  -- operator, score expression, and which GUC to set
  v_op := case p_mode
             when 'similarity'  then '%'
             when 'word'        then '<%'
             when 'strict_word' then '<<%'
           end;

  v_score := case p_mode
               when 'similarity'  then format('similarity(s.%I, $1)', v_col)
               when 'word'        then format('word_similarity(s.%I, $1)', v_col)
               when 'strict_word' then format('strict_word_similarity(s.%I, $1)', v_col)
             end;

  v_guc := case p_mode
             when 'similarity'  then 'pg_trgm.similarity_threshold'
             when 'word'        then 'pg_trgm.word_similarity_threshold'
             when 'strict_word' then 'pg_trgm.strict_word_similarity_threshold'
           end;

  -- Set a per-call (transaction-local) threshold for the chosen operator, if provided.
  -- This change auto-reverts at transaction end; no manual reset needed.
  if p_threshold is not null then
    execute format('SET LOCAL %s = %L', v_guc, p_threshold);
  end if;

  -- Build one query that uses the chosen operator & score
  v_sql := format($f$
    select
      s.biblio_id as entity_id,
      s.biblio_id,
      s.%2$I::text as label,
      greatest(
        case when s.%1$I = $1 then 1.0
             else %3$s
        end, 0.0001
      )::double precision as name_sim
    from (
      select biblio_id,
             %2$I,
             authority.immutable_unaccent(lower(%2$I)) as norm_%2$I
      from public.tbl_biblio
    ) s
    where s.%1$I %4$s $1       -- operator enforces threshold (uses GUC if set)
    order by name_sim desc, s.%2$I
    limit $2
  $f$, v_col, p_target_field, v_score, v_op);

  -- Execute (2 params if no threshold, 3rd param not used in SQL anymore)
  return query execute v_sql using v_q, p_limit;
end;
$$;

/* Data Type: implemented inline in strategy class for simplicity */

-- drop view if exists authority.data_types;
-- create or replace view authority.data_types as
--   select  data_type_id,
--           data_type_name as label,
--           definition as description,
--           authority.immutable_unaccent(lower(data_type_name)) as norm_label
--   from public.tbl_data_types;

-- create index if not exists tbl_data_types_norm_trgm
--   on public.tbl_data_types
--     using gin ( (authority.immutable_unaccent(lower(data_type_name))) gin_trgm_ops );

-- drop function if exists authority.fuzzy_data_types(text, integer);
-- create or replace function authority.fuzzy_data_types(
-- 	p_text text,
-- 	p_limit integer default 10
-- ) returns table (
-- 	data_type_id integer,
-- 	label text,
-- 	name_sim double precision
-- )
-- language sql
-- stable
-- as $$
--     select
--       s.data_type_id,
--       s.label,
--       greatest(
--           case when s.norm_label = pq.q then 1.0
--               else similarity(s.norm_label, pq.q)
--           end, 0.0001
--       ) as name_sim
--     from authority.feature_types as s
--       cross join (
--       select authority.immutable_unaccent(lower('year'))::text as q
--     ) as pq
--     where s.norm_label % pq.q       -- trigram candidate filter
--     order by name_sim desc, s.label
--     limit p_limit;
-- $$;
 

/**********************************************************************************************
**  Method
**********************************************************************************************/

drop view if exists authority.methods;
create or replace view authority.methods as
  select  method_id,
          method_name as label,
          description,
          authority.immutable_unaccent(lower(method_name)) as norm_label
  from public.tbl_methods;

create index if not exists tbl_methods_norm_trgm
  on public.tbl_methods
    using gin ( (authority.immutable_unaccent(lower(method_name))) gin_trgm_ops );

drop function if exists authority.fuzzy_methods(text, integer);
create or replace function authority.fuzzy_methods(
	p_text text,
	p_limit integer default 10
) returns table (
	method_id integer,
	label text,
	name_sim double precision
)
language sql
stable
as $$
  with params as (
        select authority.immutable_unaccent(lower(p_text))::text as q
  )
    select
      s.method_id,
      s.label,
      greatest(
          case when s.norm_label = (select q from params) then 1.0
              else similarity(s.norm_label, (select q from params))
          end, 0.0001
      ) as name_sim
    from authority.methods as s
    where s.norm_label % (select q from params)
    order by name_sim desc, s.label
    limit p_limit;
$$;

-- call sead_utility.create_full_text_search_materialized_view();

create or replace function authority.fuzzy_find_entity_type_candidates(
	p_text text,
	p_limit integer default 10
) returns table (
	table_name text,
	column_name text,
	value text,
  fts_rank double precision,
  trigram_sim double precision,
  row_score double precision
)
language sql
stable
as $$
    with params as (
      select p_text::text as q,
            websearch_to_tsquery('simple', p_text) as tsq
    ),
    candidates AS (
      select
        sead_utility.table_name_to_entity_name(t.table_name) as entity_name,
        t.table_name,
        t.column_name,
        t.value,
        t.value_norm,
        t.tsv,
        ts_rank_cd(t.tsv, p.tsq)                         AS fts_rank,
        similarity(t.value_norm, p.q)                    AS trigram_sim,
        -- combined row score (FTS dominates if it hits)
        (case when t.tsv @@ p.tsq then 1.0 else 0.0 end) * ts_rank_cd(t.tsv, p.tsq)
          + 0.35 * similarity(t.value_norm, p.q)         as row_score
      from sead_utility.full_text_search t
      cross join params p
      where t.tsv @@ p.tsq or t.value_norm % p.q
    )
    select distinct on (table_name)
      table_name, column_name, value, fts_rank, trigram_sim, row_score
    from candidates
    order by table_name, row_score desc
    limit p_limit;
$$;


commit;
