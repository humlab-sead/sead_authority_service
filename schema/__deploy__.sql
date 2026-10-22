-- SEAD Authority Service Database Schema

-- Generated automatically by create_schema.sh

\set quiet on
\set echo none
\set verbosity terse

set client_min_messages = warning;

begin;

-- Core authority schema objects


drop schema if exists authority cascade;

create schema if not exists authority;

create extension if not exists unaccent;
create extension if not exists pg_trgm;
create extension if not exists postgis;

select version();

/***************************************************************************************************
 ** Function  authority.snake_to_title
 ** What      Converts snake_case strings to Title Case (e.g., 'zyz_abc' -> 'Zyz Abc')
 ** Usage     SELECT authority.snake_to_title('method_group');  -- Returns 'Method Group'
 **           SELECT authority.snake_to_title('taxa_tree_master');  -- Returns 'Taxa Tree Master'
 ****************************************************************************************************/

drop function if exists authority.snake_to_title(text);

create or replace function authority.snake_to_title(input_text text)
returns text language sql immutable strict
as $$
  select string_agg(initcap(word), ' ')
  from unnest(string_to_array(input_text, '_')) as word
$$;
-- Immutable wrapper around unaccent using a fixed dictionary
create or replace function authority.immutable_unaccent(p_value text)
returns text language sql immutable parallel safe
as $$
  select unaccent('public.unaccent'::regdictionary, p_value)
$$;


