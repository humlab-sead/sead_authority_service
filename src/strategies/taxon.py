from ast import Dict
from typing import Any, List, Optional

from .interface import ReconciliationStrategy, Strategies


@Strategies.register(key="taxon")
class TaxonReconciliationStrategy(ReconciliationStrategy):
    """Future taxon reconciliation strategy"""

    def get_entity_id_field(self) -> str:
        return "taxon_id"

    def get_label_field(self) -> str:
        return "scientific_name"

    def get_id_path(self) -> str:
        return "taxon"

    async def find_candidates(self, query: str, cursor, limit: int = 10) -> List[Dict[str, Any]]:
        # Implement taxon-specific logic here
        # Could handle genus/species parsing, synonym matching, etc.
        pass

    async def get_details(self, entity_id: str, cursor) -> Optional[Dict[str, Any]]:
        """Fetch details for a specific taxon (placeholder)."""
        # When implemented, this would query the taxon authority tables.
        return None
