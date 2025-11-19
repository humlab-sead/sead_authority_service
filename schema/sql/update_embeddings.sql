/****************************************************************************************************
** Procedure:   authority.update_all_embeddings
** Description: Dynamically updates embeddings for all embedding tables in authority schema
** Note:        This procedure discovers all *_embeddings tables in the authority schema and calls
**              the corresponding update function for each table. It assumes a naming convention:
**                         Table: authority.{entity}_embeddings
**               Update function: authority.update_{entity}_embeddings()
*****************************************************************************************************/

create or replace procedure authority.update_all_embeddings( p_force_update boolean default false )
language plpgsql
as $$
declare
    table_record record;
    entity_name text;
    update_function text;
    table_count integer := 0;
    rows_updated integer := 0;
    total_rows integer := 0;
    start_time timestamp;
    end_time timestamp;
    duration interval;
    function_exists boolean;
begin
    raise notice 'Starting update of all embeddings in authority schema...';
    raise notice 'Force update mode: %', p_force_update;
    start_time := clock_timestamp();

    -- Loop through all embedding tables in the authority schema
    for table_record in
        select 
            schemaname,
            tablename,
            regexp_replace(tablename, '_embeddings$', '') as entity_name
        from pg_tables
        where schemaname = 'authority'
          and tablename like '%_embeddings'
        order by tablename
    loop
        -- Extract entity name by removing '_embeddings' suffix
        entity_name := table_record.entity_name;
        update_function := format('authority.update_%s_embeddings', entity_name);
        
        -- Check if the update function exists
        select exists(
            select 1 
            from pg_proc p
            join pg_namespace n on p.pronamespace = n.oid
            where n.nspname = 'authority'
              and p.proname = format('update_%s_embeddings', entity_name)
        ) into function_exists;
        
        if function_exists then
            raise notice 'Updating embeddings for table: % using function: %', table_record.tablename, update_function;
            
            begin
                -- Call the update function with force_update parameter
                if p_force_update then
                    execute format('SELECT authority.%I(true)', update_function)
                        into rows_updated;
                else
                    execute format('SELECT authority.%I(false)', update_function)
                        into rows_updated;
                end if;
                
                total_rows := total_rows + rows_updated;
                table_count := table_count + 1;
                
                raise notice '  → Updated % rows in %', rows_updated, table_record.tablename;
            exception
                when others then
                    raise warning 'Failed to update embeddings for %: %', table_record.tablename, sqlerrm;
            end;
        else
            raise notice 'Skipping % - update function % does not exist', table_record.tablename, update_function;
        end if;
    end loop;

    end_time := clock_timestamp();
    duration := end_time - start_time;
    
    raise notice '═══════════════════════════════════════════════════════════════';
    raise notice 'Completed embedding updates:';
    raise notice '  Tables processed: %', table_count;
    raise notice '  Total rows updated: %', total_rows;
    raise notice '  Duration: % seconds', extract(epoch from duration)::numeric(10,3);
    raise notice '═══════════════════════════════════════════════════════════════';
end;
$$;

comment on procedure authority.update_all_embeddings(boolean) is
    'Dynamically updates embeddings for all *_embeddings tables in the authority schema by calling their corresponding update functions. Set p_force_update=true to regenerate all embeddings.';


/**************************************************************************************************
** Function:    authority.get_embedding_status
** Description: Returns status information for all embedding tables
** Note:        Dynamically discovers ID columns and source tables from pg_constraint
**************************************************************************************************/

create or replace function authority.get_embedding_status()
returns table (
    table_name text,
    total_records bigint,
    embeddings_present bigint,
    embeddings_missing bigint,
    coverage_percent numeric
)
language plpgsql
as $$
declare
    table_record record;
    entity_name text;
    id_column text;
    source_table text;
    query text;
begin
    -- Loop through all embedding tables
    for table_record in
        select tablename
        from pg_tables
        where schemaname = 'authority'
          and tablename like '%_embeddings'
        order by tablename
    loop
        entity_name := regexp_replace(table_record.tablename, '_embeddings$', '');
        
        -- Dynamically find the ID column and source table from foreign key constraint
        select a.attname::text, format('%I.%I', nf.nspname, cf.relname)
        into id_column, source_table
        from pg_constraint con
        join pg_class c on con.conrelid = c.oid
        join pg_namespace n on c.relnamespace = n.oid
        join pg_attribute a on a.attrelid = c.oid and a.attnum = con.conkey[1]
        join pg_class cf on con.confrelid = cf.oid
        join pg_namespace nf on cf.relnamespace = nf.oid
        where n.nspname = 'authority'
          and c.relname = table_record.tablename
          and con.contype = 'f'  -- foreign key
        limit 1;
        
        -- Skip if we couldn't determine the mapping
        if id_column is null or source_table is null then
            raise notice 'Skipping % - could not determine ID column or source table', table_record.tablename;
            continue;
        end if;
        
        -- Build dynamic query to get statistics
        query := format($q$
            select 
                '%1$s'::text as table_name,
                (select count(*) from %2$s) as total_records,
                (select count(*) from authority.%1$I where emb is not null) as embeddings_present,
                (select count(*) from %2$s s 
                 where not exists (
                     select 1 from authority.%1$I e 
                     where e.%3$I = s.%3$I and e.emb is not null
                 )) as embeddings_missing,
                case 
                    when (select count(*) from %2$s) = 0 then 0
                    else round(
                        (select count(*) from authority.%1$I where emb is not null)::numeric / 
                        (select count(*) from %2$s)::numeric * 100, 2
                    )
                end as coverage_percent
        $q$, 
            table_record.tablename, source_table, id_column
        );
        
        return query execute query;
    end loop;
end;
$$;

comment on function authority.get_embedding_status() is
    'Returns coverage statistics for all embedding tables in the authority schema. Automatically discovers table relationships via foreign keys.';


-- =====================================================================================
-- Usage examples:
-- =====================================================================================
-- Update only missing embeddings (default):
--   CALL authority.update_all_embeddings();
--
-- Force update all embeddings (regenerate everything):
--   CALL authority.update_all_embeddings(true);
--
-- Check embedding coverage status:
--   SELECT * FROM authority.get_embedding_status();
-- =====================================================================================
