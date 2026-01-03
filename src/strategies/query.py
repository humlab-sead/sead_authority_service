from abc import ABC, abstractmethod
from typing import Any, Literal, Mapping, Sequence, TypeAlias, Union, overload

import psycopg
from loguru import logger
from psycopg.rows import dict_row, tuple_row

from src.configuration.resolve import ConfigValue
from src.configuration.setup import get_connection
from src.utility import resolve_specification

from . import StrategySpecification

Params: TypeAlias = Union[Sequence[Any], Mapping[str, Any]]
DictRow: TypeAlias = dict[str, Any]
TupleRow: TypeAlias = tuple[Any, ...]


class AbstractRepository(ABC):
    """Abstract base class for entity-specific query proxies"""

    def __init__(self, specification: StrategySpecification | str, **kwargs) -> None:  # pylint: disable=unused-argument
        self.specification: StrategySpecification = resolve_specification(specification)
        self.config: dict[str, Any] = ConfigValue("table_specs." + self.specification["key"]).resolve() or {}

    @property
    def key(self) -> str:
        """Return the unique key for this query proxy"""
        return self.specification["key"]

    @abstractmethod
    async def find(self, name: str, limit: int = 10, **kwargs) -> list[dict[str, Any]]:
        """Perform (possibly) fuzzy name search"""

    @abstractmethod
    async def get_details(self, entity_id: str, **kwargs) -> dict[str, Any] | None:
        """Fetch details for a specific entity by ID"""

    @abstractmethod
    async def fetch_by_alternate_identity(self, alternate_identity: str, **kwargs) -> list[dict[str, Any]]:
        """Fetch entity by alternate identity"""

    def get_sql_queries(self) -> dict[str, str]:
        """Return the SQL queries defined in the specification"""
        return self.specification.get("sql_queries", {})

    def get_sql_query(self, key: str) -> str:
        """Return the SQL query defined in the specification for a given key."""
        return self.get_sql_queries().get(key, "")

    def get_find_fuzzy_sql(self) -> str:
        """Return the SQL query for fuzzy finding entities"""
        sql: str = self.get_sql_queries().get("fuzzy_find_sql", "")
        if not sql:
            sql = "select * from authority.fuzzy_site(%(q)s, %(n)s);"
        return sql


class BaseRepository(AbstractRepository):

    def __init__(self, specification: StrategySpecification | str, **kwargs) -> None:
        super().__init__(specification, **kwargs)
        self.connection: psycopg.AsyncConnection | None = kwargs.get("connection")
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

    @overload
    async def fetch_all(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict"] = "dict") -> list[DictRow]: ...

    @overload
    async def fetch_all(self, sql: str, params: Params | None = None, *, row_factory: Literal["tuple"]) -> list[TupleRow]: ...

    async def fetch_all(
        self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict"
    ) -> list[DictRow] | list[TupleRow]:
        async with get_connection() as connection:
            async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
                await cursor.execute(sql.strip(), params)  # type: ignore
                rows: list[Any] = await cursor.fetchall()
                if row_factory == "tuple":
                    return list(rows)
                return [d if isinstance(d, dict) else dict(d) for d in rows]

    @overload
    async def fetch_one(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict"] = "dict") -> DictRow | None: ...

    @overload
    async def fetch_one(self, sql: str, params: Params | None = None, *, row_factory: Literal["tuple"]) -> TupleRow | None: ...

    async def fetch_one(
        self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict"
    ) -> DictRow | TupleRow | None:
        async with get_connection() as connection:
            async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
                await cursor.execute(sql.strip(), params)  # type: ignore
                row: Any = await cursor.fetchone()
                if not row:
                    return None
                if row_factory == "tuple":
                    return row
                return row if isinstance(row, dict) else dict(row)

    def get_details_sql(self) -> str:
        """Return the SQL query for fetching detailed information for a given entity ID."""
        return self.get_sql_query("details_sql")

    async def get_details(self, entity_id: str, **kwargs) -> dict[str, Any] | None:  # pylint: disable=unused-argument
        """Fetch details for a specific location."""
        try:
            return await self.fetch_one(self.get_details_sql(), {"id": int(entity_id)})
        except (ValueError, psycopg.Error) as e:
            logger.error(f"Error fetching details for entity_id {entity_id}: {e}")
            return None

    async def find(self, name: str, limit: int = 10, **kwargs) -> list[dict[str, Any]]:  # pylint: disable=unused-argument
        """Perform fuzzy name search"""
        return await self.fetch_all(self.get_find_fuzzy_sql(), {"q": name, "n": limit})

    async def fetch_by_alternate_identity(
        self, alternate_identity: str, **kwargs
    ) -> list[dict[str, Any]]:  # pylint: disable=unused-argument
        """Fetch entity by alternate identity"""
        sql: str = self.get_sql_query("alternate_identity_sql")
        if not sql:
            return []
        return await self.fetch_all(sql, {"alternate_identity": alternate_identity})
