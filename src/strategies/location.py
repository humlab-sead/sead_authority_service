import psycopg

from .query import QueryProxy

from .interface import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "location",
    "display_name": "Locations & Places", 
    "id_field": "location_id",
    "label_field": "label",
    "properties": [
        {
            "id": "place_name",
            "name": "Place Name",
            "type": "string",
            "description": "Geographic place, locality, or administrative area name",
        },
    ],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_label_sql": """
        select * from authority.fuzzy_locations(%(q)s, %(n)s);
    """,
        "get_details": """
            select  location_id as "ID",
                    label as "Place Name",
                    latitude as "Latitude",
                    longitude as "Longitude",
                    location_type as "Location Type",
                    description as "Description"
            from authority.locations
            where location_id = %(id)s::int
    """,
    },
}


class LocationQueryProxy(QueryProxy):
    def __init__(self, specification: dict, cursor: psycopg.AsyncCursor) -> None:
        super().__init__(specification, cursor)


@Strategies.register(key="location")
class LocationReconciliationStrategy(ReconciliationStrategy):
    """Location-specific reconciliation with place names and coordinates"""

    def __init__(self, specification: dict[str, str] = None) -> None:
        specification = specification or SPECIFICATION
        super().__init__(specification, LocationQueryProxy)
