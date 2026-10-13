# Shape Shifter Target-Model Entity Register

> Auto-generated from SEAD Clearinghouse Extended v2.1.0
>
> This register describes Shape Shifter target-model metadata, not the entity types configured in SIMS or the identity records SIMS stores. The `identity_tracking` label below is a target-model property.
>
> For current SIMS operation support, see [`config/identity_policy.yml`](../../config/identity_policy.yml). An operation is enabled when its policy entry sets the corresponding `operations` flag to `true`. Policy entries do not show whether SIMS already stores identities for that type.

## Summary

| Category | Count |
|----------|-------|
| Total entities | 102 |
| Target-model `identity_tracking: tracked` | 5 |
| Provider-owned (children) | 37 |
| Shared metadata (reconciled) | 55 |
| Relationship (derived) | 5 |

---

## Entity Register

### Provider-Owned Root Entities

Target-model entities whose identity intent permits allocation. This does not prescribe the SIMS identity value format or allocator implementation.

| Entity | Target Table | Role | Business Key | Required | Reconciliation | Aggregate Parent | Domains |
|--------|--------------|------|--------------|----------|----------------|------------------|---------|
| analysis_entity | tbl_analysis_entities | bridge | - | yes | allocate | - | core |
| dataset | tbl_datasets | lookup | dataset_name | yes | allocate | - | core |
| sample | tbl_physical_samples | fact | sample_group_id, sample_name | yes | allocate | - | core |
| submission | tbl_submissions | fact | submission_uuid | no | allocate | - | core, provenance |
| submission_task | tbl_submission_tasks | fact | - | no | allocate | - | core, provenance |

### Provider-Owned Child Entities (Value Objects)

Target-model value objects owned by an aggregate root; this classification does not imply an independent SIMS identity.

