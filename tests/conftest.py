from unittest.mock import AsyncMock

import psycopg
import pytest

from src.configuration.inject import Config, ConfigStore

ConfigStore.configure_context(source="./tests/config.yml", env_filename=None)
ConfigStore.config().update({"runtime:connection": AsyncMock(spec=psycopg.AsyncConnection)})


@pytest.fixture(scope="session")
def cfg() -> Config:
    ConfigStore.configure_context(source="./tests/config.yml", env_filename=None)
    return ConfigStore.config()
