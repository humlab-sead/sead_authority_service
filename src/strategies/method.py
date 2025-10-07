from typing import Any, Tuple

import psycopg

from .query import QueryProxy

from .interface import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "method",
    "display_name": "Methods",
    "id_field": "method_id",
    "label_field": "label",
    "abbreviation_field": "method_abbreviation",
    "properties": [
        {
            "id": "method_abbreviation",
            "name": "Method Abbreviation",
            "type": "string",
            "description": "Abbreviation for the method used",
        }
    ],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_label_sql": """
        select * from authority.methods(%(q)s, %(n)s);
    """,
        "get_details": """
            select 
                m.method_id as "ID", 
                m.method_name as "Name", 
                m.description as "Description", 
                m.method_abbrev_or_alt_name as "Abbreviation",
                mg.group_name as "Group",
                mg.description as "Group Description"
            from tbl_methods as m
            join tbl_method_groups mg using (method_group_id)
            where method_id = %(id)s
    """,
        "fetch_method_by_abbreviation": """
        select method_id, label, 1.0 as name_sim
        from authority.methods
        where method_abbrev_or_alt_name = %(abbreviation)s
        limit 1
    """,
    },
}


class MethodQueryProxy(QueryProxy):
    def __init__(self, specification: StrategySpecification, cursor: psycopg.AsyncCursor) -> None:
        super().__init__(specification, cursor)

    async def fetch_method_by_abbreviation(self, abbreviation: str) -> list[dict]:
        """Fetch method by abbreviation"""
        sql: str = self.get_sql_queries().get("fetch_method_by_abbreviation", "")
        await self.cursor.execute(sql, {"abbreviation": abbreviation})
        row: Tuple[Any, ...] | None = await self.cursor.fetchone()
        return [dict(row)] if row else []


@Strategies.register(key="method")
class MethodReconciliationStrategy(ReconciliationStrategy):
    """Method-specific reconciliation with place names and coordinates"""

    def __init__(self) -> None:
        super().__init__(SPECIFICATION, MethodQueryProxy)
