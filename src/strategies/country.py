from .location import LocationReconciliationStrategy
from .strategy import Strategies


@Strategies.register(key="country", support="supported")
class CountryReconciliationStrategy(LocationReconciliationStrategy):
    """Country-specific reconciliation"""
