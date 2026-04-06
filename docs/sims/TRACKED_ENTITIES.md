# SIMS Tracked Entity Register

> **Checklist coverage:** A1 (entity enumeration), A2 (aggregate boundaries), A3 (associations), A4 (shared-metadata classification), C1 (business keys).

> **Policy sync notice.** This file mirrors `config/identity_policy.yml`. When onboarding a new entity, update both files together — add the entity to Section 2 here and add its policy block to `identity_policy.yml`.

## 1. Scope

This document enumerates the SEAD entities relevant to the SIMS identity system. The primary source is the Shape Shifter target model (`sead_standard_model.yml`, 49 entities) cross-referenced with the SEAD ERD color-coded classification.

| ERD Color | Meaning | SIMS Relevance |
|-----------|---------|----------------|
| Green | Aggregate root / tracked entity | Full identity tracking (UUID + PK) |
| Blue | Value object / aggregate child | Inherits parent identity, no independent UUID |
| Yellow | Classifier / lookup | Reconciled by business key, no UUID |
| Pink | Association / bridge | Identity derived from referenced entities |

### Terminology

| Term            | Definition                                                   | Source                           |
|-----------------|--------------------------------------------------------------|----------------------------------|
| Provider-owned  | Data originating from a provider submission                  | REQUIREMENTS.md §Entity Subtypes |
| Shared metadata | Reference data shared across providers                       | REQUIREMENTS.md §Entity Subtypes |
| Relationship    | Association connecting two or more entities                  | REQUIREMENTS.md §Entity Subtypes |
| TM Role         | Target model role (`fact`, `lookup`, `classifier`, `bridge`) | sead_standard_model.yml          |
| Business key    | The `identity_columns` field from the target model           | sead_standard_model.yml          |

---

## 1.5 SIMS Identity Policy Coverage

The table below shows every entity registered in `config/identity_policy.yml` with its policy subtype, key flags, and implementation phase. Entities not listed here fall under the `defaults` block in the policy file (`shared_metadata`, `allow_allocation: false`, `auto_confirm: false`).

| Entity | Policy Subtype | accept_uuid | allow_allocation | auto_confirm | Phase |
|--------|---------------|:-----------:|:----------------:|:------------:|-------|
| site | provider_owned | no | yes | yes | **Phase 1 – live** |
| sample_group | provider_owned | no | yes | yes | **Phase 1 – live** |
| sample | provider_owned | no | yes | yes | **Phase 1 – live** |
| analysis_entity | provider_owned | no | yes | yes | **Phase 1 – live** |
| dataset | provider_owned | no | yes | yes | **Phase 1 – live** |
| taxa_tree_master | shared_metadata | yes | no | no | Phase 2+ – planned |
| feature_type | shared_metadata | yes | no | no | Phase 2+ – planned |
| method | shared_metadata | yes | no | no | Phase 2+ – planned |
| data_type | shared_metadata | yes | no | no | Phase 2+ – planned † |
| unit | shared_metadata | yes | no | no | Phase 2+ – planned † |
| sample_dimension | relationship | no | no | no | Phase 2+ – planned |
| abundance | relationship | no | no | no | Phase 2+ – planned |

† `data_type` and `unit` are registered in `identity_policy.yml` but are not yet present in the Shape Shifter target model (`sead_standard_model.yml`). They are reserved for a future model extension.

---

## 2. Entity Register (A1 + C1)

All 49 target model entities, grouped by SIMS subtype.

### 2.1 Provider-Owned Entities

These entities contain observation or measurement data submitted by research providers. Each submission allocates fresh identities.

#### Aggregate Roots

| # | Entity          | Target Table            | TM Role | Business Key                 | Required | Domains |
|---|-----------------|-------------------------|---------|------------------------------|----------|---------|
| 1 | sample          | tbl_physical_samples    | fact    | sample_group_id, sample_name | yes      | core    |
| 2 | analysis_entity | tbl_analysis_entities   | bridge  | physical_sample_id, dataset_id | yes    | core    |

