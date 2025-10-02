from typing import Any
import psycopg


class QueryProxy:
    def __init__(self, specification: dict[str, str], cursor: psycopg.AsyncCursor) -> None:
        self.cursor: psycopg.AsyncCursor[tuple[Any]] = cursor
        self.specification: dict[str, str] = specification

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        """Fetch details for a specific location."""
        try:
            sql: str = self.specification["get_details"]
            await self.cursor.execute(sql, {"id": int(entity_id)})
            row: tuple[Any] | None = await self.cursor.fetchone()
            return dict(row) if row else None
        except (ValueError, psycopg.Error):
            return None
