from .location import LocationReconciliationStrategy
from .strategy import Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "administrative_region",
    "display_name": "Sub-country administrative region",
    "id_field": "location_id",
    "label_field": "label",
    "property_settings": {},
    "sql_queries": {
        "fuzzy_label_sql": """ select * from authority.fuzzy_location(%(q)s, %(n)s, 7) """,
        "details_sql": """
            select  location_id as "ID",
                    label as "Region",
                    description as "Description"
            from authority.locations
            where location_id = %(id)s::int
    """,
    },
}


@Strategies.register(key="administrative_region")
class AdministrativeRegionReconciliationStrategy(LocationReconciliationStrategy):
    """Administrative region-specific reconciliation"""

    def __init__(self):
        super().__init__(SPECIFICATION)