> **Note on analysis_entity.** The target model classifies `analysis_entity` as a bridge (sample ↔ dataset), but it serves as the observation context — the parent aggregate for abundance, geochronology, and relative-dating records. SIMS treats it as a **provider-owned entity** with full identity tracking (UUID + PK).

#### Aggregate Children (Value Objects)

These entities are owned by their parent aggregate root. They receive integer PKs but not independent UUIDs; they are included in the parent's content hash for change detection.

| # | Entity | Target Table | TM Role | Business Key | Parent | Required |
|---|--------|-------------|---------|--------------|--------|----------|
| 3 | sample_description | tbl_sample_descriptions | fact | physical_sample_id, sample_description_type_id | sample | no |
| 4 | sample_coordinate | tbl_sample_coordinates | fact | physical_sample_id, coordinate_method_dimension_id | sample | no |
| 5 | sample_alt_ref | tbl_sample_alt_refs | fact | physical_sample_id, alt_ref_type_id, alt_ref | sample | no |
| 6 | sample_dimension | tbl_sample_dimensions | fact | physical_sample_id, dimension_id, method_id | sample | no |
| 7 | abundance | tbl_abundances | fact | analysis_entity_id, taxon_id | analysis_entity | no |
| 8 | relative_dating | tbl_relative_dates | fact | analysis_entity_id, relative_age_id | analysis_entity | no |
| 9 | geochronology | tbl_geochronology | fact | analysis_entity_id, lab_number | analysis_entity | no |
| 10 | abundance_property | tbl_abundance_properties | fact | abundance_id, property_type_id, property_value | abundance | no |

### 2.2 Shared Metadata — Provider-Extensible

Reference data shared across providers. Providers may submit new entries, which are reconciled against existing SEAD records. If no match is found, a new entry is allocated.

| #  | Entity            | Target Table          | TM Role | Business Key                    | Required | Domains          |
|----|-------------------|-----------------------|---------|---------------------------------|----------|------------------|
| 11 | location          | tbl_locations         | lookup  | location_type_id, location_name | yes      | core             |
| 12 | site              | tbl_sites             | lookup  | site_name                       | yes      | core             |
| 13 | sample_group      | tbl_sample_groups     | lookup  | site_id, sample_group_name      | yes      | core             |
| 14 | dataset           | tbl_datasets          | lookup  | dataset_name                    | yes      | core             |
| 15 | master_dataset    | tbl_dataset_masters   | lookup  | master_name                     | no       | core, provenance |
| 16 | project           | tbl_projects          | lookup  | project_name                    | no       | core, provenance |
| 17 | citation          | tbl_biblio            | lookup  | title, year, authors            | no       | provenance       |
| 18 | chronology        | tbl_chronologies      | lookup  | chronology_name                 | no       | dating           |
| 19 | dating_material   | tbl_dating_material   | lookup  | dating_material_name            | no       | dating           |
| 20 | relative_ages     | tbl_relative_ages     | lookup  | relative_age_name               | no       | dating           |
| 21 | dating_lab        | tbl_dating_labs       | lookup  | international_lab_id            | no       | dating           |
| 22 | feature           | tbl_features          | lookup  | feature_type_id, feature_name   | no       | core, excavation |

> **Gaps:**
> - `contact` has no `identity_columns` in the target model. Treated as SEAD-administered classifier (§2.3).

### 2.3 Shared Metadata — SEAD-Administered

Controlled vocabularies maintained by SEAD administrators. Providers reference existing entries by business key. Default reconciliation: exact match only; unmatched values rejected.