| Entity | Target Table | Role | Business Key | Required | Reconciliation | Aggregate Parent | Domains |
|--------|--------------|------|--------------|----------|----------------|------------------|---------|
| abundance | tbl_abundances | fact | analysis_entity_id, taxon_id | no | - | analysis_entity | abundance, taxonomy |
| abundance_property | tbl_abundance_properties | fact | abundance_id, property_type_id, property_value | no | - | abundance | abundance |
| analysis_boolean_value | tbl_analysis_boolean_values | fact | analysis_value_id, qualifier, value | no | - | analysis_value | analysis |
| analysis_categorical_value | tbl_analysis_categorical_values | fact | analysis_value_id, value_type_item_id | no | - | analysis_value | analysis |
| analysis_dating_range | tbl_analysis_dating_ranges | fact | analysis_value_id, low_value, high_value, low_qualifier, high_qualifier | no | - | analysis_value | analysis, dating |
| analysis_identifier | tbl_analysis_identifiers | fact | analysis_value_id, value | no | - | analysis_value | analysis |
| analysis_integer_range | tbl_analysis_integer_ranges | fact | analysis_value_id, low_value, high_value, low_qualifier, high_qualifier | no | - | analysis_value | analysis |
| analysis_integer_value | tbl_analysis_integer_values | fact | analysis_value_id, qualifier, value | no | - | analysis_value | analysis |
| analysis_note | tbl_analysis_notes | fact | analysis_value_id, value | no | - | analysis_value | analysis |
| analysis_numerical_range | tbl_analysis_numerical_ranges | fact | analysis_value_id, value, low_qualifier, high_qualifier | no | - | analysis_value | analysis |
| analysis_numerical_value | tbl_analysis_numerical_values | fact | analysis_value_id, qualifier, value | no | - | analysis_value | analysis |
| analysis_taxon_count | tbl_analysis_taxon_counts | fact | analysis_value_id, taxon_id | no | - | analysis_value | analysis, taxonomy |
| analysis_value | tbl_analysis_values | fact | analysis_entity_id, value_class_id, analysis_value | no | - | analysis_entity | analysis |
| analysis_value_dimension | tbl_analysis_value_dimensions | fact | analysis_value_id, dimension_id | no | - | analysis_value | analysis |
| ecocode | tbl_ecocodes | fact | taxon_id, ecocode_definition_id | no | - | taxa_tree_master | taxonomy |
| feature_property | tbl_feature_properties | fact | feature_id, property_type_id, property_value | no | - | feature | excavation |
| geochronology | tbl_geochronology | fact | analysis_entity_id, lab_number | no | - | analysis_entity | dating |
| rdb | tbl_rdb | fact | taxon_id, location_id, rdb_code_id | no | - | taxa_tree_master | taxonomy |
| relative_dating | tbl_relative_dates | fact | analysis_entity_id, relative_age_id | no | - | analysis_entity | dating |
| sample_alt_ref | tbl_sample_alt_refs | fact | physical_sample_id, alt_ref_type_id, alt_ref | no | - | sample | sample-metadata |
| sample_colour | tbl_sample_colours | fact | physical_sample_id, colour_id | no | - | sample | sample-metadata |
| sample_coordinate | tbl_sample_coordinates | fact | physical_sample_id, coordinate_method_dimension_id | no | - | sample | spatial, sample-metadata |
| sample_description | tbl_sample_descriptions | fact | physical_sample_id, sample_description_type_id | no | - | sample | core, sample-metadata |
| sample_dimension | tbl_sample_dimensions | fact | physical_sample_id, dimension_id, method_id | no | - | sample | sample-metadata, physical-properties |
| sample_group_coordinate | tbl_sample_group_coordinates | fact | sample_group_id, coordinate_method_dimension_id | no | - | sample_group | spatial, sample-metadata |
| sample_group_dimension | tbl_sample_group_dimensions | fact | sample_group_id, dimension_id | no | - | sample_group | sample-metadata, physical-properties |
| sample_group_note | tbl_sample_group_notes | fact | sample_group_id, note | no | - | sample_group | sample-metadata |
| sample_group_reference | tbl_sample_group_references | fact | sample_group_id, biblio_id | no | - | sample_group | sample-metadata, provenance, bibliography |
| sample_horizon | tbl_sample_horizons | fact | physical_sample_id, horizon_id | no | - | sample | sample-metadata |
| sample_location | tbl_sample_locations | fact | physical_sample_id, sample_location_type_id, location | no | - | sample | sample-metadata, spatial |
| sample_note | tbl_sample_notes | fact | physical_sample_id, note_type, note | no | - | sample | sample-metadata |
| site_natgridref | tbl_site_natgridrefs | fact | site_id, method_id, natgridref | no | - | site | spatial |
| site_property | tbl_site_properties | fact | site_id, property_type_id, property_value | no | - | site | spatial |
| taxa_common_names | tbl_taxa_common_names | lookup | taxon_id, common_name | no | - | taxa_tree_master | taxonomy |
| taxa_measured_attributes | tbl_taxa_measured_attributes | fact | taxon_id, attribute_type, attribute_measure | no | - | taxa_tree_master | taxonomy |
| taxa_synonyms | tbl_taxa_synonyms | lookup | taxon_id, biblio_id, synonym | no | - | taxa_tree_master | taxonomy |
| taxonomic_order | tbl_taxonomic_order | fact | taxon_id, taxonomic_order_system_id, taxonomic_code | no | - | taxa_tree_master | taxonomy |

### Shared Metadata — Provider-Extensible

Shared reference entities with extensible target-model reconciliation intent; SIMS support is determined by its own configuration.

| Entity | Target Table | Role | Business Key | Required | Reconciliation | Aggregate Parent | Domains |
|--------|--------------|------|--------------|----------|----------------|------------------|---------|
| chronology | tbl_chronologies | lookup | chronology_name | no | reconcile-exact | - | dating |
| citation | tbl_biblio | lookup | title, year, authors | no | reconcile-fuzzy | - | provenance, bibliography |
| dating_lab | tbl_dating_labs | lookup | international_lab_id | no | reconcile-exact | - | dating |
| dating_material | tbl_dating_material | lookup | material_dated | no | reconcile-exact | - | dating |
| ecocode_system | tbl_ecocode_systems | lookup | name | no | reconcile-exact | - | taxonomy |
| feature | tbl_features | lookup | feature_type_id, feature_name | no | reconcile-exact | - | core, excavation |
| location | tbl_locations | lookup | location_type_id, location_name | yes | reconcile-exact | - | core, spatial |
| master_dataset | tbl_dataset_masters | lookup | master_name | no | reconcile-exact | - | core, provenance |
| project | tbl_projects | lookup | project_name | no | reconcile-exact | - | core, provenance |
| rdb_system | tbl_rdb_systems | lookup | location_id, rdb_system, rdb_version | no | reconcile-exact | - | taxonomy |
| relative_ages | tbl_relative_ages | lookup | relative_age_name | no | reconcile-exact | - | dating |
| sample_group | tbl_sample_groups | lookup | site_id, sample_group_name | yes | reconcile-exact | - | core |
| site | tbl_sites | lookup | site_name | yes | reconcile-exact | - | core, spatial |
| taxonomic_order_system | tbl_taxonomic_order_systems | lookup | system_name | no | reconcile-exact | - | taxonomy |

