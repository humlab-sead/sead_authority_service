from .query import BaseRepository
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

class DataTypeRepository(BaseRepository):
    """Data Type-specific query proxy"""


@Strategies.register(key="data_type")
class DataTypeReconciliationStrategy(ReconciliationStrategy):
    """Data Type-specific reconciliation with data type names and descriptions"""

    def __init__(self, specification: StrategySpecification | None = None) -> None:
        super().__init__(specification, DataTypeRepository)
