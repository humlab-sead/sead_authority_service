from typing import Any

from strategies.query import BaseRepository

from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
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


class TaxonRepository(BaseRepository):

    def __init__(self, specification: dict[str, str | dict[str, Any]], repository_or_cls: type[BaseRepository] | BaseRepository | None = None) -> None:
        self.specification: dict[str, str | dict[str, Any]] = specification
        super().__init__(specification=specification, repository_or_cls=repository_or_cls)

    # Placeholder for future query methods
    # e.g., async def fetch_by_name(self, name: str, limit: int) -> list[dict[str, Any]]: ...


@Strategies.register(key="taxon", repository_cls=TaxonRepository)
class TaxonReconciliationStrategy(ReconciliationStrategy):
    """Future taxon reconciliation strategy"""

    def __init__(self):
        super().__init__(SPECIFICATION)

    async def find_candidates(self, query: str, properties: None | dict[str, Any] = None, limit: int = 10) -> list[dict[str, Any]]:
        # Implement taxon-specific logic here
        # Could handle genus/species parsing, synonym matching, etc.
        return []

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific taxon (placeholder)."""
        # When implemented, this would query the taxon authority tables.
        return None
