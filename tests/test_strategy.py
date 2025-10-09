# from typing import Any, Type
# from unittest.mock import AsyncMock

# import psycopg
# import pytest

# from src.configuration.inject import MockConfigProvider
# from src.strategies.country import SPECIFICATION as COUNTRY_SPECIFICATION
# from src.strategies.country import CountryReconciliationStrategy
# from src.strategies.data_type import SPECIFICATION as DATA_TYPE_SPECIFICATION
# from src.strategies.data_type import (DataTypeQueryProxy,
#                                       DataTypeReconciliationStrategy)
# from src.strategies.dimension import SPECIFICATION as DIMENSION_SPECIFICATION
# from src.strategies.dimension import (DimensionQueryProxy,
#                                       DimensionReconciliationStrategy)
# from src.strategies.feature_type import \
#     SPECIFICATION as FEATURE_TYPE_SPECIFICATION
# from src.strategies.feature_type import (FeatureTypeQueryProxy,
#                                          FeatureTypeReconciliationStrategy)
# from src.strategies.location import SPECIFICATION as LOCATION_SPECIFICATION
# from src.strategies.location import (LocationQueryProxy,
#                                      LocationReconciliationStrategy)
# from src.strategies.method import SPECIFICATION as METHOD_SPECIFICATION
# from src.strategies.method import (MethodQueryProxy,
#                                    MethodReconciliationStrategy)
# from src.strategies.query import QueryProxy
# from src.strategies.site import SPECIFICATION as SITE_TYPE_SPECIFICATION
# from src.strategies.site import SiteQueryProxy, SiteReconciliationStrategy
# from strategies.strategy import ReconciliationStrategy, StrategySpecification
# from tests.decorators import with_test_config

# # pylint: disable=attribute-defined-outside-init,protected-access, unused-argument

# SQL_QUERIES: dict[str, str] = LOCATION_SPECIFICATION["sql_queries"]

# CountryQueryProxy = LocationQueryProxy  # Country uses the same QueryProxy as Location

# RECONCILIATION_STRATEGY_SETUPS: tuple[dict[str, Any], ReconciliationStrategy, QueryProxy] = [
#     (LOCATION_SPECIFICATION, LocationReconciliationStrategy, LocationQueryProxy),
#     (COUNTRY_SPECIFICATION, CountryReconciliationStrategy, CountryQueryProxy),
#     (FEATURE_TYPE_SPECIFICATION, FeatureTypeReconciliationStrategy, FeatureTypeQueryProxy),
#     (SITE_TYPE_SPECIFICATION, SiteReconciliationStrategy, SiteQueryProxy),
#     (DATA_TYPE_SPECIFICATION, DataTypeReconciliationStrategy, DataTypeQueryProxy),
#     (DIMENSION_SPECIFICATION, DimensionReconciliationStrategy, DimensionQueryProxy),
#     (METHOD_SPECIFICATION, MethodReconciliationStrategy, MethodQueryProxy),
# ]


# class TestMultipleReconciliationStrategy:

#     @pytest.mark.parametrize(
#         "specification, strategy_class, query_proxy_class",
#         RECONCILIATION_STRATEGY_SETUPS,
#     )
#     @pytest.mark.asyncio
#     @with_test_config
#     async def test_reconciliation_strategy(self, specification: StrategySpecification,
#           strategy_class: Type[ReconciliationStrategy], query_proxy_class: Type[QueryProxy], test_provider: MockConfigProvider) -> None:
#         """Test reconciliation strategy."""
#         mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
#         proxy = query_proxy_class(specification, mock_cursor)
#         id_field: str = specification.get("id_field", "id")
#         key: str = specification.get("key", "unknown")
#         mock_rows = [{id_field: 1, "label": f"Test {key.capitalize()} 1", "name_sim": 0.9},
#                       {id_field: 2, "label": f"Test {key.capitalize()} 2", "name_sim": 0.8}]
#         mock_cursor.fetchall.return_value = mock_rows
#         strategy_class_instance = strategy_class()
#         assert strategy_class_instance.specification == specification

#         result: list[dict[str, Any]] = await proxy.fetch_by_fuzzy_label("test site", limit=5)

#         expected_sql: str = SQL_QUERIES["fuzzy_label_sql"]
#         mock_cursor.execute.assert_called_once_with(expected_sql, {"q": "test site", "n": 5})
#         mock_cursor.fetchall.assert_called_once()
#         assert result == mock_rows
