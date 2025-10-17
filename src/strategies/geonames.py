import math
from typing import Any

from src.geonames.proxy import GeoNamesQueryProxy

from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "geonames",
    "display_name": "GeoNames Places",
    "id_field": "geoname_id",
    "label_field": "label",
    "properties": [],
    "property_settings": {},
    "sql_queries": {},
}


@Strategies.register(key="geonames")
class GeoNamesReconciliationStrategy(ReconciliationStrategy):
    """Location-specific reconciliation with place names and coordinates"""

    def __init__(self, specification: dict[str, str] = None) -> None:
        strategy_options: dict[str, Any] = ConfigValue(f"policy.{self.key}.geonames.options").resolve() or {}
        proxy: QueryProxy = GeoNamesQueryProxy(SPECIFICATION, **strategy_options)
        super().__init__(specification or SPECIFICATION, proxy)

    def as_candidate(self, entity_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Convert entity data to OpenRefine candidate format"""
        entity_id: str = str(entity_data["geonameId"])
        admin_bits: list[str] = [entity_data.get("adminName1"), entity_data.get("countryName")]
        admin_str: str = ", ".join([b for b in admin_bits if b])
        label: str = entity_data["name"] + (f", {admin_str}" if admin_str else "")
        candidate: dict[str, Any] = {
            "id": entity_id,
            "name": label,
            "score": self._calculate_score(entity_data),
            "match": label.lower() == query.lower(),
            "type": [self._geonames_type_for_refine(entity_data)],
            "description": self._generate_description(entity_data),
            "uri": f"https://www.geonames.org/{entity_data['geonameId']}",
        }
        candidate['name_sim'] = candidate['score'] / 100.0
        return candidate
    
    def _calculate_score(self, data: dict[str, Any]) -> float:
        gn_score: float = float(data.get("score", 0.0))
        pop: int = int(data.get("population", 0))
        pop_boost: float = math.log10(pop) if pop > 0 else 0.0
        score: float = round(60 + 40 * min(1.0, (gn_score / 100.0) + (pop_boost / 7)), 2)
        return score

    def _generate_description(self, data: dict[str, Any]) -> str:
        pop: int = int(data.get("population", 0))
        return f"{data.get('fcodeName', data.get('fcode')) or ''}{f' · pop {pop:,}' if pop else ''}".strip()

    async def find_candidates(self, query: str, properties: None | dict[str, Any] = None, limit: int = 10) -> list[dict[str, Any]]:
        """Find candidate matches for the given query

        This method should be implemented by subclasses to provide entity-specific
        candidate retrieval logic.

        Default implementations find candidates based on fuzzy name matching.
        """
        properties = properties or {}

        candidates: list[dict] = await self.get_proxy().find(query, limit, properties=properties)

        return sorted(candidates, key=lambda x: x.get("name_sim", 0), reverse=True)[:limit]

    async def get_details(self, entity_id: str, **kwargs) -> dict[str, Any] | None:
        """Fetch details for a specific entity."""
        options: dict[str, Any] = {k: v for k, v in kwargs.items() if k in ("lang", "style")}
        return await self.get_proxy().get_details(geoname_id=entity_id, **options)

    def _geonames_type_for_refine(self, g: dict[str, Any]) -> dict[str, str]:
        fc = g.get("fcl")
        fcode = g.get("fcode", "")
        if fc == "P":
            return {"id": "/location/citytown", "name": "City/Town"}
        if fc == "A" and fcode.startswith("ADM"):
            return {"id": "/location/administrative_area", "name": "Administrative Area"}
        return {"id": "/location/place", "name": "Place"}

