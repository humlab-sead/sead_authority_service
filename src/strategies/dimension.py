from .query import BaseRepository
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification


class DimensionRepository(BaseRepository):
    """Dimension-specific query proxy"""


@Strategies.register(key="dimension", repository_cls=DimensionRepository)
class DimensionReconciliationStrategy(ReconciliationStrategy):
    """Dimension-specific reconciliation with place names and coordinates"""

    def __init__(
        self, specification: StrategySpecification | str | None = None, repository_or_cls: type[BaseRepository] | BaseRepository | None = None
    ) -> None:
        super().__init__(specification=specification, repository_or_cls=repository_or_cls)
