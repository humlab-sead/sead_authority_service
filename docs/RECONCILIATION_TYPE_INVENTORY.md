# Reconciliation Type Inventory

This register is a snapshot of the Shape Shifter target model and the Authority Service's declared reconciliation types. It explains exclusions; it does not control the API. The service derives `defaultTypes` and `supportedTypes` from strategy registrations.

`supported` means a strategy declares that status, not that its configuration, schema, or deployment has been verified. In particular, `dimension` is registered as supported while its separate configuration and schema review remains outstanding. `excluded` covers registered types declared excluded and classifier or lookup entities without a registration. `not-a-target` covers unregistered fact and bridge entities. A service-only row has no separate target-model entity. The service type column distinguishes a registered exclusion from an unregistered entity.

Target tables and model text columns come from the target model. A text column is a possible input, not proof of a usable label. Configured labels, markers, and scope columns come from the service's table specifications; `-` means none is declared there. For specialized strategies, the configured-label column may be empty even when the strategy obtains its label elsewhere.

## Maintenance

Update the handwritten aliases, reasons, and planned phases in the YAML comment below, then run `make generate-reconciliation-inventory`. The default model path is `../sead_shape_shifter/resources/target_models/sead_standard_model.yml`; override it with `TARGET_MODEL=/path/to/sead_standard_model.yml` when the model is elsewhere. The generator needs a local copy of the model, not a database. Review changes to model coverage as a manual cross-repository snapshot.

The focused registry test runs without the sibling repository and checks that every registered service type appears exactly once with its declared disposition. Remove completed planned phases from the handwritten section; the generated phase column disappears when no planned entries remain.

<!-- reconciliation-inventory:manual
aliases:
  taxa: taxon
reasons:
  abundance_element_group: The project-side grouping has no target table.
  contact: No single label column is defined, and no contact strategy is registered.
  coordinate_method_dimension: No direct text label exists; derived-label reconciliation is out of scope.
  dataset: Datasets are tracked aggregates, and no dataset reconciliation strategy is registered.
  geonames: The external GeoNames strategy is registered as excluded.
  modification_type: The LLM-based strategy is registered as excluded.
  taxa: The registered taxon strategy is a placeholder and is excluded.
  value_qualifier_symbol: This alternate symbol maps to a value qualifier and has no standalone strategy.
-->

<!-- reconciliation-inventory:generated:start -->
## Snapshot Counts

Target-model version: `2.8.0`.
Model entities: 136. Registered service types: 69.

| Role | Count |
| --- | ---: |
| bridge | 13 |
| classifier | 53 |
| fact | 52 |
| lookup | 18 |
| service-only | 3 |

| Disposition | Count |
| --- | ---: |
| excluded | 8 |
| not-a-target | 65 |
| supported | 66 |

## Entity Register

