
drop schema if exists authority cascade;

create schema if not exists authority;

create extension if not exists unaccent;
create extension if not exists pg_trgm;
create extension if not exists postgis;

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
