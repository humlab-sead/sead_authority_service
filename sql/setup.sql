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
**  Feature Type
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

/**********************************************************/

select *
from authority.fuzzy_find_entity_type_candidates('burial ground', 5);

-- find "träkol" in full text search using fuzzy matching
select *, ts_rank_cd(tsv, plainto_tsquery('english', unaccent(pq.q))) as rank, sead_utility.table_name_to_entity_name(table_name) as entity_name
from sead_utility.full_text_search
cross join (
    select authority.immutable_unaccent(lower('Pithole'))::text as q
) as pq
--where value % pq.q
where value::tsvector @@ to_tsquery('Pithole')
order by ts_rank_cd(tsv, plainto_tsquery('english', unaccent(pq.q))) desc
limit 20;

select *, sead_utility.table_name_to_entity_name(table_name) as entity_name
from sead_utility.full_text_search
cross join (
    select plainto_tsquery('insect') as q, authority.immutable_unaccent(:user_query) as uq
) as pq
where tsv @@ pq.q
limit 20;

select * from sead_utility.full_text_search

-- Fuzzy full text search threshold tuning:
/*
SHOW pg_trgm.similarity_threshold;
SET pg_trgm.similarity_threshold = 0.25;
| Method                              | Description                          | Strengths                              | Weaknesses                                                        |
| ----------------------------------- | ------------------------------------ | -------------------------------------- | ----------------------------------------------------------------- |
| **`%` (trigram)**                   | Boolean fuzzy match using `pg_trgm`  | Fast, indexable, tunable               | Threshold-based (no numeric result unless you use `similarity()`) |
| **`similarity(a,b)`**               | Returns float 0–1                    | Precise scoring, rank results          | Slower if no index, you must filter manually                      |
| **`<->`**                           | “Distance” operator (1 − similarity) | Works for `ORDER BY value <-> 'query'` | Threshold must be applied separately                              |
| **`ILIKE`**                         | Case-insensitive substring           | Simple, deterministic                  | No fuzziness, no index use (usually)                              |
| **`Levenshtein(a,b)`**              | Edit distance from `fuzzystrmatch`   | Exact edit count                       | No index support, slower for big datasets                         |
| **`dmetaphone(a) = dmetaphone(b)`** | Phonetic match (`fuzzystrmatch`)     | Good for names/speech                  | Not useful for general text                                       |
| **`to_tsvector @@ to_tsquery`**     | Full-text search                     | Semantic/stem-based                    | No typo tolerance                                                 |

| Operator | Meaning                   | Typical use                     |
| -------- | ------------------------- | ------------------------------- |
| `%`      | fuzzy match (basic)       | general-purpose fuzzy search    |
| `<->`    | similarity distance       | ranking / ordering              |
| `<%>`    | fuzzy match at word level | matching subwords in long text  |
| `<<%>>`  | strict word fuzzy match   | when words must match exactly   |
| `<<->`   | word-level distance       | ranking for token-level matches |
| `<<<->`  | strict word distance      | ranking stricter matches        |
| Function                                 | Description                                                                                          | Return type | Example                                                                    | Notes                            |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------- | -------------------------------- |
| **`similarity(text, text)`**             | Returns a number between **0 and 1** showing how similar two strings are (based on trigram overlap). | `float4`    | `SELECT similarity('cat', 'cats');` → `0.75`                               | Used for ranking.                |
| **`show_trgm(text)`**                    | Returns the set of trigrams (three-character sequences) that make up the text.                       | `text[]`    | `SELECT show_trgm('pithole');` → `{  p, pi, pit, ith, tho, hol, ole, le }` | Diagnostic tool.                 |
| **`word_similarity(text, text)`**        | Measures trigram similarity between words within the two strings.                                    | `float4`    | `SELECT word_similarity('postgres', 'postgreSQL database');`               | Focuses on word boundaries.      |
| **`strict_word_similarity(text, text)`** | Like `word_similarity` but requires entire words to match.                                           | `float4`    |                                                                            | Useful for token-aware matching. |
| **`word_similarity_op(text, text)`**     | Same as `word_similarity`, used internally by `<%%>` operator.                                       | `float4`    |                                                                            | Normally not called directly.    |
| Category                   | Function / Operator                         | Output         | Indexed | Notes                   |
| -------------------------- | ------------------------------------------- | -------------- | ------- | ----------------------- |
| **Similarity**             | `similarity(a,b)`                           | Float 0–1      | ✅       | core measure            |
| **Boolean fuzzy**          | `%`                                         | Boolean        | ✅       | default threshold       |
| **Distance**               | `<->`                                       | Float distance | ✅       | use for ORDER BY        |
| **Word similarity**        | `word_similarity(a,b)`                      | Float 0–1      | ✅       | word-based              |
| **Strict word similarity** | `strict_word_similarity(a,b)`               | Float 0–1      | ✅       | stricter token match    |
| **Word boolean fuzzy**     | `<%>`, `<<%>>`                              | Boolean        | ✅       | word-level thresholds   |
| **Word distance**          | `<<->`, `<<<->`                             | Float          | ✅       | word-level ORDER BY     |
| **Debugging**              | `show_trgm(a)`                              | Text array     | ❌       | reveals actual trigrams |
| **Tuning**                 | `SET pg_trgm.similarity_threshold = n`      | —              | —       | affects `%` ops         |
| **Tuning (word)**          | `SET pg_trgm.word_similarity_threshold = n` | —              | —       | affects word ops        |
*/


with params as (
  select 'brandgrav'::text as q,
         websearch_to_tsquery('simple', 'brandgrav') as tsq
)
select
  t.table_name,
  -- take the best fts score among that table's rows (only when fts matched)
  coalesce(max(ts_rank_cd(t.tsv, p.tsq)) filter (where t.tsv @@ p.tsq), 0) as fts_rank,
  -- best trigram similarity among that table's rows (only when trigram matched)
  coalesce(max(similarity(t.value_norm, p.q)) filter (where t.value_norm % p.q), 0) as trigram_sim,
  -- combined score: weight fts higher than trigram fuzziness
  (coalesce(max(ts_rank_cd(t.tsv, p.tsq)) filter (where t.tsv @@ p.tsq), 0)
   + 0.35 * coalesce(max(similarity(t.value_norm, p.q)) filter (where t.value_norm % p.q), 0)
  ) as score
from sead_utility.full_text_search t
cross join params p
where t.tsv @@ p.tsq
   or t.value_norm % p.q
group by t.table_name
order by score desc
limit 5;

select * from sead_utility.full_text_search
where table_name = 'tbl_taxa_tree_master'

drop function authority.fuzzy_find_entity_type_candidates( p_text text, p_limit integer);