| # | Entity | Target Table | TM Role | Business Key | Required | Domains |
|---|--------|-------------|---------|--------------|----------|---------|
| 23 | location_type | tbl_location_types | classifier | location_type | no | core |
| 24 | site_type_group | tbl_site_type_groups | classifier | site_type_group | no | core |
| 25 | site_type | tbl_site_types | classifier | site_type | no | core |
| 26 | sample_type | tbl_sample_types | classifier | type_name | yes | core |
| 27 | sample_description_type | tbl_sample_description_types | classifier | type_name | no | sample-metadata |
| 28 | dimension | tbl_dimensions | classifier | dimension_abbrev | no | spatial |
| 29 | coordinate_method_dimension | tbl_coordinate_method_dimensions | classifier | method_id, dimension_id | no | spatial |
| 30 | alt_ref_type | tbl_alt_ref_types | classifier | alt_ref_type | no | sample-metadata |
| 31 | method | tbl_methods | classifier | method_name | yes | core |
| 32 | method_group | tbl_method_groups | classifier | group_name | no | core |
| 33 | abundance_element | tbl_abundance_elements | classifier | element_name | no | abundance |
| 34 | abundance_element_group | *(none)* | classifier | abundance_element_group_name | no | abundance |
| 35 | modification_type | tbl_modification_types | classifier | modification_type_name | no | abundance |
| 36 | identification_level | tbl_identification_levels | classifier | identification_level_abbrev | no | taxonomy |
| 37 | taxa_tree_master | tbl_taxa_tree_master | classifier | genus_id, species | no | taxonomy |
| 38 | age_type | tbl_age_types | classifier | age_type | no | dating |
| 39 | relative_age_type | tbl_relative_age_types | classifier | age_type | no | dating |
| 40 | dating_uncertainty | tbl_dating_uncertainty | classifier | uncertainty | no | dating |
| 41 | contact_type | tbl_contact_types | classifier | contact_type_name | no | contacts |
| 42 | feature_type | tbl_feature_types | classifier | feature_type_name | no | excavation |
| 43 | contact | tbl_contacts | lookup | *(no business key)* | no | contacts |

> **Notes:**
> - `abundance_element_group` has no `target_table` — it exists only as a Shape Shifter grouping concept, not as a SEAD database table.
> - `taxa_tree_master` is the canonical SEAD taxonomy. While SEAD-administered, new taxa are periodically added through a curated process. Its aggregate includes `taxa_common_names` (§3).
> - `contact` has no `identity_columns` in the target model. Treated as SEAD-administered; matching is by manual curation rather than business key.
> - Some classifiers may accept provider-proposed values in future phases (marked `lookup-extensible` in §5). For now, all are treated as pre-populated.

### 2.4 Relationships (Bridges)

Join entities connecting two or more tracked entities. Identity is derived from the referenced entity keys.

| # | Entity | Target Table | TM Role | Business Key | Referenced Entities | Required |
|---|--------|-------------|---------|--------------|---------------------|----------|
| 44 | site_location | tbl_site_locations | bridge | site_id, location_id | site, location | no |
| 45 | abundance_modification | tbl_abundance_modifications | bridge | abundance_id, modification_type_id | abundance, modification_type | no |
| 46 | abundance_ident_level | tbl_abundance_ident_levels | bridge | abundance_id, identification_level_id | abundance, identification_level | no |
| 47 | dataset_contact | tbl_dataset_contacts | bridge | dataset_id, contact_id, contact_type_id | dataset, contact, contact_type | no |
| 48 | sample_feature | tbl_physical_sample_features | bridge | physical_sample_id, feature_id | sample, feature | no |
| 49 | taxa_common_names | tbl_taxa_common_names | lookup | taxon_id, common_name | taxa_tree_master | no |

> **Note on taxa_common_names.** Classified as a value object within the `taxa_tree_master` aggregate (§3). Listed here to maintain the 49-entity count from the target model.

---

## 3. Aggregate Boundaries (A2)

Each aggregate root owns value-object child tables. Child rows have no independent identity need — they are created, updated, and deleted as part of the root entity. For change detection (Group E), the content hash includes all child rows.

