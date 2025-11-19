
drop schema if exists authority cascade;

create schema if not exists authority;

create extension if not exists unaccent;
create extension if not exists pg_trgm;
create extension if not exists postgis;
create extension if not exists vector; -- apt install -y postgresql-16-pgvector
create extension if not exists ai cascade;

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

/***************************************************************************************************
 ** Function  authority.compute_text_embedding
 ** What      Computes a 768-dimensional embedding vector from input text using pgai
 ** Usage     SELECT authority.compute_text_embedding('example text');
 ** Note      Uses pgai extension with configurable embedding provider
 **           
 **           SETUP INSTRUCTIONS:
 **           
 **           1. Install pgai extension:
 **              CREATE EXTENSION IF NOT EXISTS ai CASCADE;
 **           
 **           2. Configure embedding provider (choose one):
 **           
 **              a) Ollama (local, free):
 **                 SELECT ai.ollama_embed('nomic-embed-text', 'test');
 **                 -- Set OLLAMA_HOST if needed: ALTER DATABASE mydb SET ai.ollama_host = 'http://localhost:11434';
 **           
 **              b) OpenAI (hosted, requires API key):
 **                 SELECT set_config('ai.openai_api_key', 'sk-...', false);
 **                 SELECT ai.openai_embed('text-embedding-3-small', 'test');
 **           
 **              c) Voyage AI:
 **                 SELECT set_config('ai.voyage_api_key', '...', false);
 **                 SELECT ai.voyage_embed('voyage-3', 'test');
 **           
 **           3. Update function below to use your chosen provider
 **           
 **           4. Verify dimension matches your model (768 for most models)
 ****************************************************************************************************/

drop function if exists authority.compute_text_embedding(text);

create or replace function authority.compute_text_embedding(input_text text)
returns vector(768) language plpgsql volatile
as $$
begin
  -- OPTION 1: Ollama (local, free) - uncomment and configure model name
  return ai.ollama_embed('nomic-embed-text', input_text);
  
  -- OPTION 2: OpenAI (hosted, requires API key)
  -- return ai.openai_embed('text-embedding-3-small', input_text);
  
  -- OPTION 3: Voyage AI (hosted, requires API key)
  -- return ai.voyage_embed('voyage-3', input_text);
  
  -- STUB: Returns zero vector until you uncomment one of the options above
  raise warning 'authority.compute_text_embedding: Uncomment pgai provider in function definition';
  return array_fill(0.0, array[768])::vector(768);
end;
$$;

comment on function authority.compute_text_embedding(text) is
  'Computes 768-dimensional text embedding using pgai extension. Configure provider by uncommenting appropriate ai.* function call.';

-- drop table if exists authority.entities cascade;

-- create table authority.entities (
--     entity_name text primary key,
--     display_name text not null,
--     table_name text not null,
--     id_column text not null,
--     label_column text not null,
--     description_column text,
--     alternate_identity_column text
-- );

