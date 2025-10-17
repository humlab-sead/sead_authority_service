from abc import ABC
from typing import Any, Type

from src.configuration import ConfigValue
from src.utility import Registry

from . import StrategySpecification
from .query import QueryProxy


class ReconciliationStrategy(ABC):
    """Abstract base class for entity-specific reconciliation strategies"""

    def __init__(self, specification: StrategySpecification, proxy_or_cls: Type[QueryProxy] | QueryProxy) -> None:
        self.specification: StrategySpecification = specification or {
            "key": "unknown",
            "id_field": "id",
            "label_field": "name",
            "properties": [],
            "property_settings": {},
            "sql_queries": {},
        }
        self._proxy_or_cls: Type[QueryProxy] = proxy_or_cls
        self._proxy: QueryProxy = None

    def get_proxy(self) -> QueryProxy:
        """Return an instance of the query proxy for this strategy"""
        if not self._proxy:
            if isinstance(self._proxy_or_cls, QueryProxy):
                self._proxy = self._proxy_or_cls
            else:
                self._proxy = self._proxy_or_cls(self.specification)
        return self._proxy

    @property
    def key(self) -> str:
        """Return the unique key for this strategy"""
        return self.specification["key"]

    def get_entity_id_field(self) -> str:
        """Return the ID field name for this entity type"""
        return self.specification["id_field"]

    def get_label_field(self) -> str:
        """Return the label field name for this entity type"""
        return self.specification["label_field"]

    def get_id_path(self) -> str:
        """Return the URL path segment for this entity type"""
        return self.specification["key"]

    def get_display_name(self) -> str:
        """Return human-readable display name for this entity type"""
        return self.specification.get("display_name", self.get_id_path().replace("_", " ").title())

    def get_properties_meta(self) -> list[dict[str, str]]:
        """Return metadata for entity-specific properties used in enhanced reconciliation"""
        return self.specification.get("properties", [])

    def get_property_settings(self) -> dict[str, dict[str, Any]]:
        """Return OpenRefine-specific settings for properties (optional override for type-specific settings)"""
        return self.specification.get("property_settings", {})

    def as_candidate(self, entity_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Convert entity data to OpenRefine candidate format"""
        auto_accept_threshold: float = ConfigValue("options:auto_accept_threshold").resolve() or 0.85
        id_base: str = ConfigValue("options:id_base").resolve()

        entity_id: str = entity_data[self.get_entity_id_field()]
        label: str = entity_data[self.get_label_field()]
        score = float(entity_data.get("name_sim", 0))
        candidate: dict[str, Any] = {
            "id": f"{id_base}{self.get_id_path()}/{entity_id}",
            "name": label,
            "score": min(100.0, round(score * 100, 2)),
            "match": bool(label.lower() == query.lower() or score >= auto_accept_threshold),
            "type": [{"id": self.get_id_path(), "name": label}],
        }

        # Add additional metadata if available
        if "distance_km" in entity_data:
            candidate["distance_km"] = round(entity_data["distance_km"], 2)

        return candidate

    async def find_candidates(self, query: str, properties: None | dict[str, Any] = None, limit: int = 10) -> list[dict[str, Any]]:
        """Find candidate matches for the given query

        This method should be implemented by subclasses to provide entity-specific
        candidate retrieval logic.

        Default implementations find candidates based on fuzzy name matching.
        """
        properties = properties or {}

        candidates: list[dict] = await self._find_candidates(query, properties, limit, self.get_proxy())

        return sorted(candidates, key=lambda x: x.get("name_sim", x.get("score", 0)), reverse=True)[:limit]

    async def _find_candidates(self, query, properties, limit, proxy) -> list[dict]:
        """Internal method to find candidates, can be overridden by subclasses"""
        candidates: list[dict] = []
        alternate_identity_field: str = self.specification.get("alternate_identity_field")

        if alternate_identity_field and properties.get(alternate_identity_field, None):
            candidates.extend(await proxy.fetch_by_alternate_identity(properties[alternate_identity_field]))

        candidates.extend(await proxy.fetch_by_fuzzy_label(query, limit))
        return candidates

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific entity."""
        return await self.get_proxy().get_details(entity_id)


class StrategyRegistry(Registry):

    items: dict[str, ReconciliationStrategy] = {}


Strategies: StrategyRegistry = StrategyRegistry()
