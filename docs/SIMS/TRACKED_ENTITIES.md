# SIMS Entity Register

> Auto-generated from SEAD Clearinghouse Extended v2.1.0
>
> This register reflects target-model metadata. Compare it with `config/identity_policy.yml` when reviewing current Authority Service rollout state.

## Summary

| Category                     | Count |
|------------------------------|-------|
| Total entities               | 51    |
| Provider-owned (tracked)     | 2     |
| Provider-owned (children)    | 9     |
| Shared metadata (reconciled) | 35    |
| Relationship (derived)       | 5     |

---

## Entity Register

### Provider-Owned Root Entities

Entities receiving fresh UUID + sequential PK allocation per submission.

| Entity          | Target Table          | Role   | Business Key                 | Required | Reconciliation | Aggregate Parent | Domains |
|-----------------|-----------------------|--------|------------------------------|----------|----------------|------------------|---------|
| analysis_entity | tbl_analysis_entities | bridge | -                            | yes      | allocate       | -                | core    |
| sample          | tbl_physical_samples  | fact   | sample_group_id, sample_name | yes      | allocate       | -                | core    |

### Provider-Owned Child Entities (Value Objects)

Value objects owned by an aggregate root; identity inherited from parent context.

| Entity             | Target Table             | Role   | Business Key                                       | Required | Reconciliation | Aggregate Parent | Domains                              |
|--------------------|--------------------------|--------|----------------------------------------------------|----------|----------------|------------------|--------------------------------------|
| abundance          | tbl_abundances           | fact   | analysis_entity_id, taxon_id                       | no       | -              | analysis_entity  | abundance, taxonomy                  |
| abundance_property | tbl_abundance_properties | fact   | abundance_id, property_type_id, property_value     | no       | -              | abundance        | abundance                            |
| geochronology      | tbl_geochronology        | fact   | analysis_entity_id, lab_number                     | no       | -              | analysis_entity  | dating                               |
| relative_dating    | tbl_relative_dates       | fact   | analysis_entity_id, relative_age_id                | no       | -              | analysis_entity  | dating                               |
| sample_alt_ref     | tbl_sample_alt_refs      | fact   | physical_sample_id, alt_ref_type_id, alt_ref       | no       | -              | sample           | sample-metadata                      |
| sample_coordinate  | tbl_sample_coordinates   | fact   | physical_sample_id, coordinate_method_dimension_id | no       | -              | sample           | spatial, sample-metadata             |
| sample_description | tbl_sample_descriptions  | fact   | physical_sample_id, sample_description_type_id     | no       | -              | sample           | core, sample-metadata                |
| sample_dimension   | tbl_sample_dimensions    | fact   | physical_sample_id, dimension_id, method_id        | no       | -              | sample           | sample-metadata, physical-properties |
| taxa_common_names  | tbl_taxa_common_names    | lookup | taxon_id, common_name                              | no       | -              | taxa_tree_master | taxonomy                             |

### Shared Metadata — Provider-Extensible

Shared metadata matched by business key; providers may propose new entries.

| Entity          | Target Table        | Role   | Business Key                    | Required | Reconciliation  | Aggregate Parent | Domains                  |
|-----------------|---------------------|--------|---------------------------------|----------|-----------------|------------------|--------------------------|
| chronology      | tbl_chronologies    | lookup | chronology_name                 | no       | reconcile-exact | -                | dating                   |
| citation        | tbl_biblio          | lookup | title, year, authors            | no       | reconcile-fuzzy | -                | provenance, bibliography |
| dataset         | tbl_datasets        | lookup | dataset_name                    | yes      | reconcile-exact | -                | core                     |
| dating_lab      | tbl_dating_labs     | lookup | international_lab_id            | no       | reconcile-exact | -                | dating                   |
| dating_material | tbl_dating_material | lookup | dating_material_name            | no       | reconcile-exact | -                | dating                   |
| feature         | tbl_features        | lookup | feature_type_id, feature_name   | no       | reconcile-exact | -                | core, excavation         |
| location        | tbl_locations       | lookup | location_type_id, location_name | yes      | reconcile-exact | -                | core, spatial            |
| master_dataset  | tbl_dataset_masters | lookup | master_name                     | no       | reconcile-exact | -                | core, provenance         |
| project         | tbl_projects        | lookup | project_name                    | no       | reconcile-exact | -                | core, provenance         |
| relative_ages   | tbl_relative_ages   | lookup | relative_age_name               | no       | reconcile-exact | -                | dating                   |
| sample_group    | tbl_sample_groups   | lookup | site_id, sample_group_name      | yes      | reconcile-exact | -                | core                     |
| site            | tbl_sites           | lookup | site_name                       | yes      | reconcile-exact | -                | core, spatial            |

### Shared Metadata — SEAD-Administered

Controlled vocabularies maintained by SEAD administrators; providers reference existing entries.

