\set quiet on
\set echo none
\set verbosity terse
set client_min_messages = warning;
begin;
\i schema/sql/authority.sql
\i schema/sql/utility.sql
\i schema/generated/bibliographic_reference.sql
\i schema/generated/data_type.sql
\i schema/generated/feature_type.sql
\i schema/generated/location.sql
\i schema/generated/method.sql
\i schema/generated/modification_type.sql
\i schema/generated/record_type.sql
\i schema/generated/site.sql
\i schema/generated/taxa_synonym.sql
\i schema/generated/taxa_tree_author.sql
\i schema/generated/taxa_tree_family.sql
\i schema/generated/taxa_tree_genus.sql
\i schema/generated/taxa_tree_master.sql
\i schema/generated/taxa_tree_order.sql
\i schema/generated/taxonomic_order_system.sql
\i schema/generated/taxonomy_note.sql
commit;
