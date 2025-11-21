from abc import ABC, abstractmethod
from typing import Any

from src.configuration import ConfigValue
from src.utility import Registry, _ensure_key_property, resolve_specification

from . import StrategySpecification
from .query import BaseRepository


class ReconciliationStrategy(ABC):
    """Abstract base class for entity-specific reconciliation strategies"""

    repository_cls: type[BaseRepository] = BaseRepository

    def __init__(
        self, specification: StrategySpecification | str | None = None, repository_or_cls: type[BaseRepository] | BaseRepository | None = None
    ) -> None:

        self.specification: StrategySpecification = resolve_specification(specification or self.key)
        self.entity_config: dict[str, Any] = ConfigValue(f"table_specs.{self.key}").resolve() or {}
        self.repository_instance_or_cls: type[BaseRepository] | BaseRepository | None = repository_or_cls or self.repository_cls
        self.repository: BaseRepository | None = None

    @property
    def key(self) -> str:
        """Return the unique key for this strategy, if registered, else 'unknown'"""
        return getattr(self, "_registry_key", "unknown")

    def get_repository(self) -> BaseRepository:
        """Return an instance of the query proxy for this strategy"""
        if not self.repository:
            if isinstance(self.repository_instance_or_cls, BaseRepository):
                self.repository = self.repository_instance_or_cls
            elif self.repository_instance_or_cls is not None:
                self.repository = self.repository_instance_or_cls(self.specification)
            else:
                raise ValueError(f"No proxy configured for strategy {self.key}")
        return self.repository

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
        if "display_name" in self.specification:
            return self.specification["display_name"]
        return self.key.replace("_", " ").title()

    def get_properties_meta(self) -> list[dict[str, str]]:
        """Return metadata for entity-specific properties used in enhanced reconciliation"""
        return self.specification.get("properties", [])

    def get_property_settings(self) -> dict[str, dict[str, Any]]:
        """Return OpenRefine-specific settings for properties (optional override for type-specific settings)"""
        return self.specification.get("property_settings", {})

    def as_candidate(self, entity_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Convert entity data to OpenRefine candidate format"""
        auto_accept_threshold: float = ConfigValue("options:auto_accept_threshold").resolve() or 0.85
        id_base: str = ConfigValue("options:id_base").resolve() or ""

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

        candidates: list[dict] = await self._find_candidates(query, properties, limit, self.get_repository())

        return sorted(candidates, key=lambda x: x.get("name_sim", x.get("score", 0)), reverse=True)[:limit]

    async def _find_candidates(self, query, properties, limit, proxy) -> list[dict]:
        """Internal method to find candidates, can be overridden by subclasses"""
        candidates: list[dict] = []
        alternate_identity_field: str | None = self.specification.get("alternate_identity_field")

        if alternate_identity_field and properties.get(alternate_identity_field, None):
            candidates.extend(await proxy.fetch_by_alternate_identity(properties[alternate_identity_field]))

        candidates.extend(await proxy.find(query, limit))
        return candidates

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific entity."""
        return await self.get_repository().get_details(entity_id)


class StrategyRegistry(Registry):

    items: dict[str, type[ReconciliationStrategy]] = {}

    @classmethod
    def registered_class_hook(cls, fn_or_class: Any, **args) -> Any:
        if args.get("type") != "function":
            if args.get("repository_cls"):
                if hasattr(fn_or_class, "repository_cls"):
                    setattr(fn_or_class, "repository_cls", staticmethod(args["repository_cls"]))
        return fn_or_class


Strategies: StrategyRegistry = StrategyRegistry()
