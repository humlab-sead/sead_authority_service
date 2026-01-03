"""Tests for configuration setup helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.configuration import setup
from src.configuration.config import Config
from src.configuration.provider import ConfigProvider, ConfigStore, MockConfigProvider, reset_config_provider, set_config_provider

# pylint: disable=redefined-outer-name


@pytest.fixture()
def reset_store_and_provider():
    """Reset global store/provider for isolation."""
    ConfigStore.reset_instance()
    reset_config_provider()
    yield
    ConfigStore.reset_instance()
    reset_config_provider()


@pytest.fixture()
def provider_with_config():
    """Use a mock provider for setup tests and restore afterwards."""
    cfg = Config(data={})
    previous: ConfigProvider = set_config_provider(MockConfigProvider(cfg))
    yield cfg
    set_config_provider(previous)


@pytest.mark.asyncio
async def test_setup_connection_pool_sets_runtime_entries(monkeypatch, provider_with_config: Config) -> None:
    """_setup_connection_pool should configure runtime dsn and connection pool."""
    cfg: Config = provider_with_config
    cfg.update(
        {
            "options:database": {
                "user": "u",
                "password": "p",
                "pool_min_size": 2,
                "pool_max_size": 10,
                "pool_timeout": 30.0,
            }
        }
    )

    monkeypatch.setattr(setup, "create_db_uri", lambda **kwargs: "postgresql://test_uri")

    # Mock AsyncConnectionPool
    mock_pool = AsyncMock()
    monkeypatch.setattr(setup, "AsyncConnectionPool", lambda *args, **kwargs: mock_pool)

    await setup._setup_connection_pool(cfg, db_opts_path="options:database")  # pylint: disable=protected-access

    assert cfg.get("runtime:dsn") == "postgresql://test_uri"
    pool = cfg.get("runtime:connection_pool")
    assert pool == mock_pool


@pytest.mark.asyncio
async def test_get_connection_from_pool(provider_with_config: Config) -> None:
    """get_connection should yield connection from pool with auto-commit/rollback."""

    cfg = provider_with_config

    # Create a mock connection with commit/rollback methods
    mock_conn = AsyncMock()
    mock_conn.commit = AsyncMock()
    mock_conn.rollback = AsyncMock()

    # Create a properly mocked pool using the same pattern as conftest.py
    mock_pool = MagicMock()

    def create_connection_cm():
        @asynccontextmanager
        async def connection_context_manager():
            yield mock_conn

        return connection_context_manager()

    mock_pool.connection = MagicMock(side_effect=create_connection_cm)

    cfg.update({"runtime:connection_pool": mock_pool})

    # Use get_connection as a context manager
    async with setup.get_connection() as connection:
        assert connection == mock_conn

    # Verify commit was called (no exception)
    mock_conn.commit.assert_called_once()
    mock_conn.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_connection_missing_pool_raises(provider_with_config: Config) -> None:
    """get_connection should raise when connection pool is not initialized."""
    # Don't set runtime:connection_pool - this should cause an error

    with pytest.raises(ValueError, match="Connection pool not initialized"):
        async with setup.get_connection():
            pass