### Shared Metadata — SEAD-Administered

Target-model vocabularies marked for controlled lookup; SIMS does not manage consumer records.

| Entity | Target Table | Role | Business Key | Required | Reconciliation | Aggregate Parent | Domains |
|--------|--------------|------|--------------|----------|----------------|------------------|---------|
| abundance_element | tbl_abundance_elements | classifier | element_name | no | lookup-extensible | - | abundance |
| abundance_element_group | - | classifier | abundance_element_group_name | no | lookup-only | - | abundance |
| age_type | tbl_age_types | classifier | age_type | no | lookup-only | - | dating |
| alt_ref_type | tbl_alt_ref_types | classifier | alt_ref_type | no | lookup-only | - | sample-metadata |
| colour | tbl_colours | classifier | method_id, colour_name | no | lookup-only | - | sample-metadata |
| contact | tbl_contacts | lookup | - | no | lookup-only | - | contacts |
| contact_type | tbl_contact_types | classifier | contact_type_name | no | lookup-only | - | contacts |
| coordinate_method_dimension | tbl_coordinate_method_dimensions | classifier | method_id, dimension_id | no | lookup-only | - | spatial |
| data_provider | tbl_data_providers | lookup | data_provider_code | no | lookup-only | - | core, provenance |
| data_type | tbl_data_types | classifier | data_type_name | no | lookup-only | - | core |
| dating_uncertainty | tbl_dating_uncertainty | classifier | uncertainty | no | lookup-only | - | dating |
| dimension | tbl_dimensions | classifier | dimension_abbrev | no | lookup-only | - | spatial, physical-properties |
| ecocode_definition | tbl_ecocode_definitions | classifier | ecocode_group_id, name | no | lookup-only | - | taxonomy |
| ecocode_group | tbl_ecocode_groups | classifier | ecocode_system_id, name | no | lookup-only | - | taxonomy |
| feature_type | tbl_feature_types | classifier | feature_type_name | no | lookup-only | - | core, excavation |
| horizon | tbl_horizons | classifier | horizon_name, method_id | no | lookup-only | - | sample-metadata |
| identification_level | tbl_identification_levels | classifier | identification_level_abbrev | no | lookup-only | - | taxonomy, abundance |
| location_type | tbl_location_types | classifier | location_type | yes | lookup-only | - | core, spatial |
| method | tbl_methods | classifier | method_name | yes | lookup-extensible | - | core |
| method_group | tbl_method_groups | classifier | group_name | no | lookup-only | - | core, contacts |
| modification_type | tbl_modification_types | classifier | modification_type_name | no | lookup-only | - | abundance |
| project_stage | tbl_project_stages | classifier | stage_name | no | lookup-only | - | core, provenance |
| project_type | tbl_project_types | classifier | project_type_name | no | lookup-only | - | core, provenance |
| property_type | tbl_property_types | classifier | property_type_name | no | lookup-only | - | abundance, spatial |
| rdb_code | tbl_rdb_codes | classifier | rdb_system_id, rdb_category | no | lookup-only | - | taxonomy |
| relative_age_type | tbl_relative_age_types | classifier | age_type | no | lookup-only | - | dating |
| sample_description_type | tbl_sample_description_types | classifier | type_name | no | lookup-only | - | core, sample-metadata |
| sample_group_sampling_context | tbl_sample_group_sampling_contexts | classifier | sampling_context | no | lookup-only | - | core, sample-metadata |
| sample_location_type | tbl_sample_location_types | classifier | location_type | no | lookup-only | - | sample-metadata, spatial |
| sample_type | tbl_sample_types | classifier | type_name | yes | lookup-only | - | core |
| site_type | tbl_site_types | classifier | site_type | no | lookup-only | - | core, spatial |
| site_type_group | tbl_site_type_groups | classifier | site_type_group | no | lookup-only | - | core, spatial |
| submission_state | tbl_submission_states | classifier | submission_state | no | lookup-only | - | core, provenance |
| submission_task_type | tbl_submission_task_types | classifier | action_task_name | no | lookup-only | - | core, provenance |
| taxa_tree_master | tbl_taxa_tree_master | classifier | genus_id, species | no | lookup-extensible | - | taxonomy |
| unit | tbl_units | classifier | unit_name | no | lookup-only | - | core |
| value_class | tbl_value_classes | classifier | value_type_id, method_id, name | no | lookup-only | - | analysis |
| value_qualifier | tbl_value_qualifiers | classifier | symbol | no | lookup-only | - | sample-metadata, analysis |
| value_qualifier_symbol | tbl_value_qualifier_symbols | classifier | symbol | no | lookup-only | - | sample-metadata, analysis |
| value_type | tbl_value_types | classifier | name | no | lookup-only | - | analysis |
| value_type_item | tbl_value_type_items | classifier | value_type_id, name | no | lookup-only | - | analysis |

