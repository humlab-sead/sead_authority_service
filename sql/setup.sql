/*
create extension if not exists unaccent;
create extension if not exists pg_trgm;
create extension if not exists postgis;

create schema if not exists authority;
*/
-- Immutable wrapper around unaccent using a fixed dictionary
create or replace function authority.immutable_unaccent(p_value text)
returns text language sql immutable parallel safe
as $$
  select unaccent('public.unaccent'::regdictionary, p_value)
$$;

/**********************************************************************************************
**  Site
**********************************************************************************************/

drop view if exists authority.sites;
create or replace view authority.sites as
  select  site_id,
          site_name as label,
          authority.immutable_unaccent(lower(site_name)) as norm_label,
          latitude_dd,
          longitude_dd,
          national_site_identifier,
          site_description,
          st_setsrid(st_makepoint(longitude_dd, latitude_dd), 4326) as geom
  from public.tbl_sites;

create index if not exists tbl_sites_norm_trgm
  on public.tbl_sites
    using gin ( (authority.immutable_unaccent(lower(site_name))) gin_trgm_ops );


drop function if exists authority.fuzzy_sites(text, integer);
create or replace function authority.fuzzy_sites(p_text text, p_limit integer default 10)
returns table ( site_id integer, label text, name_sim double precision )
language sql
stable
as $$
    with params as (
        select authority.immutable_unaccent(lower(p_text))::text as q
    )
        select
        s.site_id,
        s.label,
        greatest(
            case when s.norm_label = (select q from params) then 1.0
                else similarity(s.norm_label, (select q from params))
            end, 0.0001
        ) as name_sim
        from authority.sites as s
        where s.norm_label % (select q from params)       -- trigram candidate filter
        order by name_sim desc, s.label
        limit p_limit;
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
**  Feature Type
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


-- optional: restore after success (transaction still open)
-- create or replace function authority._restore_pgtrgm_thresholds(prev_sim text, prev_word text, prev_sword text) returns void
-- language plpgsql as $$
-- begin
--   if prev_sim   is not null then perform set_config('pg_trgm.similarity_threshold',            prev_sim,   true); end if;
--   if prev_word  is not null then perform set_config('pg_trgm.word_similarity_threshold',       prev_word,  true); end if;
--   if prev_sword is not null then perform set_config('pg_trgm.strict_word_similarity_threshold',prev_sword, true); end if;
-- end; $$;

/*
select *
from authority.fuzzy_bibliographic_references( 'Smith', 10, 'authors', 'word', null );

select *
from tbl_biblio
where unaccent(full_reference) % unaccent('Smith'::text)

select *
from tbl_biblio
where tbl_biblio.full_reference like '%Smith%'
*/

select *
from tbl_biblio
where bugs_reference is not null
and POSITION(bugs_reference IN full_reference) = 0 