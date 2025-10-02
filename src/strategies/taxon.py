from typing import Any

import psycopg

from .interface import ReconciliationStrategy, Strategies

SPECIFICATION: dict[str, str] = {
    "key": "taxon",
    "id_field": "taxon_id",
    "label_field": "label",
    "properties": [
        {
            "id": "scientific_name",
            "name": "Scientific Name",
            "type": "string",
            "description": "Full taxonomic scientific name",
        },
        {
            "id": "genus",
            "name": "Genus",
            "type": "string",
            "description": "Taxonomic genus name",
        },
        {
            "id": "species",
            "name": "Species",
            "type": "string",
            "description": "Taxonomic species name",
        },
        {
            "id": "family",
            "name": "Family",
            "type": "string",
            "description": "Taxonomic family name",
        },
    ],
    "property_settings": {},
    "sql_queries": {},
}


@Strategies.register(key="taxon")
class TaxonReconciliationStrategy(ReconciliationStrategy):
    """Future taxon reconciliation strategy"""

    def __init__(self):
        super().__init__(SPECIFICATION)

    async def find_candidates(self, cursor: psycopg.AsyncCursor, query: str, properties: None | dict[str, Any] = None, limit: int = 10) -> list[dict[str, Any]]:
        # Implement taxon-specific logic here
        # Could handle genus/species parsing, synonym matching, etc.
        pass

    async def get_details(self, entity_id: str, cursor) -> dict[str, Any] | None:
        """Fetch details for a specific taxon (placeholder)."""
        # When implemented, this would query the taxon authority tables.
        return None
