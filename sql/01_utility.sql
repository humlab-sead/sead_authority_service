
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