/*
with known_entities (entity_name, display_name, table_name, id_column, label_column, description_column, alternate_identity_column) as (
    values 
    ('bibliographic_reference', 'Bibliographic Reference', 'tbl_biblio', 'biblio_id', 'full_reference', 'title', 'doi'),
    ('data_type', 'Data Type', 'tbl_data_types', 'data_type_id', 'data_type_name', 'definition', null),
    ('data_type_group', 'Data Type Group', 'tbl_data_type_groups', 'data_type_group_id', 'data_type_group_name', 'description', null),
    ('dating_uncertainty', 'Dating Uncertainty', 'tbl_dating_uncertainty', 'dating_uncertainty_id', 'uncertainty', 'description', null),
    ('feature_type', 'Feature Type', 'tbl_feature_types', 'feature_type_id', 'feature_type_name', 'feature_type_description', null),
    ('feature', 'Feature', 'tbl_features', 'feature_id', 'feature_name', 'feature_description', null),
    ('location_type', 'Location Type', 'tbl_location_types', 'location_type_id', 'location_type', 'description', null),
    ('location', 'Location', 'tbl_locations', 'location_id', 'location_name', null, null),
    ('method_group', 'Method Group', 'tbl_method_groups', 'method_group_id', 'group_name', 'description', null),
    ('method', 'Method', 'tbl_methods', 'method_id', 'method_name', 'description', 'method_abbrev_or_alt_name'),
    ('modification_type', 'Modification Type', 'tbl_modification_types', 'modification_type_id', 'modification_type_name', 'modification_type_description', null),
    ('record_type', 'Record Type', 'tbl_record_types', 'record_type_id', 'record_type_name', 'record_type_description', null),
    ('relative_age_type', 'Relative Age Type', 'tbl_relative_age_types', 'relative_age_type_id', 'age_type', 'description', null),
    ('relative_age', 'Relative Age', 'tbl_relative_ages', 'relative_age_id', 'relative_age', 'description', null),
    ('site', 'Site', 'tbl_sites', 'site_id', 'site_name', 'site_description', 'national_site_identifier'),
    ('sampling_context', 'Sampling Context', 'tbl_sample_group_sampling_contexts', 'sampling_context_id', 'sampling_context', 'description', null),
    ('sample_group_description_type', 'Sample Group Description Type', 'tbl_sample_group_description_types', 'sample_group_description_type_id', 'type_name', 'type_description', null),
    ('sample_description_type', 'Sample Description Type', 'tbl_sample_description_types', 'sample_description_type_id', 'type_name', 'type_description', null),
    ('sample_location_type', 'Sample Location Type', 'tbl_sample_location_types', 'sample_location_type_id', 'location_type', 'location_type_description', null),
    ('sample_type', 'Sample Type', 'tbl_sample_types', 'sample_type_id', 'type_name', 'description', null),
    ('taxa_tree_master', 'Taxa', 'tbl_taxa_tree_master', 'taxon_id', 'species', null, null)
)
    insert into authority.entities(entity_name, display_name, table_name, id_column, label_column, description_column, alternate_identity_column)
    select entity_name, display_name, table_name, id_column, label_column, description_column, alternate_identity_column
    from known_entities
    on conflict (entity_name) do nothing;


with sead_table as (
    select pt.tablename, sead_utility.table_name_to_entity_name(pt.tablename) as entity_name
    from sead_utility.sead_columns pt
    where pt.schemaname = 'public'
    and pt.tablename like 'tbl_%'
), embedding_tables as (
    select et.tablename, regexp_replace(et.tablename, '_embeddings$', '') as entity_name
    from pg_tables et
    where et.schemaname = 'authority'   
    and et.tablename like '%_embeddings'
)
select *
from sead_table st
full outer join embedding_tables et using (entity_name)
order by st.tablename


select *
from sead_utility.table_columns

select table_name,
       authority.snake_to_title(sead_utility.table_name_to_entity_name(table_name)) as display_name
       column_name as id_column,
       sead_utility.table_name_to_entity_name(table_name) as entity_name,

from sead_utility.table_columns tc
where table_schema = 'public'
  and table_name like 'tbl_%'
  and is_pk = 'YES'
  and not table_name ~* 'tbl_(aggregate|mcr|tephra|dendro|ceramics|isotope|ecocode|imported|lithology|horizon|updates|text|temp|project|colour|.*refs|.*image)'
  and not exists (
    -- Exclude tables that contain columns indicating they are data tables, not authority tables
    select 1
    from sead_utility.table_columns sc
    where sc.table_schema = tc.table_schema
      and sc.table_name = tc.table_name
      and sc.column_name in ('analysis_entity_id', 'analysis_value_id', 'abundance_id', 'dataset_id', 'physical_sample_id', 'sample_group_id')
  )
  and exists (
    -- Ensure that this table is referenced by at least one FK from another table
    select 1
    from sead_utility.table_columns sc
    where sc.table_schema = tc.table_schema
      and sc.table_name <> tc.table_name
      and sc.column_name = tc.column_name
      and sc.fk_table_name = tc.table_name
      and sc.is_fk = 'YES'
  )
order by table_name;
*/