from .location import LocationReconciliationStrategy
from .strategy import Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "country",
    "display_name": "Countries",
    "id_field": "location_id",
    "label_field": "label",
    # "alternate_identity_field": "country_abbreviation",
    # "properties": [
    #     {
    #         "id": "country_abbreviation",
    #         "name": "Country Abbreviation",
    #         "type": "string",
    #         "description": "Abbreviation for the country used",
    #     }
    # ],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_find_sql": """ select * from authority.fuzzy_locations(%(q)s, %(n)s, 1) """,
        "details_sql": """
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
