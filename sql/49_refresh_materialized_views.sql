-- =====================================================================================
-- Procedure: authority.refresh_all_materialized_views
-- Description: Dynamically refreshes all materialized views in the authority schema
-- =====================================================================================

create or replace procedure authority.refresh_all_materialized_views()
language plpgsql
as $$
declare
    view_record record;
    view_count integer := 0;
    start_time timestamp;
    end_time timestamp;
    duration interval;
begin
    raise notice 'Starting refresh of all materialized views in authority schema...';
    start_time := clock_timestamp();

    -- Loop through all materialized views in the authority schema
    for view_record in
        select schemaname, matviewname
        from pg_matviews
        where schemaname = 'authority'
        order by matviewname
    loop
        raise notice 'Refreshing materialized view: %.%', view_record.schemaname, view_record.matviewname;
        
        -- Execute refresh for each materialized view
        execute format('REFRESH MATERIALIZED VIEW %I.%I', 
                      view_record.schemaname, 
                      view_record.matviewname);
        
        view_count := view_count + 1;
    end loop;

    end_time := clock_timestamp();
    duration := end_time - start_time;
    
    raise notice 'Completed refresh of % materialized view(s) in % seconds', 
                 view_count, 
                 extract(epoch from duration)::numeric(10,3);
end;
$$;

comment on procedure authority.refresh_all_materialized_views() is
    'Dynamically refreshes all materialized views in the authority schema by querying pg_matviews';

-- =====================================================================================
-- Optional: Create a concurrent refresh procedure (does not lock the view)
-- Note: Requires materialized views to have a unique index
-- =====================================================================================

create or replace procedure authority.refresh_all_materialized_views_concurrent()
language plpgsql
as $$
declare
    view_record record;
    view_count integer := 0;
    start_time timestamp;
    end_time timestamp;
    duration interval;
    refresh_failed boolean := false;
begin
    raise notice 'Starting concurrent refresh of all materialized views in authority schema...';
    start_time := clock_timestamp();

    -- Loop through all materialized views in the authority schema
    for view_record in
        select schemaname, matviewname
        from pg_matviews
        where schemaname = 'authority'
        order by matviewname
    loop
        raise notice 'Refreshing materialized view (concurrent): %.%', 
                     view_record.schemaname, view_record.matviewname;
        
        begin
            -- Execute concurrent refresh for each materialized view
            execute format('REFRESH MATERIALIZED VIEW CONCURRENTLY %I.%I', 
                          view_record.schemaname, 
                          view_record.matviewname);
            
            view_count := view_count + 1;
        exception
            when others then
                raise warning 'Failed to refresh %.% concurrently: %. Falling back to standard refresh.', 
                              view_record.schemaname, view_record.matviewname, sqlerrm;
                
                -- Fall back to standard refresh
                execute format('REFRESH MATERIALIZED VIEW %I.%I', 
                              view_record.schemaname, 
                              view_record.matviewname);
                
                view_count := view_count + 1;
                refresh_failed := true;
        end;
    end loop;

    end_time := clock_timestamp();
    duration := end_time - start_time;
    
    if refresh_failed then
        raise notice 'Completed refresh of % materialized view(s) in % seconds (some views fell back to standard refresh)', 
                     view_count, 
                     extract(epoch from duration)::numeric(10,3);
    else
        raise notice 'Completed concurrent refresh of % materialized view(s) in % seconds', 
                     view_count, 
                     extract(epoch from duration)::numeric(10,3);
    end if;
end;
$$;

comment on procedure authority.refresh_all_materialized_views_concurrent() is
    'Dynamically refreshes all materialized views in the authority schema using CONCURRENTLY when possible. Falls back to standard refresh if concurrent refresh fails (requires unique index).';

-- =====================================================================================
-- Usage examples:
-- =====================================================================================
-- Standard refresh (locks views during refresh):
--   CALL authority.refresh_all_materialized_views();
--
-- Concurrent refresh (does not lock views, requires unique indexes):
--   CALL authority.refresh_all_materialized_views_concurrent();
-- =====================================================================================