### Target Model Aggregates

| Aggregate Root  | Value-Object Children                                                         | Notes                              |
|-----------------|-------------------------------------------------------------------------------|------------------------------------|
| sample          | sample_description, sample_coordinate, sample_alt_ref, sample_dimension       | 4 child entity types               |
| analysis_entity | abundance, relative_dating, geochronology                                     | 3 observation entity types         |
| abundance       | abundance_property                                                            | Sub-aggregate within analysis_entity |
| taxa_tree_master| taxa_common_names                                                             | Shared-metadata aggregate          |

> **Nested aggregates.** The analysis_entity aggregate has two levels: analysis_entity → abundance → abundance_property. Abundance, relative_dating, and geochronology are value objects of analysis_entity. Abundance_property is a value object of abundance (grandchild of analysis_entity). The content hash for analysis_entity includes all descendant rows.

### Additional Children from ERD (not in target model)

These tables appear as blue (value object) in the ERD but are not yet in the Shape Shifter target model. They are future candidates for aggregate inclusion.

| Aggregate Root | ERD Children (not yet modeled) |
|---------------|-------------------------------|
| site | tbl_site_preservation_status, tbl_site_images, tbl_site_other_records, tbl_site_references, tbl_site_natgridrefs, tbl_site_properties |
| sample_group | tbl_sample_group_descriptions, tbl_sample_group_notes, tbl_sample_group_references, tbl_sample_group_dimensions, tbl_sample_group_coordinates, tbl_sample_group_images, tbl_lithology |
| sample | tbl_sample_notes, tbl_sample_images, tbl_sample_colours, tbl_sample_horizons, tbl_sample_locations |
| taxa_tree_master | tbl_taxonomy_notes, tbl_taxa_synonyms, tbl_taxa_reference_specimens, tbl_taxa_measured_attributes, tbl_taxa_images, tbl_taxa_seasonality |
| dataset | tbl_dataset_submissions |
| analysis_entity | tbl_analysis_entity_dimensions, tbl_analysis_entity_ages, tbl_analysis_entity_prep_methods |
| geochronology | tbl_geochron_refs |

### Excluded from Aggregates

These child tables are intentionally excluded because they represent cross-aggregate associations, not ownership:

- `tbl_site_locations` — association (site ↔ location)
- `tbl_dataset_contacts` — association (dataset ↔ contact ↔ contact_type)
- `tbl_physical_sample_features` — association (sample ↔ feature)

---

## 4. Cross-Aggregate Associations (A3)

Associations are many-to-many or cross-aggregate links. Their identity is derived from the referenced entities.

### Target Model Associations

| Association Table            | Entity A  | Entity B             | Additional FK | Notes                             |
|------------------------------|-----------|----------------------|---------------|-----------------------------------|
| tbl_site_locations           | site      | location             | —             | Canonical example (ASSESSMENT.md) |
| tbl_abundance_modifications  | abundance | modification_type    | —             |                                   |
| tbl_abundance_ident_levels   | abundance | identification_level | —             |                                   |
| tbl_dataset_contacts         | dataset   | contact              | contact_type  | 3-way association                 |
| tbl_physical_sample_features | sample    | feature              | —             |                                   |

### ERD Associations (not in target model)

| Association Table        | Entity A | Entity B               | Notes                     |
|--------------------------|----------|------------------------|---------------------------|
| tbl_ecocodes             | taxon    | ecocode_definition     | Ecological classification |
| tbl_species_associations | taxon    | taxon                  | Self-referential          |
| tbl_rdb                  | taxon    | rdb_code + location    | 3-way association         |
| tbl_taxonomic_order      | taxon    | taxonomic_order_system | Ordering context          |

---

## 5. Shared Metadata Reconciliation (A4)

For each shared-metadata entity, the reconciliation strategy determines how provider-submitted references are matched against existing SEAD records.

