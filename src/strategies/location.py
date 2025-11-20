from .query import BaseRepository
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

class LocationRepository(BaseRepository):
    """Location-specific query proxy"""


@Strategies.register(key="location")
class LocationReconciliationStrategy(ReconciliationStrategy):
    """Location-specific reconciliation with place names and coordinates"""

    def __init__(self, specification: StrategySpecification | None = None) -> None:
        super().__init__(specification, LocationRepository)
