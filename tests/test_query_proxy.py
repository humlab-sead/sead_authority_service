from typing import Any

import pytest

from src.strategies.country import SPECIFICATION as COUNTRY_SPECIFICATION
from src.strategies.data_type import SPECIFICATION as DATA_TYPE_SPECIFICATION
from src.strategies.data_type import DataTypeQueryProxy
from src.strategies.dimension import SPECIFICATION as DIMENSION_SPECIFICATION
from src.strategies.dimension import DimensionQueryProxy
from src.strategies.feature_type import SPECIFICATION as FEATURE_TYPE_SPECIFICATION
from src.strategies.feature_type import FeatureTypeQueryProxy
from src.strategies.location import SPECIFICATION as LOCATION_SPECIFICATION
from src.strategies.location import LocationQueryProxy
from src.strategies.method import SPECIFICATION as METHOD_SPECIFICATION
from src.strategies.method import MethodQueryProxy
from src.strategies.site import SPECIFICATION as SITE_TYPE_SPECIFICATION
from src.strategies.site import SiteQueryProxy
from strategies.query import DatabaseQueryProxy
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config

# pylint: disable=attribute-defined-outside-init,protected-access, unused-argument

SQL_QUERIES: dict[str, str] = LOCATION_SPECIFICATION["sql_queries"]

QUERY_PROXY_TESTS_SETUPS = [
    (LOCATION_SPECIFICATION, LocationQueryProxy),
    (COUNTRY_SPECIFICATION, LocationQueryProxy),
    (FEATURE_TYPE_SPECIFICATION, FeatureTypeQueryProxy),
    (SITE_TYPE_SPECIFICATION, SiteQueryProxy),
    (DATA_TYPE_SPECIFICATION, DataTypeQueryProxy),
    (DIMENSION_SPECIFICATION, DimensionQueryProxy),
    (METHOD_SPECIFICATION, MethodQueryProxy),
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
        id_name: str = specification["id_field"]
        mock_rows = [{id_name: 1, "label": "Test Entity 1", "name_sim": 0.9}, {id_name: 2, "label": "Test Entity 2", "name_sim": 0.8}]

        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)
        proxy: DatabaseQueryProxy = proxy_cls(specification)

        result: list[dict[str, Any]] = await proxy.fetch_by_fuzzy_label("test entity", limit=5)

        sql_queries: dict[str, str] = specification["sql_queries"]
        expected_sql: str = sql_queries["fuzzy_label_sql"]
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

        await proxy.fetch_by_fuzzy_label("test")
        sql_queries: dict[str, str] = specification["sql_queries"]
        expected_sql: str = sql_queries["fuzzy_label_sql"]
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
        id_name: str = specification["id_field"]
        mock_row = {id_name: 123, "label": "Test", "description": "A test location", "dummpy1": 59.3293, "dummy2": 18.0686}
        test_provider.create_connection_mock(fetchone=mock_row, execute=None)

        result: dict[str, Any] | None = await proxy.get_details("123")

        sql_queries: dict[str, str] = specification["sql_queries"]
        expected_sql: str = sql_queries["details_sql"]
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
