"""Tests for configuration setup helpers."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

import main
from src.configuration import setup
from src.configuration.config import Config
from src.configuration.provider import ConfigProvider, ConfigStore, MockConfigProvider, reset_config_provider, set_config_provider
from src.record_selection import RecordSelectionConfigurationError, validate_record_selection_configuration
from src.strategies.configured_classifier import ClassifierConfigurationError, validate_classifier_configuration

# pylint: disable=redefined-outer-name

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


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
    """Builds a classifier validation payload from the inline test table specifications.

    Every specification is kept, because scope columns resolve against parent
    entities that are not themselves marked for reconciliation.
    """
    specs: dict[str, Any] = yaml.safe_load((REPOSITORY_ROOT / "tests/config/config.yml").read_text(encoding="utf-8"))["table_specs"]
    table_specs: dict[str, Any] = {key: dict(table_spec) for key, table_spec in specs.items() if isinstance(table_spec, dict)}
    return {
        "table_specs": table_specs,
        "options": {"reconciliation": {"label_threshold": 0.30, "description_threshold": 0.50}},
    }


def _blank_id_column(config: dict[str, Any]) -> None:
    del config["table_specs"]["location_type"]["id_column"]


def _declare_properties(config: dict[str, Any]) -> None:
    config["table_specs"]["feature_type"]["properties"] = [{"id": "code", "name": "Code", "type": "string"}]


def _declare_property_settings(config: dict[str, Any]) -> None:
    config["table_specs"]["feature_type"]["property_settings"] = {"code": {"max": 10}}


def _weight_without_description_column(config: dict[str, Any]) -> None:
    config["table_specs"]["country"]["description_match_weight"] = 0.15


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


def _unknown_scope_column(config: dict[str, Any]) -> None:
    config["table_specs"]["colour"]["scope_columns"] = ["missing_parent_id"]


def _lookup_description_weight(config: dict[str, Any]) -> None:
    config["table_specs"]["feature"]["description_match_weight"] = 0.15


def _lookup_without_label(config: dict[str, Any]) -> None:
    config["table_specs"]["feature"]["label_column"] = ""


@pytest.mark.parametrize(
    "mutation, expected_message",
    [
        (_unknown_scope_column, "missing_parent_id"),
        (_lookup_description_weight, "must not score descriptions"),
        (_lookup_without_label, "label_column"),
    ],
)
def test_validate_classifier_configuration_rejects_invalid_scoped_config(
    provider_with_config: Config, mutation, expected_message: str
) -> None:
    config_data: dict[str, Any] = _classifier_config()
    mutation(config_data)
    provider_with_config.update(config_data)

    with pytest.raises(ClassifierConfigurationError, match=expected_message):
        validate_classifier_configuration()


def test_validate_classifier_configuration_accepts_valid_config(provider_with_config: Config) -> None:
    provider_with_config.update(_classifier_config())

    validate_classifier_configuration()


@pytest.mark.parametrize(
    "mutation, expected_message",
    [
        (_blank_label_column, "label_column"),
        (_blank_id_column, "id_column"),
        (_unknown_details_column, "details column"),
        (_declare_properties, "properties"),
        (_declare_property_settings, "property_settings"),
        (_weight_without_description_column, "description_column"),
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


def test_record_selection_rejects_an_enabled_key_that_is_not_a_simple_classifier(provider_with_config: Config) -> None:
    """An enabled record type that is no longer marked fails configuration, not a request."""
    config_data: dict[str, Any] = _classifier_config()
    del config_data["table_specs"]["feature_type"]
    provider_with_config.update(config_data)
    provider_with_config.update({"options:record_selection": {"types": {"feature_type": {"search_supported": True}}}})

    with pytest.raises(RecordSelectionConfigurationError, match="feature_type"):
        validate_record_selection_configuration()


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
