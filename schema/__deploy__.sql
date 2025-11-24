\set quiet on
\set echo none
\set verbosity terse
set client_min_messages = warning;
begin;
\i schema/sql/authority.sql
\i schema/sql/utility.sql
\i schema/generated/bibliographic_reference.sql
\i schema/generated/data_type_group.sql
\i schema/generated/data_type.sql
\i schema/generated/dating_uncertainty.sql
\i schema/generated/feature.sql
\i schema/generated/feature_type.sql
\i schema/generated/location.sql
\i schema/generated/location_type.sql
\i schema/generated/method_group.sql
\i schema/generated/method.sql
\i schema/generated/modification_type.sql
\i schema/generated/record_type.sql
\i schema/generated/relative_age.sql
\i schema/generated/relative_age_type.sql
\i schema/generated/sample_description_type.sql
\i schema/generated/sample_group_description_type.sql
\i schema/generated/sample_location_type.sql
\i schema/generated/sample_type.sql
\i schema/generated/sampling_context.sql
\i schema/generated/site.sql
\i schema/generated/taxa_synonym.sql
\i schema/generated/taxa_tree_author.sql
\i schema/generated/taxa_tree_family.sql
\i schema/generated/taxa_tree_genus.sql
\i schema/generated/taxa_tree_master.sql
\i schema/generated/taxa_tree_order.sql
\i schema/generated/taxonomic_order_system.sql
\i schema/generated/taxonomy_note.sql
\i schema/generated/semantic-bibliographic_reference.sql
\i schema/generated/semantic-data_type.sql
\i schema/generated/semantic-feature_type.sql
\i schema/generated/semantic-location.sql
\i schema/generated/semantic-method.sql
\i schema/generated/semantic-modification_type.sql
\i schema/generated/semantic-record_type.sql
\i schema/generated/semantic-site.sql
\i schema/generated/semantic-taxa_synonym.sql
\i schema/generated/semantic-taxa_tree_author.sql
\i schema/generated/semantic-taxa_tree_family.sql
\i schema/generated/semantic-taxa_tree_genus.sql
\i schema/generated/semantic-taxa_tree_master.sql
\i schema/generated/semantic-taxa_tree_order.sql
\i schema/generated/semantic-taxonomic_order_system.sql
\i schema/generated/semantic-taxonomy_note.sql
commit;
