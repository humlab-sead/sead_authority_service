"""Test fixtures and utilities for configuration management"""

from contextlib import contextmanager
from typing import Any, Dict, Generator
from unittest.mock import AsyncMock

import psycopg
import pytest

from src.configuration.config import Config
from src.configuration.inject import (ConfigProvider, ConfigStore,
                                      MockConfigProvider,
                                      reset_config_provider,
                                      set_config_provider)


@contextmanager
def patch_config_provider(provider: ConfigProvider) -> Generator[ConfigProvider, None, None]:
    """Context manager to temporarily replace the config provider"""
    original_provider = set_config_provider(provider)
    try:
        yield provider
    finally:
        set_config_provider(original_provider)


@contextmanager
def config_context(config_dict: Dict[str, Any]) -> Generator[Config, None, None]:
    """Context manager that provides a test configuration"""
    config = Config(data=config_dict)
    provider = MockConfigProvider(config)

    with patch_config_provider(provider):
        yield config


@pytest.fixture
def reset_config():
    """Fixture to reset Config Store and provider before each test"""
    ConfigStore.reset_instance()
    reset_config_provider()
    yield
    ConfigStore.reset_instance()
    reset_config_provider()


def mock_connection():
    """Create a mock connection for testing"""
    mock_conn = AsyncMock(spec=psycopg.AsyncConnection)
    mock_conn.cursor.return_value = AsyncMock(spec=psycopg.AsyncCursor)
    return mock_conn


@pytest.fixture
def test_config_dict():
    """Default test configuration dictionary"""
    return {
        "options": {"id_base": "https://test.example.com/sead/id/"},
        "database": {"host": "localhost", "port": 5432, "database": "test_sead", "user": "test_user", "password": "test_password"},
        "runtime": {"connection_factory": lambda: mock_connection()},
        "logging": {"level": "DEBUG"},
    }


@pytest.fixture
def test_config_provider(test_config_dict):
    """Fixture that provides a MockConfigProvider with default test config"""
    config = Config(data=test_config_dict)
    return MockConfigProvider(config)


@pytest.fixture
def mock_config_context(test_config_provider):
    """Fixture that sets up a test config context for the duration of the test"""
    with patch_config_provider(test_config_provider):
        yield test_config_provider


# Convenience functions for manual testing
def setup_test_config(config_dict: Dict[str, Any] = None) -> MockConfigProvider:
    """Manually set up test configuration (for use outside pytest)"""
    if config_dict is None:
        config_dict = {"options": {"id_base": "https://test.example.com/sead/id/", "database": {"host": "localhost"}}}

    config = Config(data=config_dict)
    provider = MockConfigProvider(config)
    set_config_provider(provider)
    return provider


def restore_production_config():
    """Restore production configuration provider"""
    reset_config_provider()