### Strategies

| Strategy | Definition | Applies To |
|----------|------------|------------|
| **reconcile-exact** | Match on full business key; allocate new if no match. | Provider-extensible lookups with stable naming |
| **reconcile-fuzzy** | Match with similarity threshold; flag ambiguous results for review. | Entities with variable naming across providers |
| **lookup-only** | Must match existing record; reject submission if not found. | SEAD-administered classifiers |
| **lookup-extensible** | Match existing; if not found, queue proposed value for admin review. | Classifiers that accept provider proposals |

### Provider-Extensible Lookups

| Entity            | Strategy        | Matching Rule                     | Notes                                       |
|-------------------|-----------------|-----------------------------------|---------------------------------------------|
| location          | reconcile-exact | [location_type_id, location_name] | Providers routinely submit new locations    |
| site              | reconcile-exact | [site_name]                       | Providers create sites; duplicates possible |
| sample_group      | reconcile-exact | [site_id, sample_group_name]      | Scoped to site; low collision risk          |
| dataset           | reconcile-exact | [dataset_name]                    | One dataset per submission typical          |
| master_dataset    | reconcile-exact | [master_name]                     | Shared across datasets                      |
| project           | reconcile-exact | [project_name]                    | Shared across datasets                      |
| citation          | reconcile-fuzzy | [title, year, authors]            | Naming varies across providers              |
| chronology        | reconcile-exact | [chronology_name]                 | Regional dating frameworks                  |
| dating_material   | reconcile-exact | [dating_material_name]            | Small controlled set                        |
| relative_ages     | reconcile-exact | [relative_age_name]               | Archaeological period names                 |
| dating_lab        | reconcile-exact | [international_lab_id]            | Lab IDs are standardized                    |
| feature           | reconcile-exact | [feature_type_id, feature_name]   | Per site-context; low collision risk        |

### SEAD-Administered Classifiers

| Entity                      | Strategy          | Notes                                        |
|-----------------------------|-------------------|----------------------------------------------|
| location_type               | lookup-only       | Fixed vocabulary                             |
| site_type_group             | lookup-only       | Fixed vocabulary                             |
| site_type                   | lookup-only       | Fixed vocabulary                             |
| sample_type                 | lookup-only       | Fixed vocabulary                             |
| sample_description_type     | lookup-only       | Fixed vocabulary                             |
| dimension                   | lookup-only       | Measurement dimensions                       |
| coordinate_method_dimension | lookup-only       | Method-dimension pairs                       |
| alt_ref_type                | lookup-only       | Reference type codes                         |
| method                      | lookup-extensible | Providers may propose new analytical methods |
| method_group                | lookup-only       | Method grouping                              |
| abundance_element           | lookup-extensible | Providers may use new element types          |
| abundance_element_group     | lookup-only       | Grouping concept (no db table)               |
| modification_type           | lookup-only       | Fixed vocabulary                             |
| identification_level        | lookup-only       | Taxonomic precision levels                   |
| taxa_tree_master            | lookup-extensible | New taxa added through curated process       |
| age_type                    | lookup-only       | Date notation systems                        |
| relative_age_type           | lookup-only       | Period type systems                          |
| dating_uncertainty          | lookup-only       | Fixed vocabulary                             |
| contact_type                | lookup-only       | Role classifications                         |
| feature_type                | lookup-only       | Feature classifications                      |
| contact                     | lookup-only       | No business key; matched by manual curation  |

> **Decision point:** The three `lookup-extensible` classifiers (method, abundance_element, taxa_tree_master) need a defined proposal workflow. Deferred to Phase 3 (D1–D3).

---

## 6. Entities Not Yet Tracked

The following SEAD tables are visible in the ERD but absent from the Shape Shifter target model. They are candidates for future SIMS inclusion.

### Ecocode System
- tbl_ecocodes, tbl_ecocode_definitions, tbl_ecocode_groups, tbl_ecocode_systems

