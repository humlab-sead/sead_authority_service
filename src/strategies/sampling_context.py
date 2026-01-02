from .query import BaseRepository
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification


@Strategies.register(key="sampling_context", repository_cls=BaseRepository)
class SamplingContextReconciliationStrategy(ReconciliationStrategy):
    """Sampling Context-specific reconciliation with sampling context names and descriptions"""

    def __init__(
        self, specification: StrategySpecification | None = None, repository_or_cls: type[BaseRepository] | BaseRepository | None = None
    ) -> None:
        super().__init__(specification=specification, repository_or_cls=repository_or_cls)
