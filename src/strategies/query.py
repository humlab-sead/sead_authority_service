from typing import Any, Tuple

import psycopg
from loguru import logger


class QueryProxy:
    def __init__(self, specification: dict[str, str], cursor: psycopg.AsyncCursor) -> None:
        self.cursor: psycopg.AsyncCursor[tuple[Any]] = cursor
        self.specification: dict[str, str] = specification

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
            sql: str = self.get_details_sql()
            # logger.debug(f"Executing SQL for get_details: {sql}")
            await self.cursor.execute(sql, {"id": int(entity_id)})
            row: tuple[Any] | None = await self.cursor.fetchone()
            return dict(row) if row else None
        except (ValueError, psycopg.Error) as e:
            logger.error(f"Error fetching details for entity_id {entity_id}: {e}")
            return None

    async def fetch_by_fuzzy_label(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Perform fuzzy name search"""
        sql: str = self.get_sql_query("fuzzy_label_sql")
        await self.cursor.execute(sql, {"q": name, "n": limit})
        rows: list[Tuple[Any]] = await self.cursor.fetchall()
        return [dict(row) for row in rows]
