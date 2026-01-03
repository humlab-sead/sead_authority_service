import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

import dotenv
import psycopg
from loguru import logger
from psycopg_pool import AsyncConnectionPool

from src.utility import configure_logging, create_db_uri

from .interface import ConfigLike
from .provider import ConfigStore, get_config_provider

dotenv.load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env"))


async def setup_config_store(
    filename: str | None = None,
    force: bool = False,
    env_prefix="SEAD_AUTHORITY",
    env_filename=".env",
    db_opts_path: str | None = "options:database",
) -> None:

    config_file: str | None = filename or os.getenv("CONFIG_FILE", "config.yml")

    store: ConfigStore = ConfigStore.get_instance()

    if store.is_configured() and not force:
        return

    store.configure_context(source=config_file, env_filename=env_filename, env_prefix=env_prefix)
    assert store.is_configured(), "Config Store failed to configure properly"

    cfg: ConfigLike | None = store.config()
    if not cfg:
        raise ValueError("Config Store did not return a config")

    cfg.update({"runtime:config_file": config_file, "runtime:env_file": env_filename})

    # FIXME: This should be done elsewhere  #  pylint: disable=fixme
    configure_logging(cfg.get("logging") or {})

    if db_opts_path:
        if not cfg.get(db_opts_path):
            logger.warning(f"Database options not found in default config at path '{db_opts_path}'")
        else:
            await _setup_connection_pool(cfg, db_opts_path=db_opts_path)

    logger.info("Config Store initialized successfully.")


async def _setup_connection_pool(cfg: ConfigLike, db_opts_path: str) -> None:
    """Create and configure async connection pool"""
    db_config = cfg.get(db_opts_path)

    # Extract pool-specific settings
    pool_min_size: int = db_config.get("pool_min_size", 2)
    pool_max_size: int = db_config.get("pool_max_size", 10)
    pool_timeout: float = db_config.get("pool_timeout", 30.0)

    # Filter out pool settings from connection parameters
    conn_params = {k: v for k, v in db_config.items() if k not in ("pool_min_size", "pool_max_size", "pool_timeout")}

    dsn: str = create_db_uri(**conn_params)

    if not dsn:
        raise ValueError("Database DSN is not configured properly")

    logger.info(f"Creating connection pool (min={pool_min_size}, max={pool_max_size}, timeout={pool_timeout}s)")

    pool = AsyncConnectionPool(
        conninfo=dsn,
        min_size=pool_min_size,
        max_size=pool_max_size,
        timeout=pool_timeout,
        open=False,  # Don't open in constructor (deprecated)
    )

    # Explicitly open the pool
    await pool.open()
    await pool.wait()

    cfg.update(
        {
            "runtime:connection_pool": pool,
            "runtime:dsn": dsn,
        }
    )

    logger.info("Database connection pool initialized successfully")


@asynccontextmanager
async def get_connection() -> AsyncIterator[psycopg.AsyncConnection]:
    """Get a database connection from the pool with automatic transaction management

    Usage:
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT ...")
                result = await cur.fetchall()
            # Transaction auto-commits on success, rolls back on exception
    """
    cfg: ConfigLike = get_config_provider().get_config()
    if not cfg:
        raise ValueError("Config Store is not configured")

    pool: AsyncConnectionPool | None = cfg.get("runtime:connection_pool")
    if not pool:
        raise ValueError("Connection pool not initialized")

    async with pool.connection() as conn:
        try:
            yield conn
            # Auto-commit on success
            await conn.commit()
        except Exception as e:
            # Auto-rollback on error
            await conn.rollback()
            logger.exception(f"Database transaction error, rolled back: {e}")
            raise


async def shutdown_connection_pool() -> None:
    """Close the connection pool gracefully"""
    cfg: ConfigLike = get_config_provider().get_config()
    pool: AsyncConnectionPool | None = cfg.get("runtime:connection_pool")

    if pool:
        logger.info("Closing database connection pool...")
        await pool.close()
        logger.info("Database connection pool closed")
    if not cfg.get("runtime:connection"):
        _connection_factory = cfg.get("runtime:connection_factory")
        if not _connection_factory:
            raise ValueError("Connection factory is not configured")
        connection = await _connection_factory()
        cfg.update({"runtime:connection": connection})
    return cfg.get("runtime:connection")
