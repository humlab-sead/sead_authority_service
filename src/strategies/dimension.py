from typing import Any, Tuple

import psycopg

from .query import QueryProxy

from .interface import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "dimension",
    "display_name": "Dimensions",
    "id_field": "dimension_id",
    "label_field": "label",
    "abbreviation_field": "dimension_abbreviation",
    "properties": [
        {
            "id": "dimension_abbreviation",
            "name": "Dimension Abbreviation",
            "type": "string",
            "description": "Abbreviation for the dimension used",
        }
    ],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_label_sql": """
            select
                s.dimension_id,
                s.dimension_name as label,
                greatest(
                    case when s.norm_label = pq.q then 1.0 else similarity(s.norm_label, pq.q) end,
                    0.0001
                ) as name_sim
            from (
                select  dimension_id,
                        dimension_name,
                        authority.immutable_unaccent(lower(dimension_name))::text as norm_label
                from tbl_dimensions
            ) as s
            cross join (
                select authority.immutable_unaccent(lower(%(q)s))::text as q
            ) as pq
            where s.norm_label % pq.q
            order by name_sim desc, 2
            limit %(n)s;
        """,
        "get_details": """
            select 
                d.dimension_id as "ID", 
                d.dimension_name as "Name", 
                d.dimension_description as "Description", 
                d.dimension_abbrev as "Abbreviation",
                u.unit_name as "Unit", 
                u.unit_abbrev as "Unit Abbreviation", mg.group_name as "Method Group"
            from tbl_dimensions as d
            join tbl_units u using (unit_id)
            left join tbl_method_groups mg using (method_group_id)
            where dimension_id = %(id)s
    """,
        "fetch_dimension_by_abbreviation": """
        select dimension_id, label, 1.0 as name_sim
        from authority.dimensions
        where dimension_abbreviation = %(abbreviation)s
        limit 1
    """,
    },
}


class DimensionQueryProxy(QueryProxy):
    def __init__(self, specification: StrategySpecification, cursor: psycopg.AsyncCursor) -> None:
        super().__init__(specification, cursor)

    async def fetch_dimension_by_abbreviation(self, abbreviation: str) -> list[dict]:
        """Fetch dimension by abbreviation"""
        sql: str = self.get_sql_queries().get("fetch_dimension_by_abbreviation", "")
        await self.cursor.execute(sql, {"abbreviation": abbreviation})
        row: Tuple[Any, ...] | None = await self.cursor.fetchone()
        return [dict(row)] if row else []


@Strategies.register(key="dimension")
class DimensionReconciliationStrategy(ReconciliationStrategy):
    """Dimension-specific reconciliation with place names and coordinates"""

    def __init__(self):
        super().__init__(SPECIFICATION, DimensionQueryProxy)
