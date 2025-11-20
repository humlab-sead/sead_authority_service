from typing import Any

import pytest

from src.strategies.data_type import DataTypeRepository
from src.strategies.dimension import DimensionRepository
from src.strategies.feature_type import FeatureTypeRepository
from src.strategies.location import LocationRepository
from src.strategies.method import MethodRepository
from src.strategies.site import SiteRepository
from strategies.query import BaseRepository
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config
from utility import load_resource_yaml

# pylint: disable=attribute-defined-outside-init,protected-access, unused-argument

QUERY_PROXY_TESTS_SETUPS = [
    ("location", LocationRepository),
    ("country", LocationRepository),
    ("feature_type", FeatureTypeRepository),
    ("site", SiteRepository),
    ("data_type", DataTypeRepository),
    ("dimension", DimensionRepository),
    ("method", MethodRepository),
]


class TestMultipleQueryProxy:
    """Tests for common logic in various QueryProxy classes."""

    @pytest.mark.parametrize(
        "specification, proxy_cls",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_by_fuzzy_search(self, specification, proxy_cls, test_provider: ExtendedMockConfigProvider):
        """Test fuzzy name search."""

        proxy: BaseRepository = proxy_cls(specification)

        assert isinstance(proxy.specification, dict)

        id_name: str = proxy.specification["id_field"]
        mock_rows = [{id_name: 1, "label": "Test Entity 1", "name_sim": 0.9}, {id_name: 2, "label": "Test Entity 2", "name_sim": 0.8}]

        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        result: list[dict[str, Any]] = await proxy.find("test entity", limit=5)

        expected_sql: str = proxy.specification["sql_queries"]["fuzzy_find_sql"].strip()
        test_provider.cursor_mock.execute.assert_called_once_with(expected_sql, {"q": "test entity", "n": 5})
        test_provider.cursor_mock.fetchall.assert_called_once()
        assert result == mock_rows

    @pytest.mark.parametrize(
        "specification, proxy_cls",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_by_fuzzy_search_default_limit(self, specification, proxy_cls, test_provider: ExtendedMockConfigProvider):
        """Test fuzzy name search with default limit."""
        test_provider.create_connection_mock(fetchall=[], execute=None)
        proxy = proxy_cls(specification)

        await proxy.find("test")
        expected_sql: str = proxy.specification["sql_queries"]["fuzzy_find_sql"].strip()
        test_provider.cursor_mock.execute.assert_called_once_with(expected_sql, {"q": "test", "n": 10})

    @pytest.mark.parametrize(
        "specification, proxy_cls",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    @with_test_config
    async def test_get_details_valid_id(self, specification, proxy_cls, test_provider: ExtendedMockConfigProvider):
        """Test getting details with valid ID."""
        proxy = proxy_cls(specification)
        id_name: str = proxy.specification["id_field"]
        mock_row = {id_name: 123, "label": "Test", "description": "A test location", "dummpy1": 59.3293, "dummy2": 18.0686}
        test_provider.create_connection_mock(fetchone=mock_row, execute=None)

        result: dict[str, Any] | None = await proxy.get_details("123")

        expected_sql: str = proxy.specification["sql_queries"]["details_sql"].strip()
        test_provider.cursor_mock.execute.assert_called_once_with(expected_sql, {"id": 123})
        assert result == mock_row

    @pytest.mark.parametrize(
        "specification, proxy_cls",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    @with_test_config
    async def test_get_details_invalid_id(self, specification, proxy_cls, test_provider: ExtendedMockConfigProvider):
        """Test getting details with invalid ID."""
        test_provider.create_connection_mock(execute=None)
        proxy = proxy_cls(specification)
        result: dict[str, Any] | None = await proxy.get_details("not_a_number")
        assert result is None
        test_provider.cursor_mock.execute.assert_not_called()

    @pytest.mark.parametrize(
        "specification, proxy_cls",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    @with_test_config
    async def test_get_details_not_found(self, specification, proxy_cls, test_provider: ExtendedMockConfigProvider):
        """Test getting details when not found."""
        test_provider.create_connection_mock(fetchone=None, execute=None)
        proxy = proxy_cls(specification)

        result = await proxy.get_details("999")

        assert result is None
        test_provider.cursor_mock.execute.assert_called_once()
