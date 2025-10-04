from typing import Any

import psycopg

from src.strategies.query import QueryProxy

from .interface import ReconciliationStrategy, Strategies

SPECIFICATION: dict[str, str] = {
    "key": "location",
    "id_field": "location_id",
    "label_field": "label",
    "properties": [
        # {
        #     "id": "latitude",
        #     "name": "Latitude",
        #     "type": "number",
        #     "description": "Geographic latitude in decimal degrees (WGS84)",
        # },
        # {
        #     "id": "longitude",
        #     "name": "Longitude",
        #     "type": "number",
        #     "description": "Geographic longitude in decimal degrees (WGS84)",
        # },
        # {
        #     "id": "national_id",
        #     "name": "National Site ID",
        #     "type": "string",
        #     "description": "Official national site identifier or registration number",
        # },
        {
            "id": "place_name",
            "name": "Place Name",
            "type": "string",
            "description": "Geographic place, locality, or administrative area name",
        },
    ],
    "property_settings": {},
    "sql_queries": {
        "fetch_by_fuzzy_search": """
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

    def __init__(self, specification: dict[str, str] = SPECIFICATION):
        super().__init__(specification, LocationQueryProxy)
