import sys
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import psycopg
import pytest
from loguru import logger

from src.configuration import Config, ConfigFactory, MockConfigProvider

# pylint: disable=unused-argument


@pytest.fixture(autouse=True, scope="session")
def setup_test_logging():
    """Configure logging for all tests with DEBUG level."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", format="{time} | {level} | {name}:{function}:{line} - {message}")


# def pytest_sessionstart(session) -> None:
#     """Hook to run before any tests are executed."""
#     os.environ["CONFIG_FILE"] = "./tests/config/config.yml"
#     os.environ["ENV_FILE"] = "./tests/.env"
#     asyncio.run(setup_config_store("./tests/config/config.yml"))


# @pytest.fixture(autouse=True)
# def setup_reset_config() -> Generator[None, Any, None]:
#     """Reset Config Store and provider before each test"""
#     ConfigStore.reset_instance()
#     reset_config_provider()
#     yield
#     ConfigStore.reset_instance()
#     reset_config_provider()


class MockRow:
    """Mock psycopg.Row that can be converted to dict"""

    def __init__(self, data) -> None:
        self._data: dict = data if isinstance(data, dict) else dict(data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data.items())

    def __len__(self):
        return len(self._data)

    def __bool__(self):
        return bool(self._data)

    # Add these methods to make it more dict-like
    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data


def mock_strategy_with_get_details(mock_strategies, value: dict[str, str]) -> AsyncMock:
    mock_strategy = AsyncMock()
    mock_strategy.get_details.return_value = value
    mock_strategies.items.get.return_value = lambda: mock_strategy
    return mock_strategy


@pytest.fixture
def test_config() -> Config:
    """Provide test configuration"""
    factory: ConfigFactory = ConfigFactory()
    config: Config = factory.load(source="./tests/config/config.yml", context="default", env_filename="./tests/.env")  # type: ignore
    # Note: Tests use mocked connections, not the real pool
    return config


class ExtendedMockConfigProvider(MockConfigProvider):
    """Extended MockConfigProvider that allows setting config after initialization"""

    def __init__(self, initial_config: Config) -> None:
        super().__init__(initial_config)
        self._mock_connection: AsyncMock | None = None

    def create_connection_mock(self, **kwargs) -> None:
        """Create a mock connection pool that returns mock connections"""
        connection = create_connection_mock(**({"execute": None} | kwargs))

        # Create mock pool
        mock_pool = MagicMock()

        # Set up connection() to return a proper async context manager
        # This function will be called by pool.connection()
        def create_connection_cm():
            @asynccontextmanager
            async def connection_context_manager():
                """Async context manager for pool.connection()"""
                yield connection

            return connection_context_manager()

        # Store reference to connection for test assertions
        self._mock_connection = connection

        # Make pool.connection a callable that returns a new context manager each time
        mock_pool.connection = MagicMock(side_effect=create_connection_cm)

        self.get_config().update({"runtime:connection_pool": mock_pool})

    @property
    def connection_mock(self) -> AsyncMock | None:
        """Get the mock connection object for assertions"""
        return getattr(self, "_mock_connection", None)

    @property
    def cursor_mock(self) -> MagicMock:
        """Get the mock cursor object for assertions"""
        if not self.connection_mock:
            raise ValueError("Connection mock not set up. Call create_connection_mock first.")

        return self.connection_mock.cursor.return_value.__aenter__.return_value


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

    # Set up cursor context manager behavior
    cursor_context_manager = AsyncMock()
    cursor_context_manager.__aenter__.return_value = mock_cursor
    cursor_context_manager.__aexit__.return_value = None
    mock_conn.cursor.return_value = cursor_context_manager
    mock_conn.cursor_instance = mock_cursor

    # Add commit and rollback methods for transaction management
    mock_conn.commit = AsyncMock()
    mock_conn.rollback = AsyncMock()

    return mock_conn
