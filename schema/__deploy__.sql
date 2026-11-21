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
  select public.unaccent('public.unaccent'::regdictionary, p_value)
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
**  Abundance Element - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.abundance_element cascade;

create or replace view authority.abundance_element as
  select
    t.abundance_element_id,
    t.element_name as label,
    authority.immutable_unaccent(lower(t.element_name)) as norm_label,
  t.element_description as description,
  authority.immutable_unaccent(lower(t.element_description)) as norm_description  from public.tbl_abundance_elements as t;

create index if not exists tbl_abundance_elements_norm_trgm
  on public.tbl_abundance_elements
    using gin ( (authority.immutable_unaccent(lower(element_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_abundance_element
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_abundance_element('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_abundance_element(text, integer) cascade;
drop function if exists authority.fuzzy_abundance_element(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_abundance_element(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  abundance_element_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.abundance_element_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.abundance_element as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Activity Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.activity_type cascade;

create or replace view authority.activity_type as
  select
    t.activity_type_id,
    t.activity_type as label,
    authority.immutable_unaccent(lower(t.activity_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_activity_types as t;

create index if not exists tbl_activity_types_norm_trgm
  on public.tbl_activity_types
    using gin ( (authority.immutable_unaccent(lower(activity_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_activity_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_activity_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_activity_type(text, integer) cascade;
drop function if exists authority.fuzzy_activity_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_activity_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  activity_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.activity_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.activity_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Age Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.age_type cascade;

create or replace view authority.age_type as
  select
    t.age_type_id,
    t.age_type as label,
    authority.immutable_unaccent(lower(t.age_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_age_types as t;

create index if not exists tbl_age_types_norm_trgm
  on public.tbl_age_types
    using gin ( (authority.immutable_unaccent(lower(age_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_age_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_age_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_age_type(text, integer) cascade;
drop function if exists authority.fuzzy_age_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_age_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  age_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.age_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.age_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Alternate Reference Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.alt_ref_type cascade;

create or replace view authority.alt_ref_type as
  select
    t.alt_ref_type_id,
    t.alt_ref_type as label,
    authority.immutable_unaccent(lower(t.alt_ref_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_alt_ref_types as t;

create index if not exists tbl_alt_ref_types_norm_trgm
  on public.tbl_alt_ref_types
    using gin ( (authority.immutable_unaccent(lower(alt_ref_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_alt_ref_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_alt_ref_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_alt_ref_type(text, integer) cascade;
drop function if exists authority.fuzzy_alt_ref_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_alt_ref_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  alt_ref_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.alt_ref_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.alt_ref_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


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
**  Colour - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.colour cascade;

create or replace view authority.colour as
  select
    t.colour_id,
    t.colour_name as label,
    authority.immutable_unaccent(lower(t.colour_name)) as norm_label,
  null::text as description,
  null::text as norm_description  from public.tbl_colours as t;

create index if not exists tbl_colours_norm_trgm
  on public.tbl_colours
    using gin ( (authority.immutable_unaccent(lower(colour_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_colour
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_colour('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_colour(text, integer) cascade;
drop function if exists authority.fuzzy_colour(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_colour(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  colour_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.colour_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.colour as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Contact Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.contact_type cascade;

create or replace view authority.contact_type as
  select
    t.contact_type_id,
    t.contact_type_name as label,
    authority.immutable_unaccent(lower(t.contact_type_name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_contact_types as t;

create index if not exists tbl_contact_types_norm_trgm
  on public.tbl_contact_types
    using gin ( (authority.immutable_unaccent(lower(contact_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_contact_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_contact_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_contact_type(text, integer) cascade;
drop function if exists authority.fuzzy_contact_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_contact_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  contact_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.contact_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.contact_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Country - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.country cascade;

create or replace view authority.country as
  select
    t.location_id,
    t.location_name as label,
    authority.immutable_unaccent(lower(t.location_name)) as norm_label,
  null::text as description,
  null::text as norm_description  from public.tbl_locations as t  where location_type_id = 1;

create index if not exists tbl_locations_norm_trgm
  on public.tbl_locations
    using gin ( (authority.immutable_unaccent(lower(location_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_country
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_country('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_country(text, integer) cascade;
drop function if exists authority.fuzzy_country(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_country(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  location_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.location_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.country as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Dataset Submission Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.dataset_submission_type cascade;

create or replace view authority.dataset_submission_type as
  select
    t.submission_type_id,
    t.submission_type as label,
    authority.immutable_unaccent(lower(t.submission_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_dataset_submission_types as t;

create index if not exists tbl_dataset_submission_types_norm_trgm
  on public.tbl_dataset_submission_types
    using gin ( (authority.immutable_unaccent(lower(submission_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_dataset_submission_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_dataset_submission_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_dataset_submission_type(text, integer) cascade;
drop function if exists authority.fuzzy_dataset_submission_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_dataset_submission_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  submission_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.submission_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.dataset_submission_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_data_type_groups as t;

create index if not exists tbl_data_type_groups_norm_trgm
  on public.tbl_data_type_groups
    using gin ( (authority.immutable_unaccent(lower(data_type_group_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_data_type_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_data_type_group('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_data_type_group(text, integer) cascade;
drop function if exists authority.fuzzy_data_type_group(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_data_type_group(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  data_type_group_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.data_type_group_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.data_type_group as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.definition as description,
  authority.immutable_unaccent(lower(t.definition)) as norm_description,
    dtg.data_type_group_name as data_type_group_name,
    dtg.description as data_type_group_description  from public.tbl_data_types as t  left join public.tbl_data_type_groups dtg using (data_type_group_id);

create index if not exists tbl_data_types_norm_trgm
  on public.tbl_data_types
    using gin ( (authority.immutable_unaccent(lower(data_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_data_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_data_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_data_type(text, integer) cascade;
drop function if exists authority.fuzzy_data_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_data_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  data_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.data_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.data_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_dating_uncertainty as t;

create index if not exists tbl_dating_uncertainty_norm_trgm
  on public.tbl_dating_uncertainty
    using gin ( (authority.immutable_unaccent(lower(uncertainty))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_dating_uncertainty
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_dating_uncertainty('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_dating_uncertainty(text, integer) cascade;
drop function if exists authority.fuzzy_dating_uncertainty(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_dating_uncertainty(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  dating_uncertainty_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.dating_uncertainty_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.dating_uncertainty as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Ecocode Definition - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.ecocode_definition cascade;

create or replace view authority.ecocode_definition as
  select
    t.ecocode_definition_id,
    t.name as label,
    authority.immutable_unaccent(lower(t.name)) as norm_label,
  t.definition as description,
  authority.immutable_unaccent(lower(t.definition)) as norm_description  from public.tbl_ecocode_definitions as t;

create index if not exists tbl_ecocode_definitions_norm_trgm
  on public.tbl_ecocode_definitions
    using gin ( (authority.immutable_unaccent(lower(name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_ecocode_definition
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_ecocode_definition('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_ecocode_definition(text, integer) cascade;
drop function if exists authority.fuzzy_ecocode_definition(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_ecocode_definition(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  ecocode_definition_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.ecocode_definition_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.ecocode_definition as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Ecocode Group - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.ecocode_group cascade;

create or replace view authority.ecocode_group as
  select
    t.ecocode_group_id,
    t.name as label,
    authority.immutable_unaccent(lower(t.name)) as norm_label,
  t.definition as description,
  authority.immutable_unaccent(lower(t.definition)) as norm_description  from public.tbl_ecocode_groups as t;

create index if not exists tbl_ecocode_groups_norm_trgm
  on public.tbl_ecocode_groups
    using gin ( (authority.immutable_unaccent(lower(name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_ecocode_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_ecocode_group('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_ecocode_group(text, integer) cascade;
drop function if exists authority.fuzzy_ecocode_group(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_ecocode_group(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  ecocode_group_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.ecocode_group_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.ecocode_group as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.feature_type_description as description,
  authority.immutable_unaccent(lower(t.feature_type_description)) as norm_description  from public.tbl_feature_types as t;

create index if not exists tbl_feature_types_norm_trgm
  on public.tbl_feature_types
    using gin ( (authority.immutable_unaccent(lower(feature_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_feature_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_feature_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_feature_type(text, integer) cascade;
drop function if exists authority.fuzzy_feature_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_feature_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  feature_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.feature_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.feature_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Horizon - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.horizon cascade;

create or replace view authority.horizon as
  select
    t.horizon_id,
    t.horizon_name as label,
    authority.immutable_unaccent(lower(t.horizon_name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_horizons as t;

create index if not exists tbl_horizons_norm_trgm
  on public.tbl_horizons
    using gin ( (authority.immutable_unaccent(lower(horizon_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_horizon
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_horizon('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_horizon(text, integer) cascade;
drop function if exists authority.fuzzy_horizon(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_horizon(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  horizon_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.horizon_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.horizon as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Identification Level - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.identification_level cascade;

create or replace view authority.identification_level as
  select
    t.identification_level_id,
    t.identification_level_name as label,
    authority.immutable_unaccent(lower(t.identification_level_name)) as norm_label,
  t.notes as description,
  authority.immutable_unaccent(lower(t.notes)) as norm_description  from public.tbl_identification_levels as t;

create index if not exists tbl_identification_levels_norm_trgm
  on public.tbl_identification_levels
    using gin ( (authority.immutable_unaccent(lower(identification_level_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_identification_level
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_identification_level('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_identification_level(text, integer) cascade;
drop function if exists authority.fuzzy_identification_level(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_identification_level(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  identification_level_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.identification_level_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.identification_level as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Language - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.language cascade;

create or replace view authority.language as
  select
    t.language_id,
    t.language_name_english as label,
    authority.immutable_unaccent(lower(t.language_name_english)) as norm_label,
  null::text as description,
  null::text as norm_description  from public.tbl_languages as t;

create index if not exists tbl_languages_norm_trgm
  on public.tbl_languages
    using gin ( (authority.immutable_unaccent(lower(language_name_english))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_language
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_language('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_language(text, integer) cascade;
drop function if exists authority.fuzzy_language(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_language(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  language_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.language_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.language as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_location_types as t;

create index if not exists tbl_location_types_norm_trgm
  on public.tbl_location_types
    using gin ( (authority.immutable_unaccent(lower(location_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_location_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_location_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_location_type(text, integer) cascade;
drop function if exists authority.fuzzy_location_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_location_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  location_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.location_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.location_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_method_groups as t;

create index if not exists tbl_method_groups_norm_trgm
  on public.tbl_method_groups
    using gin ( (authority.immutable_unaccent(lower(group_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_method_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_method_group('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_method_group(text, integer) cascade;
drop function if exists authority.fuzzy_method_group(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_method_group(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  method_group_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.method_group_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.method_group as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
**  Project Stage - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.project_stage cascade;

create or replace view authority.project_stage as
  select
    t.project_stage_id,
    t.stage_name as label,
    authority.immutable_unaccent(lower(t.stage_name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_project_stages as t;

create index if not exists tbl_project_stages_norm_trgm
  on public.tbl_project_stages
    using gin ( (authority.immutable_unaccent(lower(stage_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_project_stage
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_project_stage('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_project_stage(text, integer) cascade;
drop function if exists authority.fuzzy_project_stage(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_project_stage(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  project_stage_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.project_stage_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.project_stage as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Project Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.project_type cascade;

create or replace view authority.project_type as
  select
    t.project_type_id,
    t.project_type_name as label,
    authority.immutable_unaccent(lower(t.project_type_name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_project_types as t;

create index if not exists tbl_project_types_norm_trgm
  on public.tbl_project_types
    using gin ( (authority.immutable_unaccent(lower(project_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_project_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_project_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_project_type(text, integer) cascade;
drop function if exists authority.fuzzy_project_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_project_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  project_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.project_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.project_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Property Type Group - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.property_type_group cascade;

create or replace view authority.property_type_group as
  select
    t.property_type_group_id,
    t.property_type_group as label,
    authority.immutable_unaccent(lower(t.property_type_group)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_property_type_groups as t;

create index if not exists tbl_property_type_groups_norm_trgm
  on public.tbl_property_type_groups
    using gin ( (authority.immutable_unaccent(lower(property_type_group))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_property_type_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_property_type_group('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_property_type_group(text, integer) cascade;
drop function if exists authority.fuzzy_property_type_group(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_property_type_group(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  property_type_group_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.property_type_group_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.property_type_group as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Property Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.property_type cascade;

create or replace view authority.property_type as
  select
    t.property_type_id,
    t.property_type_name as label,
    authority.immutable_unaccent(lower(t.property_type_name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_property_types as t;

create index if not exists tbl_property_types_norm_trgm
  on public.tbl_property_types
    using gin ( (authority.immutable_unaccent(lower(property_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_property_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_property_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_property_type(text, integer) cascade;
drop function if exists authority.fuzzy_property_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_property_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  property_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.property_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.property_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  RDB Code - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.rdb_code cascade;

create or replace view authority.rdb_code as
  select
    t.rdb_code_id,
    t.rdb_category as label,
    authority.immutable_unaccent(lower(t.rdb_category)) as norm_label,
  t.rdb_definition as description,
  authority.immutable_unaccent(lower(t.rdb_definition)) as norm_description  from public.tbl_rdb_codes as t;

create index if not exists tbl_rdb_codes_norm_trgm
  on public.tbl_rdb_codes
    using gin ( (authority.immutable_unaccent(lower(rdb_category))) gin_trgm_ops );

create index if not exists tbl_rdb_codes_norm_desc_trgm
  on public.tbl_rdb_codes
    using gin ( (authority.immutable_unaccent(lower(rdb_definition))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_rdb_code
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_rdb_code('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_rdb_code(text, integer) cascade;
drop function if exists authority.fuzzy_rdb_code(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_rdb_code(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  rdb_code_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  , scored as (
    select
      s.rdb_code_id,
      s.label,
      s.description,
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q) end as label_sim,
      coalesce(strict_word_similarity(pq.q, s.norm_description), 0) as description_sim
    from authority.rdb_code as s
    cross join params pq
  )
  , filtered as (
    select *
    from scored
    where scored.label_sim >= p_label_threshold
       or scored.description_sim >= p_description_threshold
  )
  select
    filtered.rdb_code_id,
    filtered.label,
    filtered.description,
    filtered.label_sim,
    least(1.0, filtered.label_sim + 0.15 * filtered.description_sim) as name_sim
  from filtered
  order by name_sim desc, filtered.label_sim desc, filtered.label
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
  t.record_type_description as description,
  authority.immutable_unaccent(lower(t.record_type_description)) as norm_description  from public.tbl_record_types as t;

create index if not exists tbl_record_types_norm_trgm
  on public.tbl_record_types
    using gin ( (authority.immutable_unaccent(lower(record_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_record_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_record_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_record_type(text, integer) cascade;
drop function if exists authority.fuzzy_record_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_record_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  record_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.record_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.record_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_relative_age_types as t;

create index if not exists tbl_relative_age_types_norm_trgm
  on public.tbl_relative_age_types
    using gin ( (authority.immutable_unaccent(lower(age_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_relative_age_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_relative_age_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_relative_age_type(text, integer) cascade;
drop function if exists authority.fuzzy_relative_age_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_relative_age_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  relative_age_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.relative_age_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.relative_age_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.type_description as description,
  authority.immutable_unaccent(lower(t.type_description)) as norm_description  from public.tbl_sample_description_types as t;

create index if not exists tbl_sample_description_types_norm_trgm
  on public.tbl_sample_description_types
    using gin ( (authority.immutable_unaccent(lower(type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_description_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_description_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_description_type(text, integer) cascade;
drop function if exists authority.fuzzy_sample_description_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_sample_description_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  sample_description_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.sample_description_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_description_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.type_description as description,
  authority.immutable_unaccent(lower(t.type_description)) as norm_description  from public.tbl_sample_group_description_types as t;

create index if not exists tbl_sample_group_description_types_norm_trgm
  on public.tbl_sample_group_description_types
    using gin ( (authority.immutable_unaccent(lower(type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_group_description_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_group_description_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_group_description_type(text, integer) cascade;
drop function if exists authority.fuzzy_sample_group_description_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_sample_group_description_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  sample_group_description_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.sample_group_description_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_group_description_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.location_type_description as description,
  authority.immutable_unaccent(lower(t.location_type_description)) as norm_description  from public.tbl_sample_location_types as t;

create index if not exists tbl_sample_location_types_norm_trgm
  on public.tbl_sample_location_types
    using gin ( (authority.immutable_unaccent(lower(location_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_location_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_location_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_location_type(text, integer) cascade;
drop function if exists authority.fuzzy_sample_location_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_sample_location_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  sample_location_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.sample_location_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_location_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_sample_types as t;

create index if not exists tbl_sample_types_norm_trgm
  on public.tbl_sample_types
    using gin ( (authority.immutable_unaccent(lower(type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_sample_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_sample_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_sample_type(text, integer) cascade;
drop function if exists authority.fuzzy_sample_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_sample_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  sample_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.sample_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.sample_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
**  Season - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.season cascade;

create or replace view authority.season as
  select
    t.season_id,
    t.season_name as label,
    authority.immutable_unaccent(lower(t.season_name)) as norm_label,
  null::text as description,
  null::text as norm_description  from public.tbl_seasons as t;

create index if not exists tbl_seasons_norm_trgm
  on public.tbl_seasons
    using gin ( (authority.immutable_unaccent(lower(season_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_season
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_season('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_season(text, integer) cascade;
drop function if exists authority.fuzzy_season(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_season(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  season_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.season_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.season as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Season Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.season_type cascade;

create or replace view authority.season_type as
  select
    t.season_type_id,
    t.season_type as label,
    authority.immutable_unaccent(lower(t.season_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_season_types as t;

create index if not exists tbl_season_types_norm_trgm
  on public.tbl_season_types
    using gin ( (authority.immutable_unaccent(lower(season_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_season_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_season_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_season_type(text, integer) cascade;
drop function if exists authority.fuzzy_season_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_season_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  season_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.season_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.season_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
**  Site Type Group - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.site_type_group cascade;

create or replace view authority.site_type_group as
  select
    t.site_type_group_id,
    t.site_type_group as label,
    authority.immutable_unaccent(lower(t.site_type_group)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_site_type_groups as t;

create index if not exists tbl_site_type_groups_norm_trgm
  on public.tbl_site_type_groups
    using gin ( (authority.immutable_unaccent(lower(site_type_group))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_site_type_group
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_site_type_group('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_site_type_group(text, integer) cascade;
drop function if exists authority.fuzzy_site_type_group(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_site_type_group(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  site_type_group_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.site_type_group_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.site_type_group as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Site Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.site_type cascade;

create or replace view authority.site_type as
  select
    t.site_type_id,
    t.site_type as label,
    authority.immutable_unaccent(lower(t.site_type)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_site_types as t;

create index if not exists tbl_site_types_norm_trgm
  on public.tbl_site_types
    using gin ( (authority.immutable_unaccent(lower(site_type))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_site_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_site_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_site_type(text, integer) cascade;
drop function if exists authority.fuzzy_site_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_site_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  site_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.site_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.site_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Species Association Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.species_association_type cascade;

create or replace view authority.species_association_type as
  select
    t.association_type_id,
    t.association_type_name as label,
    authority.immutable_unaccent(lower(t.association_type_name)) as norm_label,
  t.association_description as description,
  authority.immutable_unaccent(lower(t.association_description)) as norm_description  from public.tbl_species_association_types as t;

create index if not exists tbl_species_association_types_norm_trgm
  on public.tbl_species_association_types
    using gin ( (authority.immutable_unaccent(lower(association_type_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_species_association_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_species_association_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_species_association_type(text, integer) cascade;
drop function if exists authority.fuzzy_species_association_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_species_association_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  association_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.association_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.species_association_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Submission State - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.submission_state cascade;

create or replace view authority.submission_state as
  select
    t.submission_state_id,
    t.submission_state as label,
    authority.immutable_unaccent(lower(t.submission_state)) as norm_label,
  t.note as description,
  authority.immutable_unaccent(lower(t.note)) as norm_description  from public.tbl_submission_states as t;

create index if not exists tbl_submission_states_norm_trgm
  on public.tbl_submission_states
    using gin ( (authority.immutable_unaccent(lower(submission_state))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_submission_state
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_submission_state('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_submission_state(text, integer) cascade;
drop function if exists authority.fuzzy_submission_state(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_submission_state(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  submission_state_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.submission_state_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.submission_state as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Submission Task Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.submission_task_type cascade;

create or replace view authority.submission_task_type as
  select
    t.submission_task_type_id,
    t.action_task_name as label,
    authority.immutable_unaccent(lower(t.action_task_name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_submission_task_types as t;

create index if not exists tbl_submission_task_types_norm_trgm
  on public.tbl_submission_task_types
    using gin ( (authority.immutable_unaccent(lower(action_task_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_submission_task_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_submission_task_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_submission_task_type(text, integer) cascade;
drop function if exists authority.fuzzy_submission_task_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_submission_task_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  submission_task_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.submission_task_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.submission_task_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
    authority.immutable_unaccent(lower(t.author_name)) as norm_label,
  null::text as description,
  null::text as norm_description  from public.tbl_taxa_tree_authors as t;

create index if not exists tbl_taxa_tree_authors_norm_trgm
  on public.tbl_taxa_tree_authors
    using gin ( (authority.immutable_unaccent(lower(author_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_taxa_tree_author
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_taxa_tree_author('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_taxa_tree_author(text, integer) cascade;
drop function if exists authority.fuzzy_taxa_tree_author(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_taxa_tree_author(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  author_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.author_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_author as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  null::text as description,
  null::text as norm_description,
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
drop function if exists authority.fuzzy_taxa_tree_family(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_taxa_tree_family(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  family_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.family_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_family as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  null::text as description,
  null::text as norm_description,
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
drop function if exists authority.fuzzy_taxa_tree_genus(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_taxa_tree_genus(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  genus_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.genus_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_genus as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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
  null::text as description,
  null::text as norm_description,
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
drop function if exists authority.fuzzy_taxa_tree_order(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_taxa_tree_order(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  order_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.order_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.taxa_tree_order as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
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

/**********************************************************************************************
**  Unit - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.unit cascade;

create or replace view authority.unit as
  select
    t.unit_id,
    t.unit_name as label,
    authority.immutable_unaccent(lower(t.unit_name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_units as t;

create index if not exists tbl_units_norm_trgm
  on public.tbl_units
    using gin ( (authority.immutable_unaccent(lower(unit_name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_unit
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_unit('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_unit(text, integer) cascade;
drop function if exists authority.fuzzy_unit(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_unit(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  unit_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.unit_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.unit as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Value Class - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.value_class cascade;

create or replace view authority.value_class as
  select
    t.value_class_id,
    t.name as label,
    authority.immutable_unaccent(lower(t.name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_value_classes as t;

create index if not exists tbl_value_classes_norm_trgm
  on public.tbl_value_classes
    using gin ( (authority.immutable_unaccent(lower(name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_value_class
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_value_class('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_value_class(text, integer) cascade;
drop function if exists authority.fuzzy_value_class(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_value_class(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  value_class_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.value_class_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.value_class as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Value Qualifier - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.value_qualifier cascade;

create or replace view authority.value_qualifier as
  select
    t.qualifier_id,
    t.symbol as label,
    authority.immutable_unaccent(lower(t.symbol)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_value_qualifiers as t;

create index if not exists tbl_value_qualifiers_norm_trgm
  on public.tbl_value_qualifiers
    using gin ( (authority.immutable_unaccent(lower(symbol))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_value_qualifier
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_value_qualifier('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_value_qualifier(text, integer) cascade;
drop function if exists authority.fuzzy_value_qualifier(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_value_qualifier(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  qualifier_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.qualifier_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.value_qualifier as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Value Type Item - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.value_type_item cascade;

create or replace view authority.value_type_item as
  select
    t.value_type_item_id,
    t.name as label,
    authority.immutable_unaccent(lower(t.name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_value_type_items as t;

create index if not exists tbl_value_type_items_norm_trgm
  on public.tbl_value_type_items
    using gin ( (authority.immutable_unaccent(lower(name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_value_type_item
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_value_type_item('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_value_type_item(text, integer) cascade;
drop function if exists authority.fuzzy_value_type_item(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_value_type_item(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  value_type_item_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.value_type_item_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.value_type_item as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


/**********************************************************************************************
**  Value Type - Tri-gram Search Objects
**  Generated from template by generate_entity_schema.py
**  
**  Note: This file creates the base view WITHOUT embeddings.
**        If the entity has embeddings, also install semantic-{entity}.sql to create
**        the embeddings table and semantic search functions.
**********************************************************************************************/

drop view if exists authority.value_type cascade;

create or replace view authority.value_type as
  select
    t.value_type_id,
    t.name as label,
    authority.immutable_unaccent(lower(t.name)) as norm_label,
  t.description as description,
  authority.immutable_unaccent(lower(t.description)) as norm_description  from public.tbl_value_types as t;

create index if not exists tbl_value_types_norm_trgm
  on public.tbl_value_types
    using gin ( (authority.immutable_unaccent(lower(name))) gin_trgm_ops );

/***************************************************************************************************
 ** Procedure  authority.fuzzy_value_type
 ** What       Trigram fuzzy search function using pg_trgm similarity
 ** Usage      SELECT * FROM authority.fuzzy_value_type('query text', 10);
 ****************************************************************************************************/

drop function if exists authority.fuzzy_value_type(text, integer) cascade;
drop function if exists authority.fuzzy_value_type(text, integer, double precision, double precision) cascade;

create or replace function authority.fuzzy_value_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50) returns table (
  value_type_id integer,
  label text,
  description text,
  label_sim double precision,
  name_sim double precision
) language sql stable
as $$
  with params as (
    select authority.immutable_unaccent(lower(p_text))::text as q
  )
  select
    s.value_type_id,
    s.label,
    s.description,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as label_sim,
    greatest(
      case when s.norm_label = pq.q then 1.0
           else similarity(s.norm_label, pq.q)
      end, 0.0001
    ) as name_sim
  from authority.value_type as s
  cross join params pq
  where case when s.norm_label = pq.q then 1.0
             else similarity(s.norm_label, pq.q) end >= p_label_threshold
  order by name_sim desc, s.label
  limit p_limit;
$$;


-- Read access to the authority schema
--
-- This file must run after every schema object exists. `authority.sql` starts
-- with `drop schema if exists authority cascade`, so the schema and its objects
-- are recreated on every deployment and their privileges go with them. A grant
-- placed before the objects exist would either be dropped with the schema or
-- silently cover nothing, because `GRANT ... ON ALL ... IN SCHEMA` only affects
-- objects that already exist when it runs.
--
-- The `fuzzy_*` search functions are SECURITY INVOKER and read the entity
-- materialized views, so a caller needs all three of:
--   * USAGE on the schema     (without it every call fails with
--                              "permission denied for schema authority")
--   * EXECUTE on the routines (covers the `fuzzy_*` functions and procedures)
--   * SELECT on the views     (`ON ALL TABLES` includes materialized views)
--
-- Grantee: PUBLIC, so any role that can connect to the database may run the
-- read-only search. To restrict access, replace PUBLIC with the roles your
-- deployment uses, for example the role named by
-- SEAD_AUTHORITY_OPTIONS_DATABASE_USER.

grant usage on schema authority to public;

grant select on all tables in schema authority to public;
grant execute on all routines in schema authority to public;

-- Apply the same access to objects created after this file runs. Default
-- privileges are stored per owning role, so this covers later objects created by
-- the role that performs the deployment.

alter default privileges in schema authority grant select on tables to public;
alter default privileges in schema authority grant execute on routines to public;

commit;
