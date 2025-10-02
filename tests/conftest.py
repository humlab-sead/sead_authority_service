import os
from typing import Any, Callable, Generator
from unittest.mock import AsyncMock

import psycopg
import pytest

from src.configuration.config import Config
from src.configuration.inject import (ConfigStore, MockConfigProvider,
                                      reset_config_provider)
from src.configuration.setup import setup_config_store


async def pytest_sessionstart(session) -> None:
    """Hook to run before any tests are executed."""
    os.environ["CONFIG_FILE"] = "./tests/config.yml"
    os.environ["ENV_FILE"] = "./tests/.env"
    await setup_config_store("./tests/config.yml")


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
def test_config():
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
    
    return Config(data={
        "options": {"id_base": "https://w3id.org/sead/id/"}, 
        "runtime": {"connection_factory": async_mock_connection}
    })


@pytest.fixture
def test_provider(test_config):
    """Provide TestConfigProvider with test configuration"""
    return MockConfigProvider(test_config)
