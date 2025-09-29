from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ReconciliationStrategy(ABC):
    """Abstract base class for entity-specific reconciliation strategies"""

    @abstractmethod
    async def find_candidates(self, query: str, cursor, limit: int = 10) -> List[Dict[str, Any]]:
        """Find candidate matches for the given query"""

    @abstractmethod
    def get_entity_id_field(self) -> str:
        """Return the ID field name for this entity type"""

    @abstractmethod
    async def get_details(self, entity_id: str, cursor) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a given entity ID."""

    @abstractmethod
    def get_label_field(self) -> str:
        """Return the label field name for this entity type"""

    @abstractmethod
    def get_id_path(self) -> str:
        """Return the URL path segment for this entity type"""
