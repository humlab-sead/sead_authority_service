import asyncio
import os
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock

import psycopg
import pytest

from src.configuration import Config, ConfigFactory, ConfigStore, MockConfigProvider, reset_config_provider, setup_config_store

# pylint: disable=unused-argument


def pytest_sessionstart(session) -> None:
    """Hook to run before any tests are executed."""
    os.environ["CONFIG_FILE"] = "./tests/config.yml"
    os.environ["ENV_FILE"] = "./tests/.env"
    asyncio.run(setup_config_store("./tests/config.yml"))


@pytest.fixture(autouse=True)
def setup_reset_config() -> Generator[None, Any, None]:
    """Reset Config Store and provider before each test"""
    ConfigStore.reset_instance()
    reset_config_provider()
    yield
    ConfigStore.reset_instance()
    reset_config_provider()


class MockRow:
    """Mock psycopg.Row that can be converted to dict"""

    def __init__(self, data) -> None:
        self._data: Any = data

    def keys(self) -> Any:
        return self._data.keys()

    def values(self) -> Any:
        return self._data.values()

    def items(self) -> Any:
        return self._data.items()

    def __getitem__(self, key) -> Any:
        return self._data[key]

    def __iter__(self) -> Any:
        return iter(self._data.items())


def mock_strategy_with_get_details(mock_strategies, value: dict[str, str]) -> AsyncMock:
    mock_strategy = AsyncMock()
    mock_strategy.get_details.return_value = value
    mock_strategies.items.get.return_value = lambda: mock_strategy
    return mock_strategy


@pytest.fixture
def test_config() -> Config:
    """Provide test configuration"""

    async def async_mock_connection():
        mock_conn = AsyncMock(spec=psycopg.AsyncConnection)
        mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)

        async def async_fetchone():
            mock_row_data = {
                "ID": 123,
                "Name": "Test Site",
                "Description": "A test archaeological site",
                "National ID": "TEST123",
                "Latitude": 59.8586,
                "Longitude": 17.6389,
            }
            return MockRow(mock_row_data)

        async def async_execute(query, params=None):
            pass

        mock_cursor.fetchone.side_effect = async_fetchone
        mock_cursor.execute.side_effect = async_execute
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    factory: ConfigFactory = ConfigFactory()
    config: Config = factory.load(source="./tests/config.yml", context="default", env_filename="./tests/.env")
    config.update(
        {
            "runtime": {
                "connection_factory": async_mock_connection,
            }
        }
    )
    return config
    # return Config(data={"options": {"id_base": "https://w3id.org/sead/id/"}, "runtime": {"connection_factory": async_mock_connection}})

class ExtendedMockConfigProvider(MockConfigProvider):
    """Extended MockConfigProvider that allows setting config after initialization"""

    def create_connection_mock(self, **kwargs) -> None:
        connection = create_connection_mock(**({'execute': None} | kwargs))
        self.get_config().update({"runtime.connection": connection})

    @property
    def connection_mock(self) -> MagicMock:
        return self.get_config().get("runtime.connection")
    
@pytest.fixture
def test_provider(test_config: Config) -> ExtendedMockConfigProvider:  # pylint: disable=redefined-outer-name
    """Provide TestConfigProvider with test configuration"""
    provider = ExtendedMockConfigProvider(test_config)
    return provider

def create_connection_mock(**method_returns: Any) -> AsyncMock:
    """
    Create an async psycopg connection mock whose cursor methods return given values.

    Example:
        mock_conn = create_connection_mock(
            fetchall=[{"id": 1, "name": "Alice"}],
            execute=None,
            fetchone={"id": 2, "name": "Bob"},
        )
    """
    mock_conn = AsyncMock(spec=psycopg.AsyncConnection)
    mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)

    # Set up each requested async method to return the specified value
    for method_name, return_value in method_returns.items():
        method = getattr(mock_cursor, method_name)
        # Wrap lists of dicts into MockRow for convenience
        if isinstance(return_value, list) and return_value and isinstance(return_value[0], dict):
            return_value = [MockRow(r) for r in return_value]
        elif isinstance(return_value, dict):
            return_value = MockRow(return_value)
        method.return_value = return_value

    # Default: ensure context manager behavior works
    mock_conn.cursor().return_value = mock_cursor
    mock_conn.cursor().return_value.__aenter__.return_value = mock_cursor
    mock_conn.cursor().return_value.__aexit__.return_value = None

    return mock_conn