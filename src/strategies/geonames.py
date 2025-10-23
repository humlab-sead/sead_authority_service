import math
from typing import Any

from src.configuration.resolve import ConfigValue
from src.geonames.proxy import GeoNamesProxy

from .query import QueryProxy
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


class GeoNamesQueryProxy(QueryProxy):  # pylint: disable=too-many-instance-attributes

    def __init__(self, specification: StrategySpecification, **kwargs) -> None:
        super().__init__(specification, **kwargs)
        self.username: str = kwargs.get("username") or ConfigValue("geonames.username", default="demo").resolve()
        self.lang: str = kwargs.get("lang") or ConfigValue("geonames.lang", default="en").resolve()
        self.country_bias: str | None = kwargs.get("country_bias") or ConfigValue("geonames.country_bias").resolve()
        self.fuzzy = float(kwargs.get("fuzzy") or ConfigValue("geonames.fuzzy", default=0.8).resolve())
        self.feature_classes: tuple[str, ...] = tuple(kwargs.get("feature_classes") or ConfigValue("geonames.feature_classes", default=("P", "A")).resolve())
        self.orderby: str = kwargs.get("orderby") or ConfigValue("geonames.orderby", default="relevance").resolve()
        self.style: str = kwargs.get("style") or ConfigValue("geonames.style", default="FULL").resolve()

        self.proxy: GeoNamesProxy = GeoNamesProxy(username=self.username, lang=self.lang)

    async def find(self, name: str, limit: int = 10, **kwargs) -> list[dict[str, Any]]:
        return await self.proxy.search(
            q=name,
            max_rows=limit,
            fuzzy=self.fuzzy,
            feature_classes=self.feature_classes,
            country_bias=self.country_bias,
            orderby=self.orderby,
            style=self.style,
        )

    async def get_details(self, entity_id: str, **kwargs) -> dict[str, Any] | None:  # pylint: disable=unused-argument
        return await self.proxy.get_details(entity_id, **kwargs)

    async def fetch_by_alternate_identity(self, alternate_identity: str, **kwargs) -> list[dict[str, Any]]:
        raise NotImplementedError("Alternate identity lookup not implemented for GeoNames")


@Strategies.register(key="geonames")
class GeoNamesReconciliationStrategy(ReconciliationStrategy):
    """Location-specific reconciliation with place names and coordinates"""

    def __init__(self, specification: dict[str, str] = None) -> None:
        key = (specification or SPECIFICATION).get("key", "geonames")
        strategy_options: dict[str, Any] = ConfigValue(f"policy.{key}.geonames.options").resolve() or {}
        proxy: QueryProxy = GeoNamesQueryProxy(SPECIFICATION, **strategy_options)
        super().__init__(specification or SPECIFICATION, proxy)

    def as_candidate(self, entity_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Convert Geonames data to OpenRefine candidate format"""
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
        candidate["name_sim"] = candidate["score"] / 100.0 if "score" in candidate and candidate["score"] is not None else 0.0
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
        return await self.get_proxy().get_details(entity_id=entity_id, **options)

    def _geonames_type_for_refine(self, g: dict[str, Any]) -> dict[str, str]:
        fc = g.get("fcl")
        fcode = g.get("fcode", "")
        if fc == "P":
            return {"id": "/location/citytown", "name": "City/Town"}
        if fc == "A" and fcode.startswith("ADM"):
            return {"id": "/location/administrative_area", "name": "Administrative Area"}
        return {"id": "/location/place", "name": "Place"}
