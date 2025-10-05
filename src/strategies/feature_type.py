from typing import Any

import psycopg

from src.strategies.query import QueryProxy

from .interface import ReconciliationStrategy, Strategies

SPECIFICATION: dict[str, str] = {
    "key": "feature_type",
    "id_field": "feature_type_id",
    "label_field": "label",
    "properties": [ ],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_label_sql": """
        select * from authority.fuzzy_feature_types(%(q)s, %(n)s);
    """,
        "get_details": """
            select feature_type_id as "ID",
                   label as "Feature Type Name",
                   description as "Description"
            from authority.feature_types
            where feature_type_id = %(id)s::int
    """,
    },
}


class FeatureTypeQueryProxy(QueryProxy):
    def __init__(self, specification: dict, cursor: psycopg.AsyncCursor) -> None:
        super().__init__(specification, cursor)


@Strategies.register(key="feature_type")
class FeatureTypeReconciliationStrategy(ReconciliationStrategy):
    """Feature-specific reconciliation with feature names and descriptions"""

    def __init__(self, specification: dict[str, str] = SPECIFICATION):
        super().__init__(specification, FeatureTypeQueryProxy)

    async def get_details(self, entity_id: str, cursor: psycopg.AsyncCursor) -> dict[str, Any] | None:
        """Fetch details for a specific site."""
        return await self.query_proxy_class(self.specification, cursor).get_details(entity_id)
