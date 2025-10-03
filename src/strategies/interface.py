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

    def collect_property_settings(self) -> list[dict[str, str]]:
        property_settings: list[dict[str, str]] = []
        for strategy_class in self.items.values():
            strategy: ReconciliationStrategy = strategy_class()
            properties = strategy.get_properties_meta()
            property_specific_settings = strategy.get_property_settings()

            for prop in properties:
                # Convert property metadata to OpenRefine property_settings format
                setting: dict[str, str] = {
                    "name": prop["id"],
                    "label": prop["name"],
                    "type": prop["type"],
                    "help_text": prop["description"],
                }

                # Add strategy-specific settings if available
                if prop["id"] in property_specific_settings:
                    setting["settings"] = property_specific_settings[prop["id"]]

                property_settings.append(setting)
        return property_settings

    def retrieve_properties(self, query: str = None, type: str = None) -> list[dict[str, str]] | Any:
        """
        Collects property suggestions returned by the /properties endpoint for OpenRefine.

        Returns available properties that can be used for enhanced reconciliation.
        OpenRefine calls this endpoint to populate property selection dropdowns.

        Args:
            query: Optional search term to filter properties
            type: Optional entity type to filter properties (e.g., "site", "taxon")

        Returns:
            Dict with matching properties
        """
        all_properties: list[dict[str, str]] = []
        if type and type in self.items:
            # Get properties for the specific entity type
            all_properties = self.items[type]().get_properties_meta()
        elif type and type not in self.items:
            # Unknown entity type - return empty to avoid confusion
            all_properties = []
        else:
            # No type specified - return properties from all registered strategies
            all_properties = []
            for strategy_class in self.items.values():
                all_properties.extend(strategy_class().get_properties_meta())

        # Filter properties based on query if provided
        if query:
            query_lower: str = query.lower()
            filtered_properties = [
                prop
                for prop in all_properties
                if query_lower in prop["id"].lower() or query_lower in prop["name"].lower() or query_lower in prop["description"].lower()
            ]
        else:
            filtered_properties: list[dict[str, str]] = all_properties
        return filtered_properties


    def get_reconciliation_metadata(self) -> dict[str, Any]:
        default_types: list[dict[str, str]] = [{"id": entity_type, "name": entity_type} for entity_type in Strategies.items]
        id_base: str = ConfigValue("options:id_base").resolve()

        # Collect property settings from all registered strategies
        property_settings: list[dict[str, str]] = Strategies.collect_property_settings()

        return {
            "name": "SEAD Entity Reconciliation",
            "identifierSpace": f"{id_base}",
            "schemaSpace": "http://www.w3.org/2004/02/skos/core#",
            "defaultTypes": default_types,
            "view": {"url": f"{id_base}reconcile/preview?id={{id}}"},
            "extend": {
                "propose_properties": {
                    "service_url": f"{id_base}reconcile",
                    "service_path": "/properties",
                },
                "property_settings": property_settings,
            },
        }
    
Strategies: StrategyRegistry = StrategyRegistry()
