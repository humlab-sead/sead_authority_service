"""Identity test fixtures.

Session-level setup for integration tests (``SIMS_INTEGRATION_DB=1``).
Unit tests (no live DB) are unaffected — the fixture is a no-op when the
flag is not set.
"""

from __future__ import annotations

import os

import pytest

from src.configuration.setup import setup_config_store

_RUN_INTEGRATION = os.environ.get("SIMS_INTEGRATION_DB", "0") == "1"


@pytest.fixture(scope="session", autouse=True)
async def setup_identity_config():
    """Initialize ConfigStore with a real DB connection for integration tests.

    When ``SIMS_INTEGRATION_DB`` is not set the fixture is a quick no-op so
    unit tests continue to work without a database.

    Environment variables expected (via ``ENV_FILE=tests/.env``):
      CONFIG_FILE                              → tests/config/config.yml
      SEAD_AUTHORITY_OPTIONS_DATABASE_HOST     → live DB host
      SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME   → live DB name
      SEAD_AUTHORITY_OPTIONS_DATABASE_USER     → DB user
      SEAD_AUTHORITY_OPTIONS_DATABASE_PORT     → DB port
    """
    if not _RUN_INTEGRATION:
        return

    config_file = os.environ.get("CONFIG_FILE", "./tests/config/config.yml")
    await setup_config_store(filename=config_file, force=True)