### RDB (Red Data Book)
- tbl_rdb, tbl_rdb_codes, tbl_rdb_systems

### Analysis Value Subtypes
- tbl_analysis_categorical_values, tbl_analysis_boolean_values, tbl_analysis_integer_values
- tbl_analysis_numerical_values, tbl_analysis_numerical_ranges, tbl_analysis_dating_ranges
- tbl_analysis_identifiers, tbl_analysis_notes, tbl_analysis_taxon_counts
- tbl_analysis_value_dimensions, tbl_measured_values, tbl_measured_value_dimensions

### Taxonomic Extensions
- tbl_taxonomic_order, tbl_taxonomic_order_systems, tbl_taxa_synonyms
- tbl_taxa_reference_specimens, tbl_taxa_images, tbl_taxa_seasonality
- tbl_taxa_measured_attributes, tbl_taxonomy_notes

### Site / Sample Group / Sample Extensions
- tbl_site_preservation_status, tbl_site_images, tbl_site_other_records, tbl_site_references, tbl_site_natgridrefs, tbl_site_properties
- tbl_sample_group_descriptions, tbl_sample_group_notes, tbl_sample_group_references, tbl_sample_group_dimensions, tbl_sample_group_coordinates, tbl_sample_group_images, tbl_lithology
- tbl_sample_notes, tbl_sample_images, tbl_sample_colours, tbl_sample_horizons, tbl_sample_locations

### Other
- tbl_dataset_submissions, tbl_geochron_refs

> **Recommendation:** Most of these are aggregate children (blue in ERD) that inherit their parent's identity. Only domain-specific systems (ecocodes, RDB) and analysis value subtypes would need independent classification if SIMS scope expands.

---

## 7. Open Questions

### Resolved

1. **Contact business key.** `contact` has no `identity_columns` in the target model. **Decision:** Treat as SEAD-administered classifier with no business key; matching is by manual curation. Moved to §2.3.

2. **Analysis entity classification.** **Decision:** Treat as a provider-owned entity (§2.1) with full UUID tracking, not a bridge. It is the aggregate root for all observation data (abundance, relative_dating, geochronology).

3. **Taxa common names ownership.** **Decision:** Value object within the `taxa_tree_master` aggregate. Moved to §3.

5. **Observation aggregate scope.** **Decision:** Abundance, relative_dating, and geochronology are value objects within the analysis_entity aggregate. They do not receive independent UUIDs. The same applies to measured_value (not yet in target model). The content hash for analysis_entity includes all descendant observation rows.

### Open

4. **Classifier extensibility workflow.** The three `lookup-extensible` classifiers (method, abundance_element, taxa_tree_master) need a proposal-and-review workflow defined in Phase 3 (D1–D3).

---

## 8. Summary

| Category                              | Count  |
|---------------------------------------|--------|
| Provider-owned aggregate roots        | 2      |
| Provider-owned aggregate children     | 8      |
| Shared metadata — provider-extensible | 12     |
| Shared metadata — SEAD-administered   | 21     |
| Relationships (bridges + other)       | 6      |
| **Total (target model)**              | **49** |

| Reconciliation Strategy   | Count |
|---------------------------|-------|
| allocate (fresh identity) | 10    |
| reconcile-exact           | 11    |
| reconcile-fuzzy           | 1     |
| lookup-only               | 18    |
| lookup-extensible         | 3     |
| derive (bridge/child)     | 3     |
| derive (bridge)           | 6     |

---

## Cross-References

- [REQUIREMENTS.md](./REQUIREMENTS.md) — entity subtypes and identity type definitions
- [DESIGN_VIEW.md](./DESIGN_VIEW.md) — Resolve → Allocate → Map decision flow
- [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md) — DDL and identity allocation structures
- [ASSESSMENT.md](./ASSESSMENT.md) — readiness checklist items A1–A4, C1
