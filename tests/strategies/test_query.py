from typing import Any
from unittest.mock import AsyncMock, MagicMock

import psycopg
import pytest
from psycopg.rows import dict_row, tuple_row

import src.strategies.query as query_module
from src.strategies.data_type import DataTypeRepository
from src.strategies.dimension import DimensionRepository
from src.strategies.feature_type import FeatureTypeRepository
from src.strategies.location import LocationRepository
from src.strategies.method import MethodRepository
from src.strategies.query import BaseRepository
from src.strategies.site import SiteRepository
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config

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


class TestMultipleRepository:
    """Tests for common logic in various Repository classes."""

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


class _StubConfigValue:
    def __init__(self, *args, **kwargs):  # noqa: ARG002
        pass

    def resolve(self):
        return {}


class TestBaseRepositoryUnit:
    def _make_repo(self, monkeypatch: pytest.MonkeyPatch, specification: dict[str, Any]) -> BaseRepository:
        monkeypatch.setattr(query_module, "ConfigValue", _StubConfigValue)
        return BaseRepository(specification, connection=None)

    def test_get_sql_queries_and_query_lookup(self, monkeypatch: pytest.MonkeyPatch):
        spec = {"key": "x", "sql_queries": {"a": "SELECT 1"}}
        repo = self._make_repo(monkeypatch, spec)
        assert repo.get_sql_queries() == {"a": "SELECT 1"}
        assert repo.get_sql_query("a") == "SELECT 1"
        assert repo.get_sql_query("missing") == ""

    def test_get_find_fuzzy_sql_fallback(self, monkeypatch: pytest.MonkeyPatch):
        repo = self._make_repo(monkeypatch, {"key": "x", "sql_queries": {}})
        assert repo.get_find_fuzzy_sql() == "select * from authority.fuzzy_site(%(q)s::text, %(n)s::int);"

    @pytest.mark.asyncio
    async def test_fetch_by_alternate_identity_no_sql_does_not_call_fetch_all(self, monkeypatch: pytest.MonkeyPatch):
        repo = self._make_repo(monkeypatch, {"key": "x", "sql_queries": {}})
        fetch_all = AsyncMock(return_value=[])
        monkeypatch.setattr(repo, "fetch_all", fetch_all)

        assert await repo.fetch_by_alternate_identity("ABC") == []
        fetch_all.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_fetch_by_alternate_identity_calls_fetch_all(self, monkeypatch: pytest.MonkeyPatch):
        repo = self._make_repo(monkeypatch, {"key": "x", "sql_queries": {"alternate_identity_sql": "SQL"}})
        fetch_all = AsyncMock(return_value=[{"id": 1}])
        monkeypatch.setattr(repo, "fetch_all", fetch_all)

        rows = await repo.fetch_by_alternate_identity("ABC")
        assert rows == [{"id": 1}]
        fetch_all.assert_awaited_once_with("SQL", {"alternate_identity": "ABC"})

    @pytest.mark.asyncio
    async def test_get_details_handles_psycopg_error(self, monkeypatch: pytest.MonkeyPatch):
        repo = self._make_repo(monkeypatch, {"key": "x", "sql_queries": {"details_sql": "SQL"}})
        fetch_one = AsyncMock(side_effect=psycopg.Error("db"))
        monkeypatch.setattr(repo, "fetch_one", fetch_one)

        assert await repo.get_details("1") is None

    @pytest.mark.asyncio
    async def test_get_details_invalid_id_does_not_call_fetch_one(self, monkeypatch: pytest.MonkeyPatch):
        repo = self._make_repo(monkeypatch, {"key": "x", "sql_queries": {"details_sql": "SQL"}})
        fetch_one = AsyncMock(return_value={"id": 1})
        monkeypatch.setattr(repo, "fetch_one", fetch_one)

        assert await repo.get_details("not_a_number") is None
        fetch_one.assert_not_awaited()
