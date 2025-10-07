from typing import Any

import psycopg

from .strategy import ReconciliationStrategy, Strategies

SPECIFICATION: dict[str, str] = {
    "key": "taxon",
    "display_name": "Taxa",
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


class TaxonQueryProxy:
    def __init__(self, specification: dict[str, str | dict[str, Any]], cursor: psycopg.AsyncCursor):
        self.specification: dict[str, str | dict[str, Any]] = specification
        self.cursor = cursor

    # Placeholder for future query methods
    # e.g., async def fetch_by_name(self, name: str, limit: int) -> list[dict[str, Any]]: ...


@Strategies.register(key="taxon")
class TaxonReconciliationStrategy(ReconciliationStrategy):
    """Future taxon reconciliation strategy"""

    def __init__(self):
        super().__init__(SPECIFICATION, TaxonQueryProxy)

    async def find_candidates(self, cursor: psycopg.AsyncCursor, query: str, properties: None | dict[str, Any] = None, limit: int = 10) -> list[dict[str, Any]]:
        # Implement taxon-specific logic here
        # Could handle genus/species parsing, synonym matching, etc.
        pass

    async def get_details(self, entity_id: str, cursor) -> dict[str, Any] | None:
        """Fetch details for a specific taxon (placeholder)."""
        # When implemented, this would query the taxon authority tables.
        return None
