from typing import Any
from unittest.mock import AsyncMock

import psycopg
import pytest
from src.strategies.location import LocationQueryProxy, SPECIFICATION as LOCATION_SPECIFICATION
from src.strategies.country import SPECIFICATION as COUNTRY_SPECIFICATION
from src.strategies.feature_type import SPECIFICATION as FEATURE_TYPE_SPECIFICATION, FeatureTypeQueryProxy
from src.strategies.site import SPECIFICATION as SITE_TYPE_SPECIFICATION, SiteQueryProxy

# pylint: disable=attribute-defined-outside-init,protected-access, unused-argument

SQL_QUERIES: dict[str, str] = LOCATION_SPECIFICATION["sql_queries"]

QUERY_PROXY_TESTS_SETUPS = [
    (LOCATION_SPECIFICATION, LocationQueryProxy),
    (COUNTRY_SPECIFICATION, LocationQueryProxy),
    (FEATURE_TYPE_SPECIFICATION, FeatureTypeQueryProxy),
    (SITE_TYPE_SPECIFICATION, SiteQueryProxy),
]


class TestMultipleQueryProxy:
    """Tests for common logic in various QueryProxy classes."""

    @pytest.mark.parametrize(
        "specification, query_proxy_class",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    async def test_fetch_by_fuzzy_search(self, specification, query_proxy_class):
        """Test fuzzy name search."""
        mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
        proxy = query_proxy_class(specification, mock_cursor)

        id_name: str = specification["id_field"]
        mock_rows = [{id_name: 1, "label": "Test Entity 1", "name_sim": 0.9}, {id_name: 2, "label": "Test Entity 2", "name_sim": 0.8}]
        mock_cursor.fetchall.return_value = mock_rows

        result: list[dict[str, Any]] = await proxy.fetch_by_fuzzy_label("test entity", limit=5)

        sql_queries: dict[str, str] = specification["sql_queries"]
        expected_sql: str = sql_queries["fuzzy_label_sql"]
        mock_cursor.execute.assert_called_once_with(expected_sql, {"q": "test entity", "n": 5})
        mock_cursor.fetchall.assert_called_once()
        assert result == mock_rows

    @pytest.mark.parametrize(
        "specification, query_proxy_class",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    async def test_fetch_by_fuzzy_search_default_limit(self, specification, query_proxy_class):
        """Test fuzzy name search with default limit."""
        mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
        proxy = query_proxy_class(specification, mock_cursor)

        mock_cursor.fetchall.return_value = []

        await proxy.fetch_by_fuzzy_label("test")
        sql_queries: dict[str, str] = specification["sql_queries"]
        expected_sql: str = sql_queries["fuzzy_label_sql"]
        mock_cursor.execute.assert_called_once_with(expected_sql, {"q": "test", "n": 10})

    @pytest.mark.parametrize(
        "specification, query_proxy_class",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    async def test_get_details_valid_id(self, specification, query_proxy_class):
        """Test getting details with valid ID."""
        mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
        proxy = query_proxy_class(specification, mock_cursor)
        id_name: str = specification["id_field"]
        mock_row = {id_name: 123, "label": "Test", "description": "A test location", "dummpy1": 59.3293, "dummy2": 18.0686}
        mock_cursor.fetchone.return_value = mock_row

        result: dict[str, Any] | None = await proxy.get_details("123")

        sql_queries: dict[str, str] = specification["sql_queries"]
        expected_sql: str = sql_queries["get_details"]
        mock_cursor.execute.assert_called_once_with(expected_sql, {"id": 123})
        assert result == mock_row

    @pytest.mark.parametrize(
        "specification, query_proxy_class",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    async def test_get_details_invalid_id(self, specification, query_proxy_class):
        """Test getting details with invalid ID."""
        mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
        proxy = query_proxy_class(specification, mock_cursor)
        result: dict[str, Any] | None = await proxy.get_details("not_a_number")
        assert result is None
        mock_cursor.execute.assert_not_called()

    @pytest.mark.parametrize(
        "specification, query_proxy_class",
        QUERY_PROXY_TESTS_SETUPS,
    )
    @pytest.mark.asyncio
    async def test_get_details_not_found(self, specification, query_proxy_class):
        """Test getting details when not found."""
        mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
        proxy = query_proxy_class(specification, mock_cursor)
        mock_cursor.fetchone.return_value = None

        result = await proxy.get_details("999")

        assert result is None
        mock_cursor.execute.assert_called_once()
