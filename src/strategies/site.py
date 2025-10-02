from typing import Any, Tuple

import psycopg

from src.configuration.inject import ConfigValue

from .interface import ReconciliationStrategy, Strategies

SQL_QUERIES: dict[str, str] = {
    "fetch_site_by_national_id": """
        select site_id, label, 1.0 as name_sim, latitude_dd as latitude, longitude_dd as longitude
        from authority.sites
        where national_site_identifier = %(identifier)s
        limit 1
    """,
    "fetch_by_fuzzy_name_search": """
        SELECT * FROM authority.fuzzy_sites(%(q)s, %(n)s);
    """,
    "fetch_site_distances": """
        select site_id, 
               ST_Distance(
                   ST_Transform(ST_SetSRID(ST_MakePoint(longitude_dd, latitude_dd), 4326), 3857),
                   ST_Transform(ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326), 3857)
               ) / 1000.0 as distance_km
        from authority.sites 
        where site_id = ANY(%(site_ids)s) 
          and latitude_dd is not null 
          and longitude_dd is not null
    """,
    "fetch_site_location_similarity": """
        select site_id, max(similarity(location_name, %(place)s)) as place_sim
        from public.tbl_site_locations
        join public.tbl_locations using(location_id)
        where site_id = any(%(site_ids)s) 
          and location_name is not null
        group by site_id
    """,
    "get_site_details": """
        select 
            site_id as "ID", 
            label as "Name", 
            site_description as "Description", 
            national_site_identifier as "National ID", 
            latitude_dd as "Latitude", 
            longitude_dd as "Longitude"
        from authority.sites 
        where site_id = %(id)s
    """,
}

SPECIFICATION: dict[str, str] = {
    "key": "site",
    "id_field": "site_id",
    "label_field": "label",
    "properties": [
        {
            "id": "latitude",
            "name": "Latitude",
            "type": "number",
            "description": "Geographic latitude in decimal degrees (WGS84)",
        },
        {
            "id": "longitude",
            "name": "Longitude",
            "type": "number",
            "description": "Geographic longitude in decimal degrees (WGS84)",
        },
        {
            "id": "country",
            "name": "Country",
            "type": "string",
            "description": "Country name where the site is located",
        },
        {
            "id": "national_id",
            "name": "National Site ID",
            "type": "string",
            "description": "Official national site identifier or registration number",
        },
        {
            "id": "place_name",
            "name": "Place Name",
            "type": "string",
            "description": "Geographic place, locality, or administrative area name",
        },
    ],
    "property_settings": {
        "latitude": {"min": -90.0, "max": 90.0, "precision": 6},
        "longitude": {"min": -180.0, "max": 180.0, "precision": 6},
    },
}


