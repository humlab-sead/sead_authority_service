from typing import Any, Tuple

import psycopg

from .query import QueryProxy
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "method",
    "display_name": "Methods",
    "id_field": "method_id",
    "label_field": "label",
    "alternate_identity_field": "method_abbreviation",
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
        "alternate_identity_sql": """
        select method_id, label, 1.0 as name_sim
        from authority.methods
        where method_abbrev_or_alt_name = %(alternate_identity)s
        limit 1
    """,
    },
}


class MethodQueryProxy(QueryProxy):
    def __init__(self, specification: StrategySpecification, cursor: psycopg.AsyncCursor) -> None:
        super().__init__(specification, cursor)


@Strategies.register(key="method")
class MethodReconciliationStrategy(ReconciliationStrategy):
    """Method-specific reconciliation with place names and coordinates"""

    def __init__(self) -> None:
        super().__init__(SPECIFICATION, MethodQueryProxy)
