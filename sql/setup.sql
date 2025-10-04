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

drop function if exists authority.fuzzy_bibliographic_references(text, integer);
create or replace function authority.fuzzy_bibliographic_references(
  p_text         text,
  p_limit        integer default 10,
  p_target_field text    default 'full_reference'
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
  v_query_text text;
  v_column_name text;
  v_sql text;
begin
  if p_target_field not in ('full_reference', 'title', 'authors', 'bugs_reference') then
    raise exception 'Invalid target field %', p_target_field;
  end if;

  v_query_text := authority.immutable_unaccent(lower(p_text));

  v_column_name := case p_target_field
              when 'full_reference'  then 'norm_full_reference'
              when 'title'           then 'norm_title'
              when 'authors'         then 'norm_authors'
              when 'bugs_reference'  then 'norm_bugs_reference'
           end;

  v_sql := format($f$
    select
      s.biblio_id as entity_id,
      s.biblio_id,
      s.label::text,
      greatest(
        case when s.%1$I = $1 then 1.0
             else similarity(s.%1$I, $1)
        end, 0.0001
      )::double precision as name_sim
    from (
        select  
          biblio_id,
          %2$I as label,
          authority.immutable_unaccent(lower(%2$I)) as norm_%2$I
        from public.tbl_biblio
    ) s
    where s.%1$I %% $1       -- trigram candidate filter
    order by name_sim desc, s.label
    limit $2
  $f$, v_column_name, p_target_field);

  return query execute v_sql using v_query_text, p_limit;
end;
$$;
/*
select * from authority.fuzzy_bibliographic_references(
  'Smith', 10, 'full_reference'
);
select *
from tbl_biblio
where unaccent(full_reference) % unaccent('Smith'::text)

select *
from tbl_biblio
where tbl_biblio.full_reference like '%Smith%'
*/