class QueryProxy:
    def __init__(self, cursor: psycopg.AsyncCursor) -> None:
        self.cursor: psycopg.AsyncCursor[Tuple[Any]] = cursor

    async def fetch_site_by_national_id(self, national_id: str) -> list[dict[str, Any]]:
        sql: str = SQL_QUERIES["fetch_site_by_national_id"]
        await self.cursor.execute(sql, {"identifier": national_id})
        row: Tuple[Any, ...] | None = await self.cursor.fetchone()
        return [dict(row)] if row else []

    async def fetch_by_fuzzy_name_search(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Perform fuzzy name search"""
        sql: str = SQL_QUERIES["fetch_by_fuzzy_name_search"]
        await self.cursor.execute(sql, {"q": name, "n": limit})
        rows: list[Tuple[Any]] = await self.cursor.fetchall()
        return [dict(row) for row in rows]

    async def fetch_site_distances(self, coordinate: dict[str, float], site_ids: list[int]) -> dict[int, float]:
        sql: str = SQL_QUERIES["fetch_site_distances"]
        await self.cursor.execute(sql, coordinate | {"site_ids": site_ids})
        distances: dict[int, float] = {row["site_id"]: row["distance_km"] for row in await self.cursor.fetchall()}
        return distances

    async def get_site_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific site."""
        try:
            sql: str = SQL_QUERIES["get_site_details"]
            await self.cursor.execute(sql, {"id": int(entity_id)})
            row: Tuple[Any] | None = await self.cursor.fetchone()
            return dict(row) if row else None
        except (ValueError, psycopg.Error):
            return None

    async def fetch_site_location_similarity(self, candidates: list[dict], place: str) -> list[dict]:
        """Boost scores based on place name context"""
        # This could query a places/regions table or use external geocoding
        # For now, simple implementation checking site descriptions

        sql: str = SQL_QUERIES["fetch_site_location_similarity"]

        site_ids: list[int] = [c["site_id"] for c in candidates]
        await self.cursor.execute(sql, {"place": place, "site_ids": site_ids})

        place_results: dict[int, float] = {row["site_id"]: row["place_sim"] for row in await self.cursor.fetchall()}
        return place_results


@Strategies.register(key="site")
class SiteReconciliationStrategy(ReconciliationStrategy):
    """Site-specific reconciliation with place names and coordinates"""

    def get_entity_id_field(self) -> str:
        return SPECIFICATION["id_field"]

    def get_label_field(self) -> str:
        return SPECIFICATION["label_field"]

    def get_id_path(self) -> str:
        return SPECIFICATION["key"]

    def get_properties_meta(self) -> list[dict[str, str]]:
        """Return metadata for site-specific properties used in enhanced reconciliation"""
        return SPECIFICATION["properties"]

    def get_property_settings(self) -> dict[str, dict[str, Any]]:
        """Return OpenRefine-specific settings for site properties"""
        return SPECIFICATION["property_settings"]

    async def find_candidates(self, cursor: psycopg.AsyncCursor, query: str, properties: None | dict[str, Any] = None, limit: int = 10) -> list[dict[str, Any]]:
        """Find candidate sites based on name, identifier, and optional geographic context"""
        candidates: list[dict] = []
        properties = properties or {}
        proxy: QueryProxy = QueryProxy(cursor)

        # 1) Exact match by national site identifier
        if properties.get("national_id"):
            candidates.extend(await proxy.fetch_site_by_national_id(properties["national_id"]))

        # 2) Fuzzy name matching with enhanced scoring
        if not candidates:
            candidates.extend(await proxy.fetch_by_fuzzy_name_search(query, limit))

        # 3) Geographic proximity boost if coordinates provided
        if properties.get("latitude") and properties.get("longitude") and candidates:
            candidates = await self._apply_geographic_scoring(candidates, {"lat": properties["latitude"], "lon": properties["longitude"]}, proxy)

        # 4) Place name context boost
        if properties.get("place") and candidates:
            candidates = await self._apply_place_context_scoring(candidates, properties["place"], proxy)

        return sorted(candidates, key=lambda x: x.get("name_sim", 0), reverse=True)[:limit]

    async def _apply_geographic_scoring(self, candidates: list[dict], coordinate: dict[str, float], proxy: QueryProxy) -> list[dict]:
        """Boost scores based on geographic proximity"""
        if not coordinate or not candidates:
            return candidates
        very_near_distance_km: float = ConfigValue("policy:site:proximity_boost:very_near_distance_km").resolve() or 0.2
        to_far_distance_km: float = ConfigValue("policy:site:proximity_boost:to_far_distance_km").resolve() or 10.0
        distances: dict[int, float] = await proxy.fetch_site_distances(coordinate, [c["site_id"] for c in candidates])
        # Apply distance-based scoring boost
        for candidate in candidates:
            site_id = candidate["site_id"]
            if site_id in distances:
                distance = distances[site_id]
                # Max boost of very_near_distance_km for sites within 1km, diminishing to 0 at 100km
                proximity_boost = max(0, very_near_distance_km * (1 - min(distance / to_far_distance_km, 1.0)))
                candidate["name_sim"] = min(1.0, candidate["name_sim"] + proximity_boost)
                candidate["distance_km"] = distance

        return candidates

    async def get_details(self, entity_id: str, cursor: psycopg.AsyncCursor) -> dict[str, Any] | None:
        """Fetch details for a specific site."""
        return await QueryProxy(cursor).get_site_details(entity_id)

    async def _apply_place_context_scoring(self, candidates: list[dict], place: str, proxy: QueryProxy) -> list[dict]:
        """Boost scores based on place name context"""

        place_results = await proxy.fetch_site_location_similarity(candidates, place)

        similarity_threshold: float = ConfigValue("policy:site:place_name_similarity_boost:similarity_threshold").resolve() or 0.3
        max_boost: float = ConfigValue("policy:site:place_name_similarity_boost:max_boost").resolve() or 0.1

        # Apply place context boost
        for candidate in candidates:
            site_id = candidate["site_id"]
            if site_id in place_results and place_results[site_id] > similarity_threshold:
                place_boost = place_results[site_id] * max_boost
                candidate["name_sim"] = min(1.0, candidate["name_sim"] + place_boost)

        return candidates
