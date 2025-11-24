from .location import LocationReconciliationStrategy
from .strategy import Strategies


@Strategies.register(key="administrative_region")
class AdministrativeRegionReconciliationStrategy(LocationReconciliationStrategy):
    """Administrative region-specific reconciliation"""
