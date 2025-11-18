\set quiet on
\set echo none
\set verbosity terse
set client_min_messages = warning;
begin;
\i sql/01_authority.sql
\i sql/01_utility.sql
\i sql/02_location.sql
\i sql/03_site.sql
\i sql/04_feature_type.sql
\i sql/05_bibliographic_reference.sql
\i sql/06_method.sql
\i sql/07_data_type.sql
\i sql/08_record_type.sql
\i sql/09_taxa_tree_author.sql
\i sql/10_taxa_tree_order.sql
\i sql/11_taxa_tree_family.sql
\i sql/12_taxa_tree_genus.sql
\i sql/13_taxa_tree_master.sql
\i sql/14_taxonomic_order_system.sql
\i sql/15_taxonomy_note.sql
\i sql/16_taxonomic_order.sql
\i sql/17_taxa_synonym.sql
\i sql/49_refresh_materialized_views.sql
commit;