### Relationship Entities (Bridges)

Association entities whose target-model identity is derived from their foreign key references; they do not receive independent SIMS identities unless configured as tracked aggregates.

| Entity | Target Table | Role | Business Key | Required | Reconciliation | Aggregate Parent | Domains |
|--------|--------------|------|--------------|----------|----------------|------------------|---------|
| abundance_ident_level | tbl_abundance_ident_levels | bridge | abundance_id, identification_level_id | no | derive | - | taxonomy, abundance |
| abundance_modification | tbl_abundance_modifications | bridge | abundance_id, modification_type_id | no | derive | - | abundance |
| dataset_contact | tbl_dataset_contacts | bridge | dataset_id, contact_id, contact_type_id, event_date | no | derive | - | contacts, provenance |
| sample_feature | tbl_physical_sample_features | bridge | physical_sample_id, feature_id | no | derive | - | core, excavation |
| site_location | tbl_site_locations | bridge | site_id, location_id | yes | derive | - | core, spatial |


---

## Aggregate Boundaries

| Root Entity | Child Entities |
|-------------|----------------|
| **abundance** | abundance_property |
| **analysis_entity** | abundance, analysis_value, geochronology, relative_dating |
| **analysis_value** | analysis_boolean_value, analysis_categorical_value, analysis_dating_range, analysis_identifier, analysis_integer_range, analysis_integer_value, analysis_note, analysis_numerical_range, analysis_numerical_value, analysis_taxon_count, analysis_value_dimension |
| **feature** | feature_property |
| **sample** | sample_alt_ref, sample_colour, sample_coordinate, sample_description, sample_dimension, sample_horizon, sample_location, sample_note |
| **sample_group** | sample_group_coordinate, sample_group_dimension, sample_group_note, sample_group_reference |
| **site** | site_natgridref, site_property |
| **taxa_tree_master** | ecocode, rdb, taxa_common_names, taxa_measured_attributes, taxa_synonyms, taxonomic_order |

---

## Cross-Aggregate Associations

Bridge entities that connect different aggregate roots.

| Bridge | Connected Entities |
|--------|--------------------|
| abundance_ident_level | abundance ↔ identification_level |
| abundance_modification | abundance ↔ modification_type |
| dataset_contact | dataset ↔ contact ↔ contact_type |
| sample_feature | sample ↔ feature |
| site_location | site ↔ location |

---

## Reconciliation Strategies

| Strategy | Description | Entities |
|----------|-------------|----------|
| allocate | Fresh identity allocation per submission | analysis_entity, dataset, sample, submission, submission_task |
| reconcile-exact | Exact business key match; allocate new if no match | chronology, dating_lab, dating_material, ecocode_system, feature, location, master_dataset, project, rdb_system, relative_ages, sample_group, site, taxonomic_order_system |
| reconcile-fuzzy | Fuzzy matching with human review for ambiguous cases | citation |
| lookup-only | Must match existing record; reject if not found | abundance_element_group, age_type, alt_ref_type, colour, contact, contact_type, coordinate_method_dimension, data_provider, data_type, dating_uncertainty, dimension, ecocode_definition, ecocode_group, feature_type, horizon, identification_level, location_type, method_group, modification_type, project_stage, project_type, property_type, rdb_code, relative_age_type, sample_description_type, sample_group_sampling_context, sample_location_type, sample_type, site_type, site_type_group, submission_state, submission_task_type, unit, value_class, value_qualifier, value_qualifier_symbol, value_type, value_type_item |
| lookup-extensible | Match existing; propose new values for admin review | abundance_element, method, taxa_tree_master |
| derive | Identity composed from foreign key references | abundance_ident_level, abundance_modification, dataset_contact, sample_feature, site_location |
