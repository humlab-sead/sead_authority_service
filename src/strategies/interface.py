from abc import ABC, abstractmethod
from typing import Any, Optional, Type

import psycopg

from src.configuration.inject import ConfigValue
from src.strategies.query import QueryProxy
from src.utility import Registry


class ReconciliationStrategy(ABC):
    """Abstract base class for entity-specific reconciliation strategies"""

    def __init__(self, specification: dict[str, str | dict[str, Any]], query_proxy_class: Type[QueryProxy]) -> None:
        self.specification: dict[str, str | dict[str, Any]] = specification or {
            "key": "unknown",
            "id_field": "id",
            "label_field": "name",
            "properties": [],
            "property_settings": {},
            "sql_queries": {},
        }
        self.query_proxy_class: Type[QueryProxy] = query_proxy_class

    def get_entity_id_field(self) -> str:
        """Return the ID field name for this entity type"""
        return self.specification["id_field"]

    def get_label_field(self) -> str:
        """Return the label field name for this entity type"""
        return self.specification["label_field"]

    def get_id_path(self) -> str:
        """Return the URL path segment for this entity type"""
        return self.specification["key"]

    def get_properties_meta(self) -> list[dict[str, str]]:
        """Return metadata for entity-specific properties used in enhanced reconciliation"""
        return self.specification["properties"]

    def get_property_settings(self) -> dict[str, dict[str, Any]]:
        """Return OpenRefine-specific settings for properties (optional override for type-specific settings)"""
        return self.specification["property_settings"]

    def as_candidate(self, entity_data: dict[str, Any]) -> dict[str, Any]:
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
            "match": bool(score >= auto_accept_threshold),
            "type": [{"id": self.get_id_path(), "name": label}],
        }

        # Add additional metadata if available
        if "distance_km" in entity_data:
            candidate["distance_km"] = round(entity_data["distance_km"], 2)

        return candidate

    @abstractmethod
    async def find_candidates(
        self, cursor: psycopg.AsyncCursor, query: str, properties: None | list[dict[str, Any]] = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Find candidate matches for the given query"""

    @abstractmethod
    async def get_details(self, entity_id: str, cursor) -> Optional[dict[str, Any]]:
        """Fetch detailed information for a given entity ID."""


class StrategyRegistry(Registry):

    items: dict[str, ReconciliationStrategy] = {}

    
Strategies: StrategyRegistry = StrategyRegistry()
