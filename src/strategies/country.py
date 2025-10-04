from .location import LocationQueryProxy, LocationReconciliationStrategy
from .interface import Strategies

SPECIFICATION: dict[str, str] = {
    "key": "country",
    "id_field": "location_id",
    "label_field": "label",
    "properties": [],
    "property_settings": {},
    "sql_queries": {
        "fetch_by_fuzzy_search": """ select * from authority.fuzzy_locations(%(q)s, %(n)s, 1) """,
        "get_details": """
            select  location_id as "ID",
                    label as "Country",
                    description as "Description"
            from authority.locations
            where location_id = %(id)s::int
    """,
    },
}


@Strategies.register(key="country")
class CountryReconciliationStrategy(LocationReconciliationStrategy):
    """Country-specific reconciliation"""

    def __init__(self):
        super().__init__(SPECIFICATION)
