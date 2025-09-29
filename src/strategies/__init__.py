from ..utility import Registry
from .interface import ReconciliationStrategy


class StrategyRegistry(Registry):
    items: dict[str, ReconciliationStrategy] = {}


Strategies: StrategyRegistry = StrategyRegistry()
