from .location import LocationReconciliationStrategy
from .strategy import Strategies


@Strategies.register(key="country")
class CountryReconciliationStrategy(LocationReconciliationStrategy):
    """Country-specific reconciliation"""
