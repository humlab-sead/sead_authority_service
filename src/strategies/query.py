from typing import Any, Tuple

import psycopg
from loguru import logger


class QueryProxy:
    def __init__(self, specification: dict[str, str], cursor: psycopg.AsyncCursor) -> None:
        self.cursor: psycopg.AsyncCursor[tuple[Any]] = cursor
        self.specification: dict[str, str] = specification

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific location."""
        try:
            sql: str = self.specification["sql_queries"]["get_details"]
            # logger.debug(f"Executing SQL for get_details: {sql}")
            await self.cursor.execute(sql, {"id": int(entity_id)})
            row: tuple[Any] | None = await self.cursor.fetchone()
            return dict(row) if row else None
        except (ValueError, psycopg.Error) as e:
            logger.error(f"Error fetching details for entity_id {entity_id}: {e}")
            return None

    async def fetch_by_fuzzy_name_search(self, name: str, limit: int = 10) -> list[dict[str, Any]]:
        """Perform fuzzy name search"""
        sql: str = self.specification["sql_queries"]["fetch_by_fuzzy_name_search"]
        await self.cursor.execute(sql, {"q": name, "n": limit})
        rows: list[Tuple[Any]] = await self.cursor.fetchall()
        return [dict(row) for row in rows]
