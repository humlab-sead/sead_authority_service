import os

import dotenv
import psycopg
from loguru import logger

from src.configuration.config import Config
from src.configuration.inject import ConfigStore
from src.utility import configure_logging, create_db_uri

dotenv.load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env"))


async def setup_config_store(filename: str = "config.yml") -> None:

    config_file: str = os.getenv("CONFIG_FILE", filename)

    if ConfigStore.is_configured():
        return

    ConfigStore.get_instance().configure_context(source=config_file, env_filename=".env", env_prefix="SEAD_AUTHORITY")

    assert store.is_configured(), "Config Store failed to configure properly"

    cfg: Config = store.config()
    if not cfg:
        raise ValueError("Config Store did not return a config")

    cfg.update({"runtime:config_file": config_file})

    configure_logging(cfg.get("logging") or {})

    await _setup_connection_factory(cfg)

    logger.info("Config Store initialized successfully.")


async def _setup_connection_factory(cfg):
    dsn: str = create_db_uri(**cfg.get("options:database"))

    if not dsn:
        raise ValueError("Database DSN is not configured properly")

    def connection_factory() -> psycopg.AsyncConnection:
        if cfg.get("runtime:connection") is None:
            con = cfg.get("runtime:connection")
        else:
            con = psycopg.AsyncConnection.connect(dsn)
            cfg.update({"runtime:connection": con})
        return con

    cfg.update(
        {
            "runtime:connection": None,
            "runtime:dsn": dsn,
            "runtime:connection_factory": connection_factory,
        }
    )


def get_connection() -> psycopg.AsyncConnection:
    """Get a database connection from the config"""
    cfg: Config = ConfigStore.get_instance().config()
    if not cfg:
        raise ValueError("ConfigStore is not configured")
    if not cfg.get("runtime:connection"):
        connection_factory = cfg.get("runtime:connection_factory")
        if not connection_factory:
            raise ValueError("Connection factory is not configured")
        cfg.update({"runtime:connection": connection_factory()})
    return cfg.get("runtime:connection")
