# from typing import Any
# from unittest.mock import AsyncMock, MagicMock, patch

# import psycopg
# import pytest
# from src.strategies.query import QueryProxy
# from src.strategies.interface import ReconciliationStrategy
# from src.strategies.location import SPECIFICATION as LOCATION_SPECIFICATION, LocationReconciliationStrategy, LocationQueryProxy
# from src.strategies.country import SPECIFICATION as COUNTRY_SPECIFICATION, CountryReconciliationStrategy
# from src.strategies.feature_type import SPECIFICATION as FEATURE_TYPE_SPECIFICATION, FeatureTypeReconciliationStrategy, FeatureTypeQueryProxy
# from src.strategies.site import SPECIFICATION as SITE_TYPE_SPECIFICATION, SiteReconciliationStrategy, SiteQueryProxy

# from src.configuration.inject import MockConfigProvider
# from tests.decorators import with_test_config

# # pylint: disable=attribute-defined-outside-init,protected-access, unused-argument

# TEST_SETUPS = [
#     ("location", LOCATION_SPECIFICATION, LocationReconciliationStrategy, LocationQueryProxy),
#     ("country", COUNTRY_SPECIFICATION, CountryReconciliationStrategy, LocationQueryProxy),
#     ("feature_type", FEATURE_TYPE_SPECIFICATION, FeatureTypeReconciliationStrategy, FeatureTypeQueryProxy),
#     ("site", SITE_TYPE_SPECIFICATION, SiteReconciliationStrategy, SiteQueryProxy),
# ]

# class TestReconciliationStrategy:
#     """Tests for common logic in various ReconciliationStrategy classes."""

#     @pytest.mark.parametrize(
#         "entity_id, specification, strategy_class, query_proxy_class",
#         TEST_SETUPS,
#     )
#     @with_test_config
#     def test_get_entity_id_field(self, entity_id, specification, strategy_class, query_proxy_class, test_provider: MockConfigProvider):
#         """Test getting entity ID field name."""
#         mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
#         proxy: QueryProxy = query_proxy_class(specification, mock_cursor)
#         strategy: ReconciliationStrategy = strategy_class(specification, proxy)
#         assert strategy.get_entity_id_field() == specification["id_field"]

#     @pytest.mark.parametrize(
#         "specification, strategy_class",
#         TEST_SETUPS,
#     )
#     @with_test_config
#     def test_get_label_field(entity_id, specification, strategy_class, query_proxy_class, test_provider: MockConfigProvider):
#         """Test getting label field name."""
#         strategy: ReconciliationStrategy = strategy_class(specification)
#         assert strategy.get_label_field() == "label"

#     @pytest.mark.parametrize(
#         "specification, strategy_class",
#         TEST_SETUPS,
#     )
#     @with_test_config
#     def test_get_id_path(entity_id, specification, strategy_class, query_proxy_class, test_provider: MockConfigProvider):
#         """Test getting ID path."""
#         strategy: ReconciliationStrategy = strategy_class(specification)
#         assert strategy.get_id_path() == "location"

#     @pytest.mark.parametrize(   
#         "entity_id, specification, strategy_class, query_proxy_class",
#         TEST_SETUPS,
#     )
#     @with_test_config
#     def test_get_property_settings(entity_id, specification, strategy_class, query_proxy_class, test_provider: MockConfigProvider):
#         """Test get_property_settings method returns location-specific settings."""
#         strategy = strategy_class(specification, query_proxy_class)
#         settings = strategy.get_property_settings()

#         assert isinstance(settings, dict)

#     @patch("src.strategies.location.LocationQueryProxy")
#     @pytest.mark.parametrize(
#         "specification, strategy_class",
#         TEST_SETUPS,
#     )
#     @pytest.mark.asyncio
#     @with_test_config
#     async def test_find_candidates_by_fuzzy_search(self, mock_query_proxy_class, specification, strategy_class, test_provider: MockConfigProvider):
#         """Test finding candidates by fuzzy search when no national ID."""
#         strategy: ReconciliationStrategy = strategy_class(specification)
#         mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
#         mock_proxy = AsyncMock()
#         mock_query_proxy_class.return_value = mock_proxy

#         mock_proxy.fetch_location_by_national_id.return_value = []
#         mock_locations: list[dict[str, Any]] = [
#             {"location_id": 1, "label": "Test Location", "name_sim": 0.9},
#             {"location_id": 2, "label": "Another Location", "name_sim": 0.7},
#         ]
#         mock_proxy.fetch_by_fuzzy_search.return_value = mock_locations

#         result = await strategy.find_candidates(mock_cursor, "test location", {}, limit=5)

#         mock_proxy.fetch_by_fuzzy_search.assert_called_once_with("test location", 5)
#         # Results should be sorted by name_sim in descending order
#         assert result[0]["name_sim"] >= result[1]["name_sim"]

#     @pytest.mark.asyncio
#     @pytest.mark.parametrize(
#         "specification, strategy_class",
#         TEST_SETUPS,
#     )
#     @patch("src.strategies.location.LocationQueryProxy")
#     @with_test_config
#     async def test_get_details(self, mock_query_proxy_class, specification, strategy_class, test_provider: MockConfigProvider):
#         """Test getting site details."""

#         strategy: ReconciliationStrategy = strategy_class(specification)
#         mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
#         mock_proxy = AsyncMock()
#         mock_query_proxy_class.return_value = mock_proxy

#         expected_details = {"ID": 123, "Name": "Test Site", "Description": "A test site"}
#         mock_proxy.get_details.return_value = expected_details

#         result = await strategy.get_details("123", mock_cursor)

#         # The LocationQueryProxy is called with the LOCATION_SPECIFICATION and cursor
#         mock_query_proxy_class.assert_called_once_with(LOCATION_SPECIFICATION, mock_cursor)
#         mock_proxy.get_details.assert_called_once_with("123")
#         assert result == expected_details
