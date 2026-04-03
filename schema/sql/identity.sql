-- Entity Metadata Functions (Reference Patterns)
--
-- These functions were extracted from the retired aggregate model design
-- (now in docs/ignore/AGGREGATE_MODEL_DESIGN.md). They implement useful
-- algorithms — topological depth, submission validation, allocation ordering —
-- but reference tables (entity_types, aggregate_definitions, entity_dependencies)
-- that do not yet exist.
--
-- Adapt when entity metadata storage is finalized (see ASSESSMENT.md Gap 8:
-- SIMS entity registry vs. Shape Shifter target model).

-- 1. Calculate Topological Depth
--
-- Iteratively assigns depth_level to each entity type: 0 for entities with
-- no parents, 1 for children of roots, etc. Standard BFS-style leveling.

CREATE OR REPLACE FUNCTION sead_utility.calculate_topological_depth()
RETURNS TABLE(
    entity_type_id INTEGER,
    entity_type_key TEXT,
    depth_level INTEGER
) AS $$
DECLARE
    v_max_depth INTEGER := 0;
    v_affected_rows INTEGER;
BEGIN
    UPDATE sead_utility.entity_types SET depth_level = NULL;

    FOR v_max_depth IN 0..100 LOOP
        IF v_max_depth = 0 THEN
            UPDATE sead_utility.entity_types et
            SET depth_level = 0
            WHERE et.depth_level IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM sead_utility.entity_dependencies d
                  WHERE d.child_entity_type_id = et.entity_type_id
              );
        ELSE
            UPDATE sead_utility.entity_types et
            SET depth_level = v_max_depth
            WHERE et.depth_level IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM sead_utility.entity_dependencies d
                  WHERE d.child_entity_type_id = et.entity_type_id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM sead_utility.entity_dependencies d
                  JOIN sead_utility.entity_types et_parent
                      ON d.parent_entity_type_id = et_parent.entity_type_id
                  WHERE d.child_entity_type_id = et.entity_type_id
                    AND (et_parent.depth_level IS NULL OR et_parent.depth_level >= v_max_depth)
              );
        END IF;

        GET DIAGNOSTICS v_affected_rows = ROW_COUNT;
        EXIT WHEN v_affected_rows = 0;
    END LOOP;

    RETURN QUERY
    SELECT et.entity_type_id, et.entity_type_key, et.depth_level
    FROM sead_utility.entity_types et
    WHERE et.status = 'active'
    ORDER BY et.depth_level NULLS LAST, et.entity_type_key;
END;
$$ LANGUAGE plpgsql;


-- 2. Validate Entity Submission
--
-- Checks that a submission includes all required parent entity types for
-- every child entity type listed. Returns a single validation result row.

CREATE OR REPLACE FUNCTION sead_utility.validate_entity_submission(
    p_submission_uuid UUID,
    p_entity_types TEXT[]
)
RETURNS TABLE(
    is_valid BOOLEAN,
    error_code TEXT,
    error_message TEXT,
    missing_parent_types TEXT[]
) AS $$
DECLARE
    v_child_type TEXT;
    v_parent_types TEXT[];
    v_missing_parents TEXT[];
BEGIN
    FOREACH v_child_type IN ARRAY p_entity_types LOOP
        SELECT ARRAY_AGG(DISTINCT et_parent.entity_type_key)
        INTO v_parent_types
        FROM sead_utility.entity_types et_child
        JOIN sead_utility.entity_dependencies d
            ON et_child.entity_type_id = d.child_entity_type_id
        JOIN sead_utility.entity_types et_parent
            ON d.parent_entity_type_id = et_parent.entity_type_id
        WHERE et_child.entity_type_key = v_child_type
          AND d.is_required = TRUE
          AND et_parent.status = 'active';

        IF v_parent_types IS NOT NULL THEN
            SELECT ARRAY_AGG(parent_type)
            INTO v_missing_parents
            FROM UNNEST(v_parent_types) AS parent_type
            WHERE parent_type != ALL(p_entity_types);

            IF v_missing_parents IS NOT NULL THEN
                RETURN QUERY SELECT
                    FALSE,
                    'MISSING_PARENT_ENTITIES'::TEXT,
                    format('Entity type "%s" requires parent types %s which are missing from submission',
                           v_child_type, v_missing_parents::TEXT),
                    v_missing_parents;
                RETURN;
            END IF;
        END IF;
    END LOOP;

    RETURN QUERY SELECT TRUE, NULL::TEXT, NULL::TEXT, NULL::TEXT[];
END;
$$ LANGUAGE plpgsql;


-- 3. Get Allocation Order
--
-- Returns entity types in topological order: depth-first, aggregates before
-- dependents, sorted by priority within each level.

CREATE OR REPLACE FUNCTION sead_utility.get_allocation_order(
    p_entity_types TEXT[]
)
RETURNS TABLE(
    allocation_order INTEGER,
    entity_type_key TEXT,
    entity_type_id INTEGER,
    table_name TEXT,
    is_aggregate BOOLEAN,
    depth_level INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ROW_NUMBER() OVER (ORDER BY et.depth_level,
                                    CASE WHEN et.is_aggregate THEN 0 ELSE 1 END,
                                    a.aggregate_priority NULLS LAST,
                                    et.entity_type_key)::INTEGER AS allocation_order,
        et.entity_type_key,
        et.entity_type_id,
        et.table_name,
        et.is_aggregate,
        et.depth_level
    FROM sead_utility.entity_types et
    LEFT JOIN sead_utility.aggregate_definitions a
        ON et.entity_type_id = a.entity_type_id
    WHERE et.entity_type_key = ANY(p_entity_types)
      AND et.status = 'active'
    ORDER BY allocation_order;
END;
$$ LANGUAGE plpgsql;
