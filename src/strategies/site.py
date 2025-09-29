import re
from typing import Any

import psycopg

from . import ReconciliationStrategy, Strategies


@Strategies.register(key="site")
class SiteReconciliationStrategy(ReconciliationStrategy):
    """Site-specific reconciliation with place names and coordinates"""

    def get_entity_id_field(self) -> str:
        return "site_id"

    def get_label_field(self) -> str:
        return "label"

    def get_id_path(self) -> str:
        return "site"

    async def find_candidates(self, query: str, cursor, limit: int = 10) -> list[dict[str, Any]]:
        candidates = []

        # Parse query for additional context (this could be more sophisticated)
        query_parts = self._parse_query(query)

        # 1) Exact match by national site identifier
        if query_parts.get("identifier"):
            exact_sql = """
                SELECT site_id, label, 1.0 AS name_sim, latitude_dd, longitude_dd
                FROM authority.sites
                WHERE national_site_identifier = %(identifier)s
                LIMIT 1
            """
            await cursor.execute(exact_sql, {"identifier": query_parts["identifier"]})
            row = await cursor.fetchone()
            if row:
                candidates.append(dict(row))

        # 2) Fuzzy name matching with enhanced scoring
        if not candidates:
            candidates.extend(await self._fuzzy_name_search(query_parts["name"], cursor, limit))

        # 3) Geographic proximity boost if coordinates provided
        if query_parts.get("coordinates") and candidates:
            candidates = await self._apply_geographic_scoring(candidates, query_parts["coordinates"], cursor)

        # 4) Place name context boost
        if query_parts.get("place") and candidates:
            candidates = await self._apply_place_context_scoring(candidates, query_parts["place"], cursor)

        return sorted(candidates, key=lambda x: x.get("name_sim", 0), reverse=True)[:limit]

    def _parse_query(self, query: str) -> Dict[str, Any]:
        """Parse query string to extract different components"""
        # This is a simple implementation - you could make this more sophisticated
        # Examples of what you might parse:
        # "Site ABC near Stockholm (59.3293, 18.0686)"
        # "Site XYZ | ID: SE123456"

        parts = {"name": query.strip()}

        # Extract coordinates if present (lat, lon) format

        coord_pattern = r"\((-?\d+\.?\d*),\s*(-?\d+\.?\d*)\)"
        coord_match = re.search(coord_pattern, query)
        if coord_match:
            parts["coordinates"] = {
                "lat": float(coord_match.group(1)),
                "lon": float(coord_match.group(2)),
            }
            parts["name"] = re.sub(coord_pattern, "", query).strip()

        # Extract identifier if present
        id_pattern = r"ID:\s*([^\s|]+)"
        id_match = re.search(id_pattern, query)
        if id_match:
            parts["identifier"] = id_match.group(1)
            parts["name"] = re.sub(id_pattern, "", parts["name"]).strip(" |")

        # Extract place context
        place_pattern = r"\bnear\s+([^(]+?)(?:\s*\(|$)"
        place_match = re.search(place_pattern, parts["name"], re.IGNORECASE)
        if place_match:
            parts["place"] = place_match.group(1).strip()
            parts["name"] = re.sub(place_pattern, "", parts["name"], flags=re.IGNORECASE).strip()

        return parts

    async def _fuzzy_name_search(self, name: str, cursor, limit: int) -> list[dict[str, Any]]:
        """Perform fuzzy name search"""
        fuzzy_sql = "SELECT * FROM authority.fuzzy_sites(%(q)s, %(n)s);"
        await cursor.execute(fuzzy_sql, {"q": name, "n": limit})
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def _apply_geographic_scoring(self, candidates: list[dict], coords: Dict, cursor) -> list[dict]:
        """Boost scores based on geographic proximity"""
        if not coords or not candidates:
            return candidates

        # Create a list of site IDs for batch geographic query
        site_ids = [c["site_id"] for c in candidates]

        geo_sql = """
            SELECT site_id, 
                   ST_Distance(
                       ST_Transform(ST_SetSRID(ST_MakePoint(longitude_dd, latitude_dd), 4326), 3857),
                       ST_Transform(ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326), 3857)
                   ) / 1000.0 as distance_km
            FROM authority.sites 
            WHERE site_id = ANY(%(site_ids)s) 
              AND latitude_dd IS NOT NULL 
              AND longitude_dd IS NOT NULL
        """

        await cursor.execute(geo_sql, {"lat": coords["lat"], "lon": coords["lon"], "site_ids": site_ids})

        geo_results = {row["site_id"]: row["distance_km"] for row in await cursor.fetchall()}

        # Apply distance-based scoring boost
        for candidate in candidates:
            site_id = candidate["site_id"]
            if site_id in geo_results:
                distance = geo_results[site_id]
                # Boost score based on proximity (closer = higher boost)
                # Max boost of 0.2 for sites within 1km, diminishing to 0 at 100km
                proximity_boost = max(0, 0.2 * (1 - min(distance / 100.0, 1.0)))
                candidate["name_sim"] = min(1.0, candidate["name_sim"] + proximity_boost)
                candidate["distance_km"] = distance

        return candidates

    async def get_details(self, entity_id: str, cursor) -> Optional[Dict[str, Any]]:
        """Fetch details for a specific site."""
        try:
            site_id_int = int(entity_id)
            await cursor.execute(
                """
                SELECT 
                    site_id as "ID", 
                    label as "Name", 
                    site_description as "Description", 
                    national_site_identifier as "National ID", 
                    latitude_dd as "Latitude", 
                    longitude_dd as "Longitude"
                FROM authority.sites 
                WHERE site_id = %(id)s
                """,
                {"id": site_id_int},
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        except (ValueError, psycopg.Error):
            return None

    async def _apply_place_context_scoring(self, candidates: list[dict], place: str, cursor) -> list[dict]:
        """Boost scores based on place name context"""
        # This could query a places/regions table or use external geocoding
        # For now, simple implementation checking site descriptions

        place_sql = """
            SELECT site_id, similarity(site_description, %(place)s) as place_sim
            FROM authority.sites 
            WHERE site_id = ANY(%(site_ids)s) 
              AND site_description IS NOT NULL
        """

        site_ids = [c["site_id"] for c in candidates]
        await cursor.execute(place_sql, {"place": place, "site_ids": site_ids})

        place_results = {row["site_id"]: row["place_sim"] for row in await cursor.fetchall()}

        # Apply place context boost
        for candidate in candidates:
            site_id = candidate["site_id"]
            if site_id in place_results and place_results[site_id] > 0.3:
                place_boost = place_results[site_id] * 0.1  # Max boost of 0.1
                candidate["name_sim"] = min(1.0, candidate["name_sim"] + place_boost)

        return candidates
