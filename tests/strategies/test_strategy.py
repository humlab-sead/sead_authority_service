from typing import Any, Type
from unittest import mock
from unittest.mock import AsyncMock, patch

import psycopg
import pytest

from configuration.provider import MockConfigProvider
from src.strategies.strategy import ReconciliationStrategy, Strategies
from strategies import strategy
from strategies.query import AbstractRepository
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config

# pylint: disable=attribute-defined-outside-init,protected-access, unused-argument


class TestMultipleReconciliationStrategy:

    @pytest.mark.parametrize(
        "strategy_cls",
        [strategy_cls for strategy_cls in Strategies.items.values()],
    )
    @pytest.mark.asyncio
    @with_test_config
    async def test_reconciliation_strategy(
        self,
        strategy_cls: Type[ReconciliationStrategy],
        test_provider: ExtendedMockConfigProvider,
    ) -> None:
        """Test reconciliation strategy."""

        strategy = strategy_cls()

        if strategy_cls.__name__.split(".")[-1] in [
            "GeoNamesReconciliationStrategy",
            "BibliographicReferenceReconciliationStrategy",
            "RAGMethodsReconciliationStrategy",
            "TaxonReconciliationStrategy",
        ]:
            return

        key: str = strategy.specification.get("key", "unknown")
        id_field: str = strategy.specification.get("id_field", "id")

        assert key == strategy.key
        assert strategy.get_entity_id_field() == id_field
        assert strategy.get_label_field() == strategy.specification.get("label_field", "name")

        mock_rows = [
            {id_field: 1, "label": f"Test {key.capitalize()} 1", "name_sim": 0.9},
            {id_field: 2, "label": f"Test {key.capitalize()} 2", "name_sim": 0.8},
        ]

        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        result: list[dict[str, Any]] = await strategy.find_candidates(f"Hej {key}", limit=5)

        test_provider.connection_mock.cursor_instance.execute.assert_called()
        test_provider.connection_mock.cursor_instance.fetchall.assert_called()
        assert result == mock_rows

    @pytest.mark.parametrize(
        "strategy_cls",
        [strategy_cls for strategy_cls in Strategies.items.values()],
    )
    @with_test_config
    def test_get_entity_id_field(self, strategy_cls, test_provider: MockConfigProvider):
        """Test getting entity ID field name."""
        strategy: ReconciliationStrategy = strategy_cls()
        assert strategy.get_entity_id_field() == strategy.specification["id_field"]

    # @pytest.mark.parametrize(
    #     "strategy_cls",
    #     [strategy_cls for strategy_cls in Strategies.items.values()],
    # )
    # @with_test_config
    # def test_get_label_field(self, strategy_cls, test_provider: MockConfigProvider):
    #     """Test getting label field name."""
    #     strategy: ReconciliationStrategy = strategy_cls()
    #     assert strategy.get_label_field() == "label"

    # @pytest.mark.parametrize(
    #     "strategy_cls",
    #     [strategy_cls for strategy_cls in Strategies.items.values()],
    # )
    # @with_test_config
    # def test_get_id_path(self, strategy_cls, test_provider: MockConfigProvider):
    #     """Test getting ID path."""
    #     strategy: ReconciliationStrategy = strategy_cls()
    #     assert strategy.specification.get("key", "unknown") == strategy.key

    @pytest.mark.parametrize(
        "strategy_cls",
        [strategy_cls for strategy_cls in Strategies.items.values()],
    )
    @with_test_config
    def test_get_property_settings(self, strategy_cls, test_provider: MockConfigProvider):
        """Test get_property_settings method returns location-specific settings."""
        strategy = strategy_cls()
        settings = strategy.get_property_settings()

        assert isinstance(settings, dict)

    # @patch("src.strategies.location.LocationRepository")
    # @pytest.mark.parametrize(
    #     "strategy_cls",
    #     [strategy_cls for strategy_cls in Strategies.items.values()],
    # )
    # @pytest.mark.asyncio
    # @with_test_config
    # async def test_find_candidates_by_fuzzy_search(self, mock_query_proxy_class, strategy_cls, test_provider: MockConfigProvider):
    #     """Test finding candidates by fuzzy search when no national ID."""
    #     strategy: ReconciliationStrategy = strategy_cls()
    #     mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
    #     mock_proxy = AsyncMock()
    #     mock_query_proxy_class.return_value = mock_proxy

    #     mock_proxy.fetch_location_by_national_id.return_value = []
    #     mock_locations: list[dict[str, Any]] = [
    #         {"location_id": 1, "label": "Test Location", "name_sim": 0.9},
    #         {"location_id": 2, "label": "Another Location", "name_sim": 0.7},
    #     ]
    #     mock_proxy.find.return_value = mock_locations

    #     result = await strategy.find_candidates(mock_cursor, "test location", {}, limit=5)

    #     mock_proxy.find.assert_called_once_with("test location", 5)
    #     # Results should be sorted by name_sim in descending order
    #     assert result[0]["name_sim"] >= result[1]["name_sim"]

    # @pytest.mark.asyncio
    # @pytest.mark.parametrize(
    #     "strategy_cls",
    #     [strategy_cls for strategy_cls in Strategies.items.values()],
    # )
    # @patch("src.strategies.location.LocationRepository")
    # @with_test_config
    # async def test_get_details(self, mock_query_proxy_class, strategy_cls, test_provider: ExtendedMockConfigProvider):
    #     """Test getting site details."""

    #     strategy: ReconciliationStrategy = strategy_cls()
    #     mock_rows = [{"ID": 123, "Name": "Test Site", "Description": "A test site"}]
    #     test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

    #     result = await strategy.get_details("123")

    #     test_provider.connection_mock.egy.get_details.assert_called_once_with("123")
    #     assert result == mock_rows
