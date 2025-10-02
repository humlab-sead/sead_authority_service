from typing import Any

import psycopg

from strategies.query import QueryProxy

from .interface import ReconciliationStrategy, Strategies

SPECIFICATION: dict[str, str] = {
    "key": "place",
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
    "property_settings": {
    },
    "sql_queries": {
        "fetch_by_fuzzy_name_search": """
        select * from authority.fuzzy_locations(%(q)s, %(n)s);
    """,
        "get_details": """
            select  location_id as "ID",
                    label as "Place Name",
                    default_lat_dd as "Latitude",
                    default_long_dd as "Longitude",
                    location_type as "Location Type",
                    description as "Description",
                    geom as "Geometry WKT"
            from authority.locations
            where location_id = %(id)s
    """,
    },
}


class LocationQueryProxy(QueryProxy):
    def __init__(self, cursor: psycopg.AsyncCursor) -> None:
        super().__init__(SPECIFICATION, cursor)


@Strategies.register(key="location")
class LocationReconciliationStrategy(ReconciliationStrategy):
    """Location-specific reconciliation with place names and coordinates"""

    def __init__(self):
        super().__init__(SPECIFICATION, LocationQueryProxy)

    async def find_candidates(self, cursor: psycopg.AsyncCursor, query: str, properties: None | dict[str, Any] = None, limit: int = 10) -> list[dict[str, Any]]:
        """Find candidate sites based on name, identifier, and optional geographic context"""
        candidates: list[dict] = []
        properties = properties or {}
        proxy: QueryProxy = self.query_proxy_class(self.specification, cursor)

        # Only fuzzy match on name for now
        candidates.extend(await proxy.fetch_by_fuzzy_name_search(query, limit))

        return sorted(candidates, key=lambda x: x.get("name_sim", 0), reverse=True)[:limit]

    async def get_details(self, entity_id: str, cursor: psycopg.AsyncCursor) -> dict[str, Any] | None:
        """Fetch details for a specific site."""
        return await self.query_proxy_class(self.specification, cursor).get_details(entity_id)
