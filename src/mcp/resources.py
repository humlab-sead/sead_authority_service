"""
MCP Resources - Read-only metadata about lookup tables

Resources provide browsable information about the SEAD authority schema.
"""

from typing import Any, Optional

from loguru import logger
from psycopg import AsyncConnection, sql

from src.configuration.resolve import ConfigValue

from .models import LookupTable, ServerInfo

# pylint: disable=too-many-positional-arguments


class MCPResources:
    """Handles MCP resource queries (metadata, browsing)"""

    def __init__(self, connection: AsyncConnection, version: str = "0.1.0"):
        self.connection = connection
        self.version = version
        self.schema = ConfigValue("table_specs", default={}).resolve()

    async def get_server_info(self) -> ServerInfo:
        """Return MCP server metadata"""
        emb_model = ConfigValue("mcp.embedding.model", default="sentence-transformers/all-mpnet-base-v2").resolve()
        emb_dim = ConfigValue("mcp.embedding.dimensions", default=768).resolve()
        return ServerInfo(
            server="sead.pg",
            version=self.version,
            emb_model=emb_model,
            pgvector_dim=emb_dim,
            features=[
                "search_lookup",
                "get_by_id",
                "lookup_tables",
                "lookup_rows",
                # "rerank",  # Add when implemented
            ],
        )

    async def list_lookup_tables(self) -> list[LookupTable]:
        """List all exposed lookup tables with metadata"""
        tables = []
        table_name: str = ""
        for table_key, table_spec in self.schema.items():
            try:
                table_name = table_spec["table_name"]
                # Query table metadata from information_schema
                query = sql.SQL(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = {table_name}
                    ORDER BY ordinal_position
                """
                ).format(table_name=sql.Identifier(table_name))

                async with self.connection.cursor() as cursor:
                    await cursor.execute(query, {"table": table_name})
                    rows = await cursor.fetchall()

                    columns = {row[0]: row[1] for row in rows}

                    # Build table metadata
                    tables.append(
                        LookupTable(
                            table=table_key,
                            domain=table_key,  # Could be enriched from config
                            languages=["en"],  # TODO: Detect from data
                            columns=columns,
                        )
                    )

            except Exception as e:  # pylint: disable=broad-except
                logger.error(f"Failed to get metadata for table {table_name}: {e}")

        return tables

    async def get_lookup_rows(  # pylint: disable=too-many-arguments, too-many-locals
        self,
        entity_type: str,
        offset: int = 0,
        limit: int = 50,
        language: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Browse paginated rows from a lookup table

        Returns:
            {"rows": [...], "next_offset": int}
        """
        if entity_type not in self.schema:
            raise ValueError(f"Entity type '{entity_type}' not in allowed list")

        if language:
            raise NotImplementedError("Language filtering not implemented yet")

        table_spec: dict[str, str] = self.schema[entity_type]
        table_name: str = table_spec["table_name"]
        id_column: str = table_spec["id_column"]
        label_column: str = table_spec["label_column"]

        query: sql.Composed = sql.SQL(
            """
            SELECT {id_column} as id, {label_column} as value
            FROM public.{table_name}
            WHERE 1 = 1
            ORDER BY id
            LIMIT %(limit)s OFFSET %(offset)s
        """
        ).format(
            id_column=sql.Identifier(id_column),
            label_column=sql.Identifier(label_column),
            table_name=sql.Identifier(table_name),
        )

        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"limit": limit, "offset": offset})
            rows = await cursor.fetchall()

            results = []
            for row in rows:
                results.append(
                    {
                        "id": str(row[0]),
                        "value": row[1],
                    }
                )

            return {"rows": results, "next_offset": offset + len(results)}