-- call sead_utility.create_full_text_search_materialized_view()
create or replace procedure sead_utility.create_full_text_search_materialized_view()
  as $udf$
  declare
  v_sql text;
  begin
  -- Optional: ensure unaccent is available
  -- EXECUTE 'CREATE EXTENSION IF NOT EXISTS unaccent';

  drop materialized view if exists sead_utility.full_text_search cascade;

  with sead_tables ("table_name", "pk_name") as (
      select "table_name", "column_name" as pk_name
      from sead_utility.table_columns
      where is_pk = 'YES'
  ),
  lookup_columns("table_name", "column_name", "column_type") as (values
    ('tbl_sample_group_sampling_contexts', 'sampling_context', 'description'),
    ('tbl_sample_description_types', 'type_description', 'description'),
    ('tbl_value_types', 'base_type', 'label'),
    ('tbl_dating_labs', 'international_lab_id', 'label'),
    ('tbl_seasons', 'season_name', 'label'),
    ('tbl_data_type_groups', 'data_type_group_name', 'label'),
    ('tbl_taxa_tree_authors', 'author_name', 'label'),
    ('tbl_dataset_submission_types', 'description', 'description'),
    ('tbl_ceramics_lookup', 'description', 'description'),
    ('tbl_location_types', 'location_type', 'label'),
    ('tbl_data_type_groups', 'description', 'description'),
    ('tbl_project_types', 'project_type_name', 'label'),
    ('tbl_value_classes', 'name', 'label'),
    ('tbl_method_groups', 'description', 'description'),
    ('tbl_value_type_items', 'description', 'description'),
    ('tbl_years_types', 'description', 'description'),
    ('tbl_contact_types', 'contact_type_name', 'label'),
    ('tbl_taxa_common_names', 'common_name', 'label'),
    ('tbl_relative_ages', 'relative_age_name', 'label'),
    ('tbl_sample_types', 'description', 'description'),
    ('tbl_taxa_tree_orders', 'order_name', 'label'),
    ('tbl_locations', 'location_name', 'label'),
    ('tbl_sample_group_description_types', 'type_description', 'description'),
    ('tbl_value_classes', 'description', 'description'),
    ('tbl_age_types', 'description', 'description'),
    ('tbl_taxonomic_order_systems', 'system_name', 'label'),
    ('tbl_text_identification_keys', 'key_text', 'description'),
    ('tbl_feature_types', 'feature_type_description', 'description'),
    ('tbl_dating_uncertainty', 'description', 'description'),
    ('tbl_sample_group_sampling_contexts', 'description', 'description'),
    ('tbl_taxa_tree_genera', 'genus_name', 'label'),
    ('tbl_sample_location_types', 'location_type_description', 'description'),
    ('tbl_rdb_codes', 'rdb_category', 'label'),
    ('tbl_record_types', 'record_type_description', 'description'),
    ('tbl_value_types', 'name', 'label'),
    ('tbl_taxa_tree_families', 'family_name', 'label'),
    ('tbl_project_stages', 'description', 'description'),
    ('tbl_sample_types', 'type_name', 'label'),
    ('tbl_rdb_systems', 'rdb_version', 'label'),
    ('tbl_units', 'unit_name', 'label'),
    ('tbl_relative_age_types', 'description', 'description'),
    ('tbl_activity_types', 'description', 'description'),
    ('tbl_dimensions', 'dimension_description', 'description'),
    ('tbl_dimensions', 'dimension_abbrev', 'abbreviation'),
    ('tbl_dating_labs', 'lab_name', 'label'),
    ('tbl_location_types', 'description', 'description'),
    ('tbl_ceramics_lookup', 'name', 'label'),
    ('tbl_relative_ages', 'abbreviation', 'abbreviation'),
    ('tbl_value_qualifiers', 'symbol', 'abbreviation'),
    ('tbl_taxonomic_order_systems', 'system_description', 'description'),
    ('tbl_value_qualifier_symbols', 'symbol', 'abbreviation'),
    ('tbl_taxa_tree_master', 'species', 'label'),
    ('tbl_relative_ages', 'description', 'description'),
    ('tbl_feature_types', 'feature_type_name', 'label'),
    ('tbl_alt_ref_types', 'alt_ref_type', 'label'),
    ('tbl_modification_types', 'modification_type_name', 'label'),
    ('tbl_alt_ref_types', 'description', 'description'),
    ('tbl_data_types', 'definition', 'description'),
    ('tbl_identification_levels', 'identification_level_name', 'label'),
    ('tbl_abundance_elements', 'element_name', 'label'),
    ('tbl_dating_uncertainty', 'uncertainty', 'label'),
    ('tbl_languages', 'language_name_english', 'label'),
    ('tbl_method_groups', 'group_name', 'label'),
    ('tbl_record_types', 'record_type_name', 'label'),
    ('tbl_age_types', 'age_type', 'label'),
    ('tbl_units', 'unit_abbrev', 'abbreviation'),
    ('tbl_modification_types', 'modification_type_description', 'description'),
    ('tbl_years_types', 'name', 'label'),
    ('tbl_methods', 'description', 'description'),
    ('tbl_season_types', 'description', 'description'),
    ('tbl_languages', 'language_name_native', 'label'),
    ('tbl_dataset_submission_types', 'submission_type', 'label'),
    ('tbl_identification_levels', 'notes', 'description'),
    ('tbl_project_types', 'description', 'description'),
    ('tbl_value_types', 'description', 'description'),
    ('tbl_species_association_types', 'association_type_name', 'label'),
    ('tbl_rdb_systems', 'rdb_system', 'label'),
    ('tbl_value_type_items', 'name', 'label'),
    ('tbl_units', 'description', 'description'),
    ('tbl_value_qualifiers', 'description', 'description'),
    ('tbl_species_association_types', 'association_description', 'description'),
    ('tbl_dimensions', 'dimension_name', 'label'),
    ('tbl_methods', 'method_name', 'label'),
    ('tbl_season_types', 'season_type', 'label'),
    ('tbl_abundance_elements', 'element_description', 'description'),
    ('tbl_project_stages', 'stage_name', 'label'),
    ('tbl_sample_location_types', 'location_type', 'label'),
    ('tbl_sample_group_description_types', 'type_name', 'label'),
    ('tbl_activity_types', 'activity_type', 'label'),
    ('tbl_contact_types', 'description', 'description'),
    ('tbl_data_types', 'data_type_name', 'label'),
    ('tbl_rdb_codes', 'rdb_definition', 'description'),
    ('tbl_relative_age_types', 'age_type', 'label'),
    ('tbl_methods', 'method_abbrev_or_alt_name', 'label'),
    ('tbl_sample_description_types', 'type_name', 'label')
  ),
  column_sql AS (
      SELECT format(
		  'select %1$L AS table_name,
				  %2$L AS column_name,
				  %3$I::text AS system_id,
				  %2$I::text AS value,
				  ''%4$s''::text as "column_type",
				  authority.immutable_unaccent(lower(%2$I::text))::text AS value_norm,
          -- weight columns: names > abbreviations > descriptions
          case ''%4$s''
            when ''label''        then setweight(to_tsvector(''simple'', authority.immutable_unaccent(%2$I)), ''a'')
            when ''abbreviation'' then setweight(to_tsvector(''simple'', authority.immutable_unaccent(%2$I)), ''b'')
            else                     setweight(to_tsvector(''simple'', authority.immutable_unaccent(%2$I)), ''c'')
          end as tsv
			from %1$I
			where %2$I is not null', "table_name", "column_name", "pk_name", "column_type") AS column_sql
      from lookup_columns
      join sead_tables using (table_name)
  )
  select 'create materialized view sead_utility.full_text_search as ' || chr(10) ||
          string_agg(column_sql, e'\nunion\n')
  into v_sql
  from column_sql;
  --raise info '%', v_sql;
  execute v_sql;
  -- gin index on the precomputed tsv column -> useful for fuzzy full text search

  v_sql := 'create index idx_full_text_search_tsv
      on sead_utility.full_text_search
        using gin (tsv)';

  execute v_sql;

  -- Also gin_trgm_ops index on the value column for fast trigram similarity/semantic searches
  -- requires pg_trgm extension
  -- Use ts_toquery() for boolean AND/OR/NOT searches
  -- Use plainto_tsquery() for simple AND searches
  -- Use phraseto_tsquery() for phrase searches
  -- Use websearch_to_tsquery() for Google-like searches

  v_sql := 'create index idx_full_text_search_value_trgm
    on sead_utility.full_text_search
      using gin (authority.immutable_unaccent(value) gin_trgm_ops)';

  execute v_sql;

  end;
  $udf$ language plpgsql;
  
CREATE OR REPLACE FUNCTION sead_utility.singularize_en(
	word text)
    RETURNS text
    LANGUAGE plpgsql
    COST 100
    IMMUTABLE STRICT PARALLEL UNSAFE
AS $BODY$
declare
  w text := lower(word);
begin
  -- hard exceptions (extend if needed)
  if w in ('species','series','news') then
    return w; -- unchanged singular/plural
  end if;
  -- don't touch words ending in -us or -ss (status, genus, class)
  if w ~ '(us|ss)$' then
    return w;
  end if;
  -- families -> family  (consonant + ies)
  if w ~ '[^aeiou]ies$' then
    return regexp_replace(w, 'ies$', 'y');
  end if;
  -- classes/boxes/churches/dishes/oes -> class/box/church/dish/o
  if w ~ '(xes|ches|shes|sses|zes|oes)$' then
    return regexp_replace(w, '(xes|ches|shes|sses|zes|oes)$', 
      case
        when w ~ 'xes$'   then 'x'
        when w ~ 'ches$'  then 'ch'
        when w ~ 'shes$'  then 'sh'
        when w ~ 'sses$'  then 'ss'
        when w ~ 'zes$'   then 'z'
        when w ~ 'oes$'   then 'o'
      end);
  end if;
  -- knives/leaves -> knife/leaf (common -ves rule)
  if w ~ '([aeioulf])ves$' then
    -- crude but useful: shelves -> shelf; leaves -> leaf; knives -> knif(e) → knife
    if w ~ '(?:[^f])ves$' then
      return regexp_replace(w, 'ves$', 'f');     -- leaves→leaf, shelves→shelf
    else
      return regexp_replace(w, 'ves$', 'fe');    -- knives→knife
    end if;
  end if;
  -- genera -> genus
  if w = 'genera' then
    return 'genus';
  end if;
  -- generic trailing -s
  if right(w,1) = 's' then
    return left(w, length(w)-1);
  end if;
  return w;
end;
$BODY$;

ALTER FUNCTION sead_utility.singularize_en(word text)
    OWNER TO humlab_admin;

-- MOVE TO SEAD Change Control System (utility project)
CREATE OR REPLACE FUNCTION sead_utility.table_name_to_entity_name(
	p_tablename text)
    RETURNS text
    LANGUAGE plpgsql
    COST 100
    IMMUTABLE STRICT PARALLEL UNSAFE
AS $BODY$
declare
  base   text;         -- without tbl_ prefix
  parts  text[];       -- split on _
  last   text;         -- last token to singularize
  result text;
begin
  base  := regexp_replace(lower(p_tablename), '^tbl_', '');
  parts := string_to_array(base, '_');
  if parts is null or array_length(parts,1) is null then
    return base;
  end if;
  last := parts[array_length(parts,1)];
  parts[array_length(parts,1)] := sead_utility.singularize_en(last);
  result := array_to_string(parts, '_');
  return result;
end;
$BODY$;

ALTER FUNCTION sead_utility.table_name_to_entity_name(p_tablename text)
    OWNER TO humlab_admin;
/**********************************************************************************************
**  Bibliographic Reference - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.bibliographic_reference cascade;

create or replace view authority.bibliographic_reference as
  select
    t.biblio_id,
    t.full_reference as label,
    authority.immutable_unaccent(lower(t.full_reference)) as norm_label,
    t.title,
    t.doi,
    t.bugs_reference,
    t.isbn,
    t.notes,
    t.year,
    t.authors,
    t.url,
    authority.immutable_unaccent(lower(t.bugs_reference)) as norm_bugs_reference,
    authority.immutable_unaccent(lower(t.title)) as norm_title,
    authority.immutable_unaccent(lower(t.authors)) as norm_authors  from public.tbl_biblio as t;

create index if not exists tbl_biblio_norm_trgm
  on public.tbl_biblio
    using gin ( (authority.immutable_unaccent(lower(full_reference))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_bibliographic_reference
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_bibliographic_reference('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_bibliographic_reference(text, integer) cascade;

create or replace function authority.fuzzy_bibliographic_reference(
  p_text text,
  p_limit integer default 10) returns table (
  biblio_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.biblio_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.bibliographic_reference as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Data Type Group - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.data_type_group cascade;

create or replace view authority.data_type_group as
  select
    t.data_type_group_id,
    t.data_type_group_name as label,
    authority.immutable_unaccent(lower(t.data_type_group_name)) as norm_label,
    t.description  from public.tbl_data_type_groups as t;

create index if not exists tbl_data_type_groups_norm_trgm
  on public.tbl_data_type_groups
    using gin ( (authority.immutable_unaccent(lower(data_type_group_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_data_type_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_data_type_group('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_data_type_group(text, integer) cascade;

create or replace function authority.fuzzy_data_type_group(
  p_text text,
  p_limit integer default 10) returns table (
  data_type_group_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.data_type_group_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.data_type_group as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Data Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.data_type cascade;

create or replace view authority.data_type as
  select
    t.data_type_id,
    t.data_type_name as label,
    authority.immutable_unaccent(lower(t.data_type_name)) as norm_label,
    t.definition  from public.tbl_data_types as t;

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

/**********************************************************************************************
**  Dating Uncertainty - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.dating_uncertainty cascade;

create or replace view authority.dating_uncertainty as
  select
    t.dating_uncertainty_id,
    t.uncertainty as label,
    authority.immutable_unaccent(lower(t.uncertainty)) as norm_label,
    t.description  from public.tbl_dating_uncertainty as t;

create index if not exists tbl_dating_uncertainty_norm_trgm
  on public.tbl_dating_uncertainty
    using gin ( (authority.immutable_unaccent(lower(uncertainty))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_dating_uncertainty
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_dating_uncertainty('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_dating_uncertainty(text, integer) cascade;

create or replace function authority.fuzzy_dating_uncertainty(
  p_text text,
  p_limit integer default 10) returns table (
  dating_uncertainty_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.dating_uncertainty_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.dating_uncertainty as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Feature - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.feature cascade;

create or replace view authority.feature as
  select
    t.feature_id,
    t.feature_name as label,
    authority.immutable_unaccent(lower(t.feature_name)) as norm_label,
    t.feature_description  from public.tbl_features as t;

create index if not exists tbl_features_norm_trgm
  on public.tbl_features
    using gin ( (authority.immutable_unaccent(lower(feature_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_feature
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_feature('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_feature(text, integer) cascade;

create or replace function authority.fuzzy_feature(
  p_text text,
  p_limit integer default 10) returns table (
  feature_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.feature_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.feature as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Feature Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.feature_type cascade;

create or replace view authority.feature_type as
  select
    t.feature_type_id,
    t.feature_type_name as label,
    authority.immutable_unaccent(lower(t.feature_type_name)) as norm_label,
    t.feature_type_description  from public.tbl_feature_types as t;

create index if not exists tbl_feature_types_norm_trgm
  on public.tbl_feature_types
    using gin ( (authority.immutable_unaccent(lower(feature_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_feature_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_feature_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_feature_type(text, integer) cascade;

create or replace function authority.fuzzy_feature_type(
  p_text text,
  p_limit integer default 10) returns table (
  feature_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.feature_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.feature_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Location - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.location cascade;

create or replace view authority.location as
  select
    t.location_id,
    t.location_name as label,
    authority.immutable_unaccent(lower(t.location_name)) as norm_label,
    t.default_lat_dd as latitude,
    t.default_long_dd as longitude,
    t.location_type_id,
    lt.location_type,
    st_setsrid(st_makepoint(t.default_long_dd, t.default_lat_dd), 4326) as geom  from public.tbl_locations as t  join public.tbl_location_types lt using (location_type_id);

create index if not exists tbl_locations_norm_trgm
  on public.tbl_locations
    using gin ( (authority.immutable_unaccent(lower(location_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_location
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_location('query text', 10); ** Params     location_type_ids: Filter by location type IDs
 ****************************************************************************************************/

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

/**********************************************************************************************
**  Location Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.location_type cascade;

create or replace view authority.location_type as
  select
    t.location_type_id,
    t.location_type as label,
    authority.immutable_unaccent(lower(t.location_type)) as norm_label,
    t.description  from public.tbl_location_types as t;

create index if not exists tbl_location_types_norm_trgm
  on public.tbl_location_types
    using gin ( (authority.immutable_unaccent(lower(location_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_location_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_location_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_location_type(text, integer) cascade;

create or replace function authority.fuzzy_location_type(
  p_text text,
  p_limit integer default 10) returns table (
  location_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.location_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.location_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Method Group - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.method_group cascade;

create or replace view authority.method_group as
  select
    t.method_group_id,
    t.group_name as label,
    authority.immutable_unaccent(lower(t.group_name)) as norm_label,
    t.description  from public.tbl_method_groups as t;

create index if not exists tbl_method_groups_norm_trgm
  on public.tbl_method_groups
    using gin ( (authority.immutable_unaccent(lower(group_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_method_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_method_group('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_method_group(text, integer) cascade;

create or replace function authority.fuzzy_method_group(
  p_text text,
  p_limit integer default 10) returns table (
  method_group_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.method_group_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.method_group as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Method - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.method cascade;

create or replace view authority.method as
  select
    t.method_id,
    t.method_name as label,
    authority.immutable_unaccent(lower(t.method_name)) as norm_label,
    t.description,
    t.method_abbrev_or_alt_name  from public.tbl_methods as t;

create index if not exists tbl_methods_norm_trgm
  on public.tbl_methods
    using gin ( (authority.immutable_unaccent(lower(method_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_method
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_method('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_method(text, integer) cascade;

create or replace function authority.fuzzy_method(
  p_text text,
  p_limit integer default 10) returns table (
  method_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.method_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.method as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Modification Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.modification_type cascade;

create or replace view authority.modification_type as
  select
    t.modification_type_id,
    t.modification_type_name as label,
    authority.immutable_unaccent(lower(t.modification_type_name)) as norm_label,
    t.modification_type_description  from public.tbl_modification_types as t;

create index if not exists tbl_modification_types_norm_trgm
  on public.tbl_modification_types
    using gin ( (authority.immutable_unaccent(lower(modification_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_modification_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_modification_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_modification_type(text, integer) cascade;

create or replace function authority.fuzzy_modification_type(
  p_text text,
  p_limit integer default 10) returns table (
  modification_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.modification_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.modification_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Record Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.record_type cascade;

create or replace view authority.record_type as
  select
    t.record_type_id,
    t.record_type_name as label,
    authority.immutable_unaccent(lower(t.record_type_name)) as norm_label,
    t.record_type_description  from public.tbl_record_types as t;

create index if not exists tbl_record_types_norm_trgm
  on public.tbl_record_types
    using gin ( (authority.immutable_unaccent(lower(record_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_record_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_record_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_record_type(text, integer) cascade;

create or replace function authority.fuzzy_record_type(
  p_text text,
  p_limit integer default 10) returns table (
  record_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.record_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.record_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Relative Age - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.relative_age cascade;

create or replace view authority.relative_age as
  select
    t.relative_age_id,
    t.relative_age_name as label,
    authority.immutable_unaccent(lower(t.relative_age_name)) as norm_label,
    t.description  from public.tbl_relative_ages as t;

create index if not exists tbl_relative_ages_norm_trgm
  on public.tbl_relative_ages
    using gin ( (authority.immutable_unaccent(lower(relative_age_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_relative_age
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_relative_age('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_relative_age(text, integer) cascade;

create or replace function authority.fuzzy_relative_age(
  p_text text,
  p_limit integer default 10) returns table (
  relative_age_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.relative_age_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.relative_age as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Relative Age Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.relative_age_type cascade;

create or replace view authority.relative_age_type as
  select
    t.relative_age_type_id,
    t.age_type as label,
    authority.immutable_unaccent(lower(t.age_type)) as norm_label,
    t.description  from public.tbl_relative_age_types as t;

create index if not exists tbl_relative_age_types_norm_trgm
  on public.tbl_relative_age_types
    using gin ( (authority.immutable_unaccent(lower(age_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_relative_age_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_relative_age_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_relative_age_type(text, integer) cascade;

create or replace function authority.fuzzy_relative_age_type(
  p_text text,
  p_limit integer default 10) returns table (
  relative_age_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.relative_age_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.relative_age_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Sample Description Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.sample_description_type cascade;

create or replace view authority.sample_description_type as
  select
    t.sample_description_type_id,
    t.type_name as label,
    authority.immutable_unaccent(lower(t.type_name)) as norm_label,
    t.type_description  from public.tbl_sample_description_types as t;

create index if not exists tbl_sample_description_types_norm_trgm
  on public.tbl_sample_description_types
    using gin ( (authority.immutable_unaccent(lower(type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_description_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_description_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_description_type(text, integer) cascade;

create or replace function authority.fuzzy_sample_description_type(
  p_text text,
  p_limit integer default 10) returns table (
  sample_description_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.sample_description_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_description_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Sample Group Description Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.sample_group_description_type cascade;

create or replace view authority.sample_group_description_type as
  select
    t.sample_group_description_type_id,
    t.type_name as label,
    authority.immutable_unaccent(lower(t.type_name)) as norm_label,
    t.type_description  from public.tbl_sample_group_description_types as t;

create index if not exists tbl_sample_group_description_types_norm_trgm
  on public.tbl_sample_group_description_types
    using gin ( (authority.immutable_unaccent(lower(type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_group_description_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_group_description_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_group_description_type(text, integer) cascade;

create or replace function authority.fuzzy_sample_group_description_type(
  p_text text,
  p_limit integer default 10) returns table (
  sample_group_description_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.sample_group_description_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_group_description_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Sample Location Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.sample_location_type cascade;

create or replace view authority.sample_location_type as
  select
    t.sample_location_type_id,
    t.location_type as label,
    authority.immutable_unaccent(lower(t.location_type)) as norm_label,
    t.location_type_description  from public.tbl_sample_location_types as t;

create index if not exists tbl_sample_location_types_norm_trgm
  on public.tbl_sample_location_types
    using gin ( (authority.immutable_unaccent(lower(location_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_location_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_location_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_location_type(text, integer) cascade;

create or replace function authority.fuzzy_sample_location_type(
  p_text text,
  p_limit integer default 10) returns table (
  sample_location_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.sample_location_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_location_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Sample Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.sample_type cascade;

create or replace view authority.sample_type as
  select
    t.sample_type_id,
    t.type_name as label,
    authority.immutable_unaccent(lower(t.type_name)) as norm_label,
    t.description  from public.tbl_sample_types as t;

create index if not exists tbl_sample_types_norm_trgm
  on public.tbl_sample_types
    using gin ( (authority.immutable_unaccent(lower(type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_type(text, integer) cascade;

create or replace function authority.fuzzy_sample_type(
  p_text text,
  p_limit integer default 10) returns table (
  sample_type_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.sample_type_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_type as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Sampling Context - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.sampling_context cascade;

create or replace view authority.sampling_context as
  select
    t.sampling_context_id,
    t.sampling_context as label,
    authority.immutable_unaccent(lower(t.sampling_context)) as norm_label,
    t.description  from public.tbl_sample_group_sampling_contexts as t;

create index if not exists tbl_sample_group_sampling_contexts_norm_trgm
  on public.tbl_sample_group_sampling_contexts
    using gin ( (authority.immutable_unaccent(lower(sampling_context))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sampling_context
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sampling_context('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sampling_context(text, integer) cascade;

create or replace function authority.fuzzy_sampling_context(
  p_text text,
  p_limit integer default 10) returns table (
  sampling_context_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.sampling_context_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sampling_context as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Site - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop materialized view if exists authority.site cascade;

create materialized view authority.site as
  select
    t.site_id,
    t.site_name as label,
    authority.immutable_unaccent(lower(t.site_name)) as norm_label,
    t.site_description,
    t.national_site_identifier,
    t.latitude_dd,
    t.longitude_dd,
    ST_SetSRID(ST_MakePoint(t.longitude_dd, t.latitude_dd), 4326) AS geom  from public.tbl_sites as t;

-- Required to allow REFRESH MATERIALIZED VIEW CONCURRENTLY
create unique index if not exists site_uidx
  on authority.site (site_id);

-- Trigram index must be on the MV column we filter with (%), not on base table.
create index if not exists site_norm_trgm
  on authority.site
    using gin (norm_label gin_trgm_ops);

-- (First-time populate)
-- refresh materialized view concurrently authority.site;
-- analyze authority.site;

/***************************************************************************************************
 ** Procedure  authority.fuzzy_site
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_site('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_site(text, integer) cascade;

create or replace function authority.fuzzy_site(
  p_text text,
  p_limit integer default 10) returns table (
  site_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.site_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.site as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Taxa Synonym - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxa_synonym cascade;

create or replace view authority.taxa_synonym as
  select
    t.synonym_id,
    t.synonym as label,
    authority.immutable_unaccent(lower(t.synonym)) as norm_label,
    t.taxon_id  from public.tbl_taxa_synonyms as t  join public.tbl_taxa_tree_master ttm using (taxon_id);

create index if not exists tbl_taxa_synonyms_norm_trgm
  on public.tbl_taxa_synonyms
    using gin ( (authority.immutable_unaccent(lower(synonym))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_synonym
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_synonym('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_synonym(text, integer) cascade;

create or replace function authority.fuzzy_taxa_synonym(
  p_text text,
  p_limit integer default 10) returns table (
  synonym_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.synonym_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_synonym as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Taxa Author - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxa_tree_author cascade;

create or replace view authority.taxa_tree_author as
  select
    t.author_id,
    t.author_name as label,
    authority.immutable_unaccent(lower(t.author_name)) as norm_label  from public.tbl_taxa_tree_authors as t;

create index if not exists tbl_taxa_tree_authors_norm_trgm
  on public.tbl_taxa_tree_authors
    using gin ( (authority.immutable_unaccent(lower(author_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_author
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_author('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_author(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_author(
  p_text text,
  p_limit integer default 10) returns table (
  author_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.author_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_author as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Taxa Family - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxa_tree_family cascade;

create or replace view authority.taxa_tree_family as
  select
    t.family_id,
    t.family_name as label,
    authority.immutable_unaccent(lower(t.family_name)) as norm_label,
    t.order_id  from public.tbl_taxa_tree_families as t  join public.tbl_taxa_tree_orders ord using (order_id);

create index if not exists tbl_taxa_tree_families_norm_trgm
  on public.tbl_taxa_tree_families
    using gin ( (authority.immutable_unaccent(lower(family_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_family
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_family('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_family(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_family(
  p_text text,
  p_limit integer default 10) returns table (
  family_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.family_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_family as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Taxa Genus - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxa_tree_genus cascade;

create or replace view authority.taxa_tree_genus as
  select
    t.genus_id,
    t.genus_name as label,
    authority.immutable_unaccent(lower(t.genus_name)) as norm_label,
    t.family_id  from public.tbl_taxa_tree_genera as t  join public.tbl_taxa_tree_families fam using (family_id);

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

/**********************************************************************************************
**  Taxa - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxa_tree_master cascade;

create or replace view authority.taxa_tree_master as
  select
    t.taxon_id,
    t.species as label,
    authority.immutable_unaccent(lower(t.species)) as norm_label,
    t.genus_id  from public.tbl_taxa_tree_master as t  join public.tbl_taxa_tree_genera gen using (genus_id);

create index if not exists tbl_taxa_tree_master_norm_trgm
  on public.tbl_taxa_tree_master
    using gin ( (authority.immutable_unaccent(lower(species))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_master
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_master('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_master(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_master(
  p_text text,
  p_limit integer default 10) returns table (
  taxon_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.taxon_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_master as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Taxa Order - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxa_tree_order cascade;

create or replace view authority.taxa_tree_order as
  select
    t.order_id,
    t.order_name as label,
    authority.immutable_unaccent(lower(t.order_name)) as norm_label,
    t.record_type_id  from public.tbl_taxa_tree_orders as t  join public.tbl_record_types rt using (record_type_id);

create index if not exists tbl_taxa_tree_orders_norm_trgm
  on public.tbl_taxa_tree_orders
    using gin ( (authority.immutable_unaccent(lower(order_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_order
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_order('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_order(text, integer) cascade;

create or replace function authority.fuzzy_taxa_tree_order(
  p_text text,
  p_limit integer default 10) returns table (
  order_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.order_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_order as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Taxonomic Order System - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxonomic_order_system cascade;

create or replace view authority.taxonomic_order_system as
  select
    t.taxonomic_order_system_id,
    t.system_name as label,
    authority.immutable_unaccent(lower(t.system_name)) as norm_label,
    t.system_description  from public.tbl_taxonomic_order_systems as t;

create index if not exists tbl_taxonomic_order_systems_norm_trgm
  on public.tbl_taxonomic_order_systems
    using gin ( (authority.immutable_unaccent(lower(system_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxonomic_order_system
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxonomic_order_system('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxonomic_order_system(text, integer) cascade;

create or replace function authority.fuzzy_taxonomic_order_system(
  p_text text,
  p_limit integer default 10) returns table (
  taxonomic_order_system_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.taxonomic_order_system_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxonomic_order_system as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

/**********************************************************************************************
**  Taxonomy Note - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.taxonomy_note cascade;

create or replace view authority.taxonomy_note as
  select
    t.taxonomy_notes_id,
    t.taxonomy_notes as label,
    authority.immutable_unaccent(lower(t.taxonomy_notes)) as norm_label  from public.tbl_taxonomy_notes as t;

create index if not exists tbl_taxonomy_notes_norm_trgm
  on public.tbl_taxonomy_notes
    using gin ( (authority.immutable_unaccent(lower(taxonomy_notes))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxonomy_note
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxonomy_note('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxonomy_note(text, integer) cascade;

create or replace function authority.fuzzy_taxonomy_note(
  p_text text,
  p_limit integer default 10) returns table (
  taxonomy_notes_id integer,
  label text,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )  select
    s.taxonomy_notes_id,
    s.label,
    greatest(
      case when s.norm_label = pq.q then 1.0
          else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxonomy_note as s
  cross join params pq  where s.norm_label % pq.q  order by name_sim desc, s.label
  limit p_limit;
$$;

commit;
