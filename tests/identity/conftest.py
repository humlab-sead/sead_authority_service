"""Identity test fixtures.

Session-level setup for integration tests (``SIMS_INTEGRATION_DB=1``).
Unit tests (no live DB) are unaffected — the fixture is a no-op when the
flag is not set.
"""

from __future__ import annotations

import os

import pytest

from src.configuration import get_config_provider
from src.configuration.setup import setup_config_store

_RUN_INTEGRATION = os.environ.get("SIMS_INTEGRATION_DB", "0") == "1"

_DISPOSABLE_DB = ("127.0.0.1", "55432", "sead_staging")


@pytest.fixture(scope="session", autouse=True)
async def setup_identity_config():
    """Point the session at the helper-owned disposable database for integration tests.

    When ``SIMS_INTEGRATION_DB`` is not set the fixture is a quick no-op so
    unit tests continue to work without a database.

    Integration tests run only against the helper-owned loopback database, so
    the suite never connects to an intended deployment. Environment variables
    expected:
      SEAD_AUTHORITY_OPTIONS_DATABASE_HOST     → 127.0.0.1
      SEAD_AUTHORITY_OPTIONS_DATABASE_PORT     → 55432
      SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME   → sead_staging
      SEAD_AUTHORITY_OPTIONS_DATABASE_USER     → postgres
      SEAD_AUTHORITY_OPTIONS_DATABASE_PASSWORD → DB password
    """
    if not _RUN_INTEGRATION:
        return

    database_host = os.environ.get("SEAD_AUTHORITY_OPTIONS_DATABASE_HOST")
    database_port = os.environ.get("SEAD_AUTHORITY_OPTIONS_DATABASE_PORT")
    database_name = os.environ.get("SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME")
    if (database_host, database_port, database_name) != _DISPOSABLE_DB:
        pytest.skip(
            "Integration tests require the helper-owned 127.0.0.1:55432/sead_staging database"
        )

    await setup_config_store(
        filename="config/config.yml",
        force=True,
        env_filename="",
        env_prefix="SEAD_AUTHORITY",
    )
    yield

    pool = get_config_provider().get_config().get("runtime:connection_pool")
    if pool is not None:
        await pool.close()
