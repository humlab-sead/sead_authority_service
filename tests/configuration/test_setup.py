"""Tests for configuration setup helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

import main
from src.configuration import setup
from src.configuration.config import Config
from src.configuration.provider import ConfigProvider, ConfigStore, MockConfigProvider, reset_config_provider, set_config_provider
from src.strategies.configured_classifier import CLASSIFIER_KEYS, ClassifierConfigurationError, validate_classifier_configuration

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
async def test_get_connection_missing_pool_raises(provider_with_config: Config) -> None:  # pylint: disable=unused-argument
    """get_connection should raise when connection pool is not initialized."""
    # Don't set runtime:connection_pool - this should cause an error

    with pytest.raises(ValueError, match="Connection pool not initialized"):
        async with setup.get_connection():
            pass


def _classifier_config() -> dict[str, Any]:
    table_specs: dict[str, Any] = {
        key: {
            "name": key.replace("_", " ").title(),
            "id_column": f"{key}_id",
            "label_column": f"{key}_label",
            "description_column": None,
            "reconciliation": "simple",
        }
        for key in CLASSIFIER_KEYS
    }
    table_specs["data_type"] = {
        "name": "Data Type",
        "id_column": "data_type_id",
        "label_column": "data_type_name",
        "description_column": "definition",
        "reconciliation": "simple",
    }
    table_specs["feature_type"] = {
        "name": "Feature Type",
        "id_column": "feature_type_id",
        "label_column": "feature_type_name",
        "description_column": "feature_type_description",
        "reconciliation": "simple",
    }
    return {
        "table_specs": table_specs,
        "options": {"reconciliation": {"label_threshold": 0.30, "description_threshold": 0.50}},
    }


def _drop_classifier_key(config: dict[str, Any]) -> None:
    del config["table_specs"]["feature_type"]


def _drop_last_classifier_key(config: dict[str, Any]) -> None:
    del config["table_specs"][CLASSIFIER_KEYS[-1]]


def _drop_marker(config: dict[str, Any]) -> None:
    del config["table_specs"]["feature_type"]["reconciliation"]


def _add_unregistered_marked_key(config: dict[str, Any]) -> None:
    config["table_specs"]["location"] = {
        "id_column": "location_id",
        "label_column": "location_name",
        "reconciliation": "simple",
    }


def _blank_label_column(config: dict[str, Any]) -> None:
    config["table_specs"]["feature_type"]["label_column"] = ""


def _unknown_details_column(config: dict[str, Any]) -> None:
    config["table_specs"]["feature_type"]["details_columns"] = ["missing_column"]


def _missing_threshold(config: dict[str, Any]) -> None:
    del config["options"]["reconciliation"]["label_threshold"]


def _zero_threshold(config: dict[str, Any]) -> None:
    config["options"]["reconciliation"]["description_threshold"] = 0


def _above_one_threshold(config: dict[str, Any]) -> None:
    config["options"]["reconciliation"]["label_threshold"] = 1.5


def _non_numeric_threshold(config: dict[str, Any]) -> None:
    config["options"]["reconciliation"]["description_threshold"] = "high"


def test_validate_classifier_configuration_accepts_valid_config(provider_with_config: Config) -> None:
    provider_with_config.update(_classifier_config())

    validate_classifier_configuration()


@pytest.mark.parametrize(
    "mutation, expected_message",
    [
        (_drop_classifier_key, "feature_type"),
        (_drop_last_classifier_key, CLASSIFIER_KEYS[-1]),
        (_drop_marker, "reconciliation: simple"),
        (_add_unregistered_marked_key, "not declared in CLASSIFIER_KEYS"),
        (_blank_label_column, "label_column"),
        (_unknown_details_column, "details column"),
        (_missing_threshold, "label_threshold"),
        (_zero_threshold, "description_threshold"),
        (_above_one_threshold, "label_threshold"),
        (_non_numeric_threshold, "description_threshold"),
    ],
)
def test_validate_classifier_configuration_rejects_invalid_config(provider_with_config: Config, mutation, expected_message: str) -> None:
    config_data: dict[str, Any] = _classifier_config()
    mutation(config_data)
    provider_with_config.update(config_data)

    with pytest.raises(ClassifierConfigurationError, match=expected_message):
        validate_classifier_configuration()


@pytest.mark.asyncio
async def test_startup_validates_classifier_configuration(monkeypatch: pytest.MonkeyPatch, provider_with_config: Config) -> None:
    provider_with_config.update(_classifier_config())

    async def fake_setup_config_store() -> None:
        return None

    monkeypatch.setattr(main, "setup_config_store", fake_setup_config_store)

    await main.startup()


@pytest.mark.asyncio
async def test_startup_fails_on_invalid_classifier_configuration(monkeypatch: pytest.MonkeyPatch, provider_with_config: Config) -> None:
    provider_with_config.update({"table_specs": {}, "options": {}})

    async def fake_setup_config_store() -> None:
        return None

    monkeypatch.setattr(main, "setup_config_store", fake_setup_config_store)

    with pytest.raises(ClassifierConfigurationError):
        await main.startup()
