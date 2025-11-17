from typing import Any

from .query import DatabaseQueryProxy
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "feature_type",
    "display_name": "Feature Types",
    "id_field": "feature_type_id",
    "label_field": "label",
    "properties": [],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_label_sql": """
        select * from authority.fuzzy_feature_types(%(q)s, %(n)s);
    """,
        "details_sql": """
            select feature_type_id as "ID",
                   label as "Feature Type Name",
                   description as "Description"
            from authority.feature_types
            where feature_type_id = %(id)s::int
    """,
    },
}


class FeatureTypeQueryProxy(DatabaseQueryProxy):
    def __init__(self, specification: StrategySpecification) -> None:  # pylint: disable=useless-parent-delegation
        super().__init__(specification)


@Strategies.register(key="feature_type")
class FeatureTypeReconciliationStrategy(ReconciliationStrategy):
    """Feature-specific reconciliation with feature names and descriptions"""

    def __init__(self, specification: StrategySpecification | None= None) -> None:
        specification = specification or SPECIFICATION
        super().__init__(specification, FeatureTypeQueryProxy)

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific site."""
        return await self.get_proxy().get_details(entity_id)
