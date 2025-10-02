from typing import Any

import psycopg

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

    def get_properties_meta(self) -> list[dict[str, str]]:
        """Return metadata for taxon-specific properties used in enhanced reconciliation"""
        return [
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
        ]

    async def find_candidates(self, cursor: psycopg.AsyncCursor, query: str, properties: None | dict[str, Any] = None, limit: int = 10) -> list[dict[str, Any]]:
        # Implement taxon-specific logic here
        # Could handle genus/species parsing, synonym matching, etc.
        pass

    async def get_details(self, entity_id: str, cursor) -> dict[str, Any] | None:
        """Fetch details for a specific taxon (placeholder)."""
        # When implemented, this would query the taxon authority tables.
        return None