<!-- reconciliation-inventory:rows:start -->
| Entity | Service type | Target table | Role | Disposition | Marker | Configured label | Model text columns | Scope columns | Reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `abundance` | - | `tbl_abundances` | fact | not-a-target | - | - | - | - | - |
| `abundance_element` | `abundance_element` | `tbl_abundance_elements` | classifier | supported | `simple` | `element_name` | `element_description`, `element_name` | `record_type_id` | - |
| `abundance_element_group` | - | - | classifier | excluded | - | - | `abundance_element_group_name`, `description` | - | The project-side grouping has no target table. |
| `abundance_ident_level` | - | `tbl_abundance_ident_levels` | bridge | not-a-target | - | - | - | - | - |
| `abundance_modification` | - | `tbl_abundance_modifications` | fact | not-a-target | - | - | - | - | - |
| `abundance_property` | - | `tbl_abundance_properties` | fact | not-a-target | - | - | `property_value` | - | - |
| `activity_type` | `activity_type` | `tbl_activity_types` | classifier | supported | `simple` | `activity_type` | `activity_type`, `description` | - | - |
| `age_type` | `age_type` | `tbl_age_types` | classifier | supported | `simple` | `age_type` | `age_type`, `description` | - | - |
| `alt_ref_type` | `alt_ref_type` | `tbl_alt_ref_types` | classifier | supported | `simple` | `alt_ref_type` | `alt_ref_type`, `description` | - | - |
| `analysis_boolean_value` | - | `tbl_analysis_boolean_values` | fact | not-a-target | - | - | `qualifier` | - | - |
| `analysis_categorical_value` | - | `tbl_analysis_categorical_values` | fact | not-a-target | - | - | - | - | - |
| `analysis_dating_range` | - | `tbl_analysis_dating_ranges` | fact | not-a-target | - | - | `high_qualifier`, `low_qualifier` | - | - |
| `analysis_entity` | - | `tbl_analysis_entities` | fact | not-a-target | - | - | - | - | - |
| `analysis_entity_age` | - | `tbl_analysis_entity_ages` | fact | not-a-target | - | - | `age_range`, `dating_specifier` | - | - |
| `analysis_entity_dimension` | - | `tbl_analysis_entity_dimensions` | fact | not-a-target | - | - | - | - | - |
| `analysis_entity_prep_method` | - | `tbl_analysis_entity_prep_methods` | bridge | not-a-target | - | - | - | - | - |
| `analysis_identifier` | - | `tbl_analysis_identifiers` | fact | not-a-target | - | - | `value` | - | - |
| `analysis_integer_range` | - | `tbl_analysis_integer_ranges` | fact | not-a-target | - | - | `high_qualifier`, `low_qualifier` | - | - |
| `analysis_integer_value` | - | `tbl_analysis_integer_values` | fact | not-a-target | - | - | `qualifier` | - | - |
| `analysis_note` | - | `tbl_analysis_notes` | fact | not-a-target | - | - | `value` | - | - |
| `analysis_numerical_range` | - | `tbl_analysis_numerical_ranges` | fact | not-a-target | - | - | `high_qualifier`, `low_qualifier` | - | - |
| `analysis_numerical_value` | - | `tbl_analysis_numerical_values` | fact | not-a-target | - | - | `qualifier` | - | - |
| `analysis_taxon_count` | - | `tbl_analysis_taxon_counts` | fact | not-a-target | - | - | - | - | - |
| `analysis_value` | - | `tbl_analysis_values` | fact | not-a-target | - | - | `analysis_value` | - | - |
| `analysis_value_dimension` | - | `tbl_analysis_value_dimensions` | fact | not-a-target | - | - | - | - | - |
| `chronology` | `chronology` | `tbl_chronologies` | lookup | supported | `lookup` | `chronology_name` | `age_model`, `chronology_name`, `notes` | - | - |
| `citation` | `bibliographic_reference` | `tbl_biblio` | lookup | supported | - | `full_reference` | `authors`, `bugs_reference`, `doi`, `full_reference`, `isbn`, `notes`, `title`, `url`, `year` | - | - |
| `colour` | `colour` | `tbl_colours` | classifier | supported | `simple` | `colour_name` | `colour_name` | `method_id` | - |
| `contact` | - | `tbl_contacts` | lookup | excluded | - | - | `address_1`, `address_2`, `email`, `first_name`, `last_name`, `phone_number`, `url` | - | No single label column is defined, and no contact strategy is registered. |
| `contact_type` | `contact_type` | `tbl_contact_types` | classifier | supported | `simple` | `contact_type_name` | `contact_type_name`, `description` | - | - |
| `coordinate_method_dimension` | - | `tbl_coordinate_method_dimensions` | classifier | excluded | - | - | - | - | No direct text label exists; derived-label reconciliation is out of scope. |
| `data_provider` | `data_provider` | `tbl_data_providers` | lookup | supported | `lookup` | `data_provider_name` | `data_provider_code`, `data_provider_name`, `notes`, `url` | - | - |
| `data_type` | `data_type` | `tbl_data_types` | classifier | supported | `simple` | `data_type_name` | `data_type_name`, `definition` | `data_type_group_id` | - |
| `data_type_group` | `data_type_group` | `tbl_data_type_groups` | classifier | supported | `simple` | `data_type_group_name` | `data_type_group_name`, `description` | - | - |
| `dataset` | - | `tbl_datasets` | lookup | excluded | - | - | `dataset_name` | - | Datasets are tracked aggregates, and no dataset reconciliation strategy is registered. |
| `dataset_contact` | - | `tbl_dataset_contacts` | bridge | not-a-target | - | - | - | - | - |
| `dataset_method` | - | `tbl_dataset_methods` | bridge | not-a-target | - | - | - | - | - |
| `dataset_submission` | - | `tbl_dataset_submissions` | fact | not-a-target | - | - | `date_submitted`, `notes` | - | - |
| `dataset_submission_type` | `dataset_submission_type` | `tbl_dataset_submission_types` | classifier | supported | `simple` | `submission_type` | `description`, `submission_type` | - | - |
| `dating_lab` | `dating_lab` | `tbl_dating_labs` | lookup | supported | `lookup` | `lab_name` | `international_lab_id`, `lab_name` | - | - |
| `dating_material` | `dating_material` | `tbl_dating_material` | lookup | supported | `lookup` | `material_dated` | `description`, `material_dated` | - | - |
| `dating_uncertainty` | `dating_uncertainty` | `tbl_dating_uncertainty` | classifier | supported | `simple` | `uncertainty` | `uncertainty` | - | - |
| `dimension` | `dimension` | `tbl_dimensions` | classifier | supported | - | - | `dimension_abbrev`, `dimension_name` | - | - |
| `ecocode` | - | `tbl_ecocodes` | fact | not-a-target | - | - | - | - | - |
| `ecocode_definition` | `ecocode_definition` | `tbl_ecocode_definitions` | classifier | supported | `simple` | `name` | `abbreviation`, `definition`, `name`, `notes` | `ecocode_group_id` | - |
| `ecocode_group` | `ecocode_group` | `tbl_ecocode_groups` | classifier | supported | `simple` | `name` | `abbreviation`, `definition`, `name` | `ecocode_system_id` | - |
| `ecocode_system` | `ecocode_system` | `tbl_ecocode_systems` | lookup | supported | `lookup` | `name` | `definition`, `ecocode_system_uuid`, `name`, `notes` | - | - |
| `feature` | `feature` | `tbl_features` | lookup | supported | `lookup` | `feature_name` | `feature_description`, `feature_name` | `feature_type_id` | - |
| `feature_property` | - | `tbl_feature_properties` | fact | not-a-target | - | - | `property_value` | - | - |
| `feature_type` | `feature_type` | `tbl_feature_types` | classifier | supported | `simple` | `feature_type_name` | `feature_type_description`, `feature_type_name` | - | - |
| `geochron_reference` | - | `tbl_geochron_refs` | bridge | not-a-target | - | - | - | - | - |
| `geochronology` | - | `tbl_geochronology` | fact | not-a-target | - | - | `lab_number`, `notes` | - | - |
| `horizon` | `horizon` | `tbl_horizons` | classifier | supported | `simple` | `horizon_name` | `description`, `horizon_name` | `method_id` | - |
| `identification_level` | `identification_level` | `tbl_identification_levels` | classifier | supported | `simple` | `identification_level_name` | `identification_level_abbrev`, `identification_level_name`, `notes` | - | - |
| `language` | `language` | `tbl_languages` | classifier | supported | `simple` | `language_name_english` | `language_name_english`, `language_name_native` | - | - |
| `lithology` | - | `tbl_lithology` | fact | not-a-target | - | - | `description`, `lower_boundary` | - | - |
| `location` | `location` | `tbl_locations` | lookup | supported | - | `location_name` | `location_name` | - | - |
| `location_type` | `location_type` | `tbl_location_types` | classifier | supported | `simple` | `location_type` | `description`, `location_type` | - | - |
| `master_dataset` | `master_dataset` | `tbl_dataset_masters` | lookup | supported | `lookup` | `master_name` | `master_name`, `master_notes`, `url` | - | - |
| `measured_value` | - | `tbl_measured_values` | fact | not-a-target | - | - | - | - | - |
| `measured_value_dimension` | - | `tbl_measured_value_dimensions` | fact | not-a-target | - | - | - | - | - |
| `method` | `method` | `tbl_methods` | classifier | supported | - | `method_name` | `description`, `method_abbrev_or_alt_name`, `method_name` | - | - |
| `method_group` | `method_group` | `tbl_method_groups` | classifier | supported | `simple` | `group_name` | `description`, `group_name` | - | - |
| `modification_type` | `modification_type` | `tbl_modification_types` | classifier | excluded | - | `modification_type_name` | `modification_type_description`, `modification_type_name` | - | The LLM-based strategy is registered as excluded. |
| `project` | `project` | `tbl_projects` | lookup | supported | `lookup` | `project_name` | `description`, `project_abbrev_name`, `project_name` | - | - |
| `project_stage` | `project_stage` | `tbl_project_stages` | classifier | supported | `simple` | `stage_name` | `description`, `stage_name` | - | - |
| `project_type` | `project_type` | `tbl_project_types` | classifier | supported | `simple` | `project_type_name` | `description`, `project_type_name` | - | - |
| `property_type` | `property_type` | `tbl_property_types` | classifier | supported | `simple` | `property_type_name` | `description`, `property_type_name` | `property_type_group_id` | - |
| `property_type_group` | `property_type_group` | `tbl_property_type_groups` | classifier | supported | `simple` | `property_type_group` | `description`, `property_type_group`, `property_type_group_abbrev` | - | - |
| `rdb` | - | `tbl_rdb` | fact | not-a-target | - | - | - | - | - |
| `rdb_code` | `rdb_code` | `tbl_rdb_codes` | classifier | supported | `simple` | `rdb_category` | `rdb_category`, `rdb_definition` | `rdb_system_id` | - |
| `rdb_system` | `rdb_system` | `tbl_rdb_systems` | lookup | supported | `lookup` | `rdb_system` | `rdb_system`, `rdb_system_uuid`, `rdb_version` | - | - |
| `record_type` | `record_type` | `tbl_record_types` | classifier | supported | `simple` | `record_type_name` | `record_type_description`, `record_type_name` | - | - |
| `relative_age_reference` | - | `tbl_relative_age_refs` | bridge | not-a-target | - | - | - | - | - |
| `relative_age_type` | `relative_age_type` | `tbl_relative_age_types` | classifier | supported | `simple` | `age_type` | `age_type`, `description` | - | - |
| `relative_ages` | `relative_age` | `tbl_relative_ages` | lookup | supported | `lookup` | `relative_age_name` | `abbreviation`, `description`, `notes`, `relative_age_name` | - | - |
| `relative_dating` | - | `tbl_relative_dates` | fact | not-a-target | - | - | `notes` | - | - |
| `sample` | - | `tbl_physical_samples` | fact | not-a-target | - | - | `date_sampled`, `sample_name` | - | - |
| `sample_alt_ref` | - | `tbl_sample_alt_refs` | fact | not-a-target | - | - | `alt_ref` | - | - |
| `sample_colour` | - | `tbl_sample_colours` | fact | not-a-target | - | - | - | - | - |
| `sample_coordinate` | - | `tbl_sample_coordinates` | fact | not-a-target | - | - | - | - | - |
| `sample_description` | - | `tbl_sample_descriptions` | fact | not-a-target | - | - | `description` | - | - |
| `sample_description_type` | `sample_description_type` | `tbl_sample_description_types` | classifier | supported | `simple` | `type_name` | `type_description`, `type_name` | - | - |
| `sample_dimension` | - | `tbl_sample_dimensions` | fact | not-a-target | - | - | - | - | - |
| `sample_feature` | - | `tbl_physical_sample_features` | bridge | not-a-target | - | - | - | - | - |
| `sample_group` | - | `tbl_sample_groups` | fact | not-a-target | - | - | `sample_group_description`, `sample_group_name` | - | - |
| `sample_group_coordinate` | - | `tbl_sample_group_coordinates` | fact | not-a-target | - | - | `position_accuracy` | - | - |
| `sample_group_description` | - | `tbl_sample_group_descriptions` | fact | not-a-target | - | - | `group_description` | - | - |
| `sample_group_description_type` | `sample_group_description_type` | `tbl_sample_group_description_types` | classifier | supported | `simple` | `type_name` | `type_description`, `type_name` | - | - |
| `sample_group_dimension` | - | `tbl_sample_group_dimensions` | fact | not-a-target | - | - | - | - | - |
| `sample_group_note` | - | `tbl_sample_group_notes` | fact | not-a-target | - | - | `note` | - | - |
| `sample_group_reference` | - | `tbl_sample_group_references` | bridge | not-a-target | - | - | - | - | - |
| `sample_group_sampling_context` | `sampling_context` | `tbl_sample_group_sampling_contexts` | classifier | supported | - | `sampling_context` | `description`, `sampling_context` | - | - |
| `sample_horizon` | - | `tbl_sample_horizons` | fact | not-a-target | - | - | - | - | - |
| `sample_location` | - | `tbl_sample_locations` | fact | not-a-target | - | - | `location` | - | - |
| `sample_location_type` | `sample_location_type` | `tbl_sample_location_types` | classifier | supported | `simple` | `location_type` | `location_type`, `location_type_description` | - | - |
| `sample_note` | - | `tbl_sample_notes` | fact | not-a-target | - | - | `note`, `note_type` | - | - |
| `sample_type` | `sample_type` | `tbl_sample_types` | classifier | supported | `simple` | `type_name` | `description`, `type_name` | - | - |
| `season` | `season` | `tbl_seasons` | classifier | supported | `simple` | `season_name` | `season_name`, `season_type` | `season_type_id` | - |
| `season_type` | `season_type` | `tbl_season_types` | classifier | supported | `simple` | `season_type` | `description`, `season_type` | - | - |
| `site` | `site` | `tbl_sites` | lookup | supported | - | `site_name` | `national_site_identifier`, `site_description`, `site_name` | - | - |
| `site_location` | - | `tbl_site_locations` | bridge | not-a-target | - | - | - | - | - |
| `site_natgridref` | - | `tbl_site_natgridrefs` | fact | not-a-target | - | - | `natgridref` | - | - |
| `site_other_record` | - | `tbl_site_other_records` | fact | not-a-target | - | - | `description` | - | - |
| `site_preservation_status` | - | `tbl_site_preservation_status` | fact | not-a-target | - | - | `assessment_type`, `description`, `preservation_status_or_threat` | - | - |
| `site_property` | - | `tbl_site_properties` | fact | not-a-target | - | - | `property_value` | - | - |
| `site_reference` | - | `tbl_site_references` | bridge | not-a-target | - | - | - | - | - |
| `site_site_type` | - | `tbl_site_site_types` | bridge | not-a-target | - | - | `notes` | - | - |
| `site_type` | `site_type` | `tbl_site_types` | classifier | supported | `simple` | `site_type` | `description`, `site_type`, `site_type_abbrev` | `site_type_group_id` | - |
| `site_type_group` | `site_type_group` | `tbl_site_type_groups` | classifier | supported | `simple` | `site_type_group` | `description`, `origin_code`, `origin_description`, `site_type_group`, `site_type_group_abbrev` | - | - |
| `species_association` | - | `tbl_species_associations` | fact | not-a-target | - | - | `referencing_type` | - | - |
| `species_association_type` | `species_association_type` | `tbl_species_association_types` | classifier | supported | `simple` | `association_type_name` | `association_description`, `association_type_name` | - | - |
| `submission` | - | `tbl_submissions` | fact | not-a-target | - | - | `author`, `data_types`, `issue_identifier`, `notes`, `source_name`, `submission_identifier`, `submission_name` | - | - |
| `submission_state` | `submission_state` | `tbl_submission_states` | classifier | supported | `simple` | `submission_state` | `note`, `submission_state` | - | - |
| `submission_task` | - | `tbl_submission_tasks` | fact | not-a-target | - | - | `notes` | - | - |
| `submission_task_type` | `submission_task_type` | `tbl_submission_task_types` | classifier | supported | `simple` | `action_task_name` | `action_task_name`, `description` | - | - |
| `taxa` | `taxon` | `tbl_taxa_tree_master` | classifier | excluded | - | `species` | `species` | - | The registered taxon strategy is a placeholder and is excluded. |
| `taxa_common_names` | `taxa_common_names` | `tbl_taxa_common_names` | lookup | supported | `lookup` | `common_name` | `common_name` | `taxon_id` | - |
| `taxa_measured_attributes` | - | `tbl_taxa_measured_attributes` | fact | not-a-target | - | - | `attribute_measure`, `attribute_type`, `attribute_units` | - | - |
| `taxa_reference_specimen` | - | `tbl_taxa_reference_specimens` | fact | not-a-target | - | - | `notes` | - | - |
| `taxa_seasonality` | - | `tbl_taxa_seasonality` | bridge | not-a-target | - | - | - | - | - |
| `taxa_synonyms` | `taxa_synonym` | `tbl_taxa_synonyms` | lookup | supported | `lookup` | `synonym` | `notes`, `reference_type`, `synonym`, `synonym_uuid` | - | - |
| `taxa_tree_author` | `taxa_tree_author` | `tbl_taxa_tree_authors` | classifier | supported | `simple` | `author_name` | `author_name` | - | - |
| `taxa_tree_family` | `taxa_tree_family` | `tbl_taxa_tree_families` | classifier | supported | `simple` | `family_name` | `family_name` | `order_id` | - |
| `taxa_tree_genus` | `taxa_tree_genus` | `tbl_taxa_tree_genera` | classifier | supported | `simple` | `genus_name` | `genus_name` | `family_id` | - |
| `taxa_tree_order` | `taxa_tree_order` | `tbl_taxa_tree_orders` | classifier | supported | `simple` | `order_name` | `order_name` | - | - |
| `taxonomic_order` | - | `tbl_taxonomic_order` | fact | not-a-target | - | - | - | - | - |
| `taxonomic_order_biblio` | - | `tbl_taxonomic_order_biblio` | bridge | not-a-target | - | - | - | - | - |
| `taxonomic_order_system` | `taxonomic_order_system` | `tbl_taxonomic_order_systems` | lookup | supported | `lookup` | `system_name` | `system_description`, `system_name`, `taxonomic_order_system_uuid` | - | - |
| `taxonomy_note` | - | `tbl_taxonomy_notes` | fact | not-a-target | - | `taxonomy_notes` | `taxonomy_notes` | - | - |
| `unit` | `unit` | `tbl_units` | classifier | supported | `simple` | `unit_name` | `description`, `unit_abbrev`, `unit_name` | - | - |
| `value_class` | `value_class` | `tbl_value_classes` | classifier | supported | `simple` | `name` | `description`, `name` | `value_type_id`, `method_id` | - |
| `value_qualifier` | `value_qualifier` | `tbl_value_qualifiers` | classifier | supported | `simple` | `symbol` | `description`, `symbol` | - | - |
| `value_qualifier_symbol` | - | `tbl_value_qualifier_symbols` | classifier | excluded | - | - | `symbol` | - | This alternate symbol maps to a value qualifier and has no standalone strategy. |
| `value_type` | `value_type` | `tbl_value_types` | classifier | supported | `simple` | `name` | `base_type`, `description`, `name` | - | - |
| `value_type_item` | `value_type_item` | `tbl_value_type_items` | classifier | supported | `simple` | `name` | `description`, `name` | `value_type_id` | - |
| `administrative_region` | `administrative_region` | - | service-only | supported | - | - | - | - | - |
| `country` | `country` | `tbl_locations` | service-only | supported | `simple` | `location_name` | - | - | - |
| `geonames` | `geonames` | - | service-only | excluded | - | - | - | - | The external GeoNames strategy is registered as excluded. |
<!-- reconciliation-inventory:rows:end -->
<!-- reconciliation-inventory:generated:end -->
