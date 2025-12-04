from typing import Any

from .query import BaseRepository
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification


class FeatureTypeRepository(BaseRepository):
    def __init__(self, specification: StrategySpecification) -> None:  # pylint: disable=useless-parent-delegation
        super().__init__(specification)


@Strategies.register(key="feature_type", repository_cls=FeatureTypeRepository)
class FeatureTypeReconciliationStrategy(ReconciliationStrategy):
    """Feature-specific reconciliation with feature names and descriptions"""

    def __init__(
        self, specification: StrategySpecification | None = None, repository_or_cls: type[BaseRepository] | BaseRepository | None = None
    ) -> None:
        super().__init__(specification=specification, repository_or_cls=repository_or_cls)

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific site."""
        return await self.get_repository().get_details(entity_id)