| Entity                      | Target Table                     | Role       | Business Key                 | Required | Reconciliation    | Aggregate Parent | Domains                      |
|-----------------------------|----------------------------------|------------|------------------------------|----------|-------------------|------------------|------------------------------|
| abundance_element           | tbl_abundance_elements           | classifier | element_name                 | no       | lookup-extensible | -                | abundance                    |
| abundance_element_group     | -                                | classifier | abundance_element_group_name | no       | lookup-only       | -                | abundance                    |
| age_type                    | tbl_age_types                    | classifier | age_type                     | no       | lookup-only       | -                | dating                       |
| alt_ref_type                | tbl_alt_ref_types                | classifier | alt_ref_type                 | no       | lookup-only       | -                | sample-metadata              |
| contact                     | tbl_contacts                     | lookup     | -                            | no       | lookup-only       | -                | contacts                     |
| contact_type                | tbl_contact_types                | classifier | contact_type_name            | no       | lookup-only       | -                | contacts                     |
| coordinate_method_dimension | tbl_coordinate_method_dimensions | classifier | method_id, dimension_id      | no       | lookup-only       | -                | spatial                      |
| data_type                   | tbl_data_types                   | classifier | data_type_name               | no       | lookup-only       | -                | core                         |
| dating_uncertainty          | tbl_dating_uncertainty           | classifier | uncertainty                  | no       | lookup-only       | -                | dating                       |
| dimension                   | tbl_dimensions                   | classifier | dimension_abbrev             | no       | lookup-only       | -                | spatial, physical-properties |
| feature_type                | tbl_feature_types                | classifier | feature_type_name            | no       | lookup-only       | -                | core, excavation             |
| identification_level        | tbl_identification_levels        | classifier | identification_level_abbrev  | no       | lookup-only       | -                | taxonomy, abundance          |
| location_type               | tbl_location_types               | classifier | location_type                | yes      | lookup-only       | -                | core, spatial                |
| method                      | tbl_methods                      | classifier | method_name                  | yes      | lookup-extensible | -                | core                         |
| method_group                | tbl_method_groups                | classifier | group_name                   | no       | lookup-only       | -                | core, contacts               |
| modification_type           | tbl_modification_types           | classifier | modification_type_name       | no       | lookup-only       | -                | abundance                    |
| relative_age_type           | tbl_relative_age_types           | classifier | age_type                     | no       | lookup-only       | -                | dating                       |
| sample_description_type     | tbl_sample_description_types     | classifier | type_name                    | no       | lookup-only       | -                | core, sample-metadata        |
| sample_type                 | tbl_sample_types                 | classifier | type_name                    | yes      | lookup-only       | -                | core                         |
| site_type                   | tbl_site_types                   | classifier | site_type                    | no       | lookup-only       | -                | core, spatial                |
| site_type_group             | tbl_site_type_groups             | classifier | site_type_group              | no       | lookup-only       | -                | core, spatial                |
| taxa_tree_master            | tbl_taxa_tree_master             | classifier | genus_id, species            | no       | lookup-extensible | -                | taxonomy                     |
| unit                        | tbl_units                        | classifier | unit_name                    | no       | lookup-only       | -                | core                         |

### Relationship Entities (Bridges)

Association entities whose identity is derived from their foreign key references.

| Entity                 | Target Table                 | Role   | Business Key                            | Required | Reconciliation | Aggregate Parent | Domains              |
|------------------------|------------------------------|--------|-----------------------------------------|----------|----------------|------------------|----------------------|
| abundance_ident_level  | tbl_abundance_ident_levels   | bridge | abundance_id, identification_level_id   | no       | derive         | -                | taxonomy, abundance  |
| abundance_modification | tbl_abundance_modifications  | bridge | abundance_id, modification_type_id      | no       | derive         | -                | abundance            |
| dataset_contact        | tbl_dataset_contacts         | bridge | dataset_id, contact_id, contact_type_id | no       | derive         | -                | contacts, provenance |
| sample_feature         | tbl_physical_sample_features | bridge | physical_sample_id, feature_id          | no       | derive         | -                | core, excavation     |
| site_location          | tbl_site_locations           | bridge | site_id, location_id                    | yes      | derive         | -                | core, spatial        |


---

## Aggregate Boundaries

| Root Entity          | Child Entities                                                          |
|----------------------|-------------------------------------------------------------------------|
| **abundance**        | abundance_property                                                      |
| **analysis_entity**  | abundance, geochronology, relative_dating                               |
| **sample**           | sample_alt_ref, sample_coordinate, sample_description, sample_dimension |
| **taxa_tree_master** | taxa_common_names                                                       |

---

## Cross-Aggregate Associations

Bridge entities that connect different aggregate roots.

| Bridge                 | Connected Entities               |
|------------------------|----------------------------------|
| abundance_ident_level  | abundance ↔ identification_level |
| abundance_modification | abundance ↔ modification_type    |
| dataset_contact        | dataset ↔ contact ↔ contact_type |
| sample_feature         | sample ↔ feature                 |
| site_location          | site ↔ location                  |

---

## Reconciliation Strategies

| Strategy          | Description                                          | Entities                                                                                                                                                                                                                                                                                                                     |
|-------------------|------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| allocate          | Fresh identity allocation per submission             | analysis_entity, sample                                                                                                                                                                                                                                                                                                      |
| reconcile-exact   | Exact business key match; allocate new if no match   | chronology, dataset, dating_lab, dating_material, feature, location, master_dataset, project, relative_ages, sample_group, site                                                                                                                                                                                              |
| reconcile-fuzzy   | Fuzzy matching with human review for ambiguous cases | citation                                                                                                                                                                                                                                                                                                                     |
| lookup-only       | Must match existing record; reject if not found      | abundance_element_group, age_type, alt_ref_type, contact, contact_type, coordinate_method_dimension, data_type, dating_uncertainty, dimension, feature_type, identification_level, location_type, method_group, modification_type, relative_age_type, sample_description_type, sample_type, site_type, site_type_group, unit |
| lookup-extensible | Match existing; propose new values for admin review  | abundance_element, method, taxa_tree_master                                                                                                                                                                                                                                                                                  |
| derive            | Identity composed from foreign key references        | abundance_ident_level, abundance_modification, dataset_contact, sample_feature, site_location                                                                                                                                                                                                                                |
