from abc import ABC, abstractmethod
import asyncio
from typing import Any, Literal, Mapping, Sequence, Tuple, TypeAlias, Union

import psycopg
from loguru import logger
from psycopg.rows import dict_row, tuple_row

from src.configuration.setup import get_connection

from . import StrategySpecification

Params: TypeAlias = Union[Sequence[Any], Mapping[str, Any]]

class QueryProxy(ABC):
    """Abstract base class for entity-specific query proxies"""

    def __init__(self, specification: StrategySpecification, **kwargs) -> None:
        self.specification: StrategySpecification = specification or {
            "key": "unknown",
            "id_field": "id",
            "label_field": "name",
            "properties": [],
            "property_settings": {},
            "sql_queries": {},
        }

    @property
    def key(self) -> str:
        """Return the unique key for this query proxy"""
        return self.specification["key"]

    @abstractmethod
    async def fetch_by_fuzzy_label(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Perform fuzzy name search"""

    @abstractmethod
    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific entity by ID"""

    @abstractmethod
    async def fetch_by_alternate_identity(self, alternate_identity: str) -> list[dict[str, Any]]:
        """Fetch entity by alternate identity"""

class DatabaseQueryProxy(QueryProxy):
    def __init__(self, specification: StrategySpecification, **kwargs) -> None:
        self.connection: psycopg.AsyncConnection | None = kwargs.get("connection")
        self.specification: StrategySpecification = specification
        self.row_factories: dict[str, Any] = {
            "dict": dict_row,
            "tuple": tuple_row,
        }

    # async def __aenter__(self) -> Self:
    #     if not self.connection:
    #         self.connection = await get_connection()
    #     return self

    # async def __aexit__(self, exc_type, exc_value, traceback) -> None:
    #     if self.connection:
    #         await self.connection.close()
    #         self.connection = None

    async def get_connection(self) -> psycopg.AsyncConnection:
        if not self.connection:
            self.connection = await get_connection()
        return self.connection

    async def fetch_all(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> list[dict[str, Any]]:
        connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
        async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
            await cursor.execute(sql, params)
            rows: list[dict[str, Any]] = await cursor.fetchall()
            return [d if isinstance(d, dict) else dict(d) for d in rows]

    async def fetch_one(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> dict[str, Any]:
        connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
        async with connection.cursor(row_factory=row_factory) as cursor:
            await cursor.execute(sql, params)
            row: dict[str, Any] | None = await cursor.fetchone()
            return dict(row) if row else None

    def get_sql_queries(self) -> dict[str, str]:
        """Return the SQL queries defined in the specification"""
        return self.specification.get("sql_queries", {})

    def get_sql_query(self, key: str) -> str:
        """Return the SQL query defined in the specification for a given key."""
        return self.get_sql_queries().get(key, "")

    def get_details_sql(self) -> str:
        """Return the SQL query for fetching detailed information for a given entity ID."""
        return self.get_sql_query("get_details")

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific location."""
        try:
            return await self.fetch_one(self.get_details_sql(), {"id": int(entity_id)})
        except (ValueError, psycopg.Error) as e:
            logger.error(f"Error fetching details for entity_id {entity_id}: {e}")
            return None

    async def fetch_by_fuzzy_label(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Perform fuzzy name search"""
        return await self.fetch_all(self.get_sql_query("fuzzy_label_sql"), {"q": name, "n": limit})

    async def fetch_by_alternate_identity(self, alternate_identity: str) -> list[dict[str, Any]]:
        """Fetch entity by alternate identity"""
        sql: str = self.get_sql_query("alternate_identity_sql")
        if not sql:
            return []
        return self.fetch_all(sql, {"alternate_identity": alternate_identity})
