"""
SEAD MCP Server - Main facade

Coordinates resources and tools; provides unified interface for FastAPI.
"""

from typing import Any, Optional, Tuple

from loguru import logger
from psycopg import AsyncConnection

from src.utility import normalize_text

from .models import GetByIdParams, GetByIdResult, LookupTable, SearchLookupParams, SearchLookupResult, ServerInfo
from .resources import MCPResources
from .tools import MCPTools

# pylint: disable=too-many-positional-arguments
# pylint: disable=fixme


class SEADMCPServer:
    """
    Embedded MCP server for SEAD reconciliation

    This provides a clean MCP-compliant interface over the SEAD authority
    database without requiring a separate service. It can be used directly
    by reconciliation strategies.

    Usage:
        async with await psycopg.AsyncConnection.connect(dsn) as conn:
            server = SEADMCPServer(conn)
            result = await server.search_lookup(
                SearchLookupParams(
                    table="methods",
                    query="radiocarbon dating",
                    k_final=10
                )
            )
    """

    def __init__(self, connection: AsyncConnection, version: str = "0.1.0") -> None:
        """
        Initialize MCP server with database connection

        Args:
            connection: Active async PostgreSQL connection
            version: Server version (semver)
        """
        self.connection: AsyncConnection[Tuple[Any, ...]] = connection
        self.version: str = version
        self.resources = MCPResources(connection, version)
        self.tools = MCPTools(connection)

        logger.info(f"SEAD MCP Server initialized (v{version})")

    async def get_server_info(self) -> ServerInfo:
        """Get server metadata"""
        return await self.resources.get_server_info()

    async def list_lookup_tables(self) -> list[dict[str, Any]]:
        """List all available lookup tables with metadata"""
        tables: list[LookupTable] = await self.resources.list_lookup_tables()
        return [table.model_dump() for table in tables]

    async def get_lookup_rows(
        self,
        table: str,
        offset: int = 0,
        limit: int = 50,
        language: Optional[str] = None,
    ) -> dict[str, Any]:
        """Browse paginated rows from a lookup table"""
        return await self.resources.get_lookup_rows(table, offset, limit, language)

    async def search_lookup(self, params: SearchLookupParams) -> dict[str, Any]:
        """
        Hybrid retrieval tool (core reconciliation operation)

        This is the primary MCP tool for reconciliation. It combines:
        - Trigram/fuzzy search (k_fuzzy top results)
        - Semantic search via pgvector (k_sem top results)
        - Blended scoring and deduplication
        - Final top-k selection (k_final)

        Args:
            params: Search parameters (table, query, k values, filters)

        Returns:
            SearchLookupResult with candidates and metadata
        """
        logger.debug(f"search_lookup: table={params.entity_type}, query='{params.query}', k_final={params.k_final}")

        result: SearchLookupResult = await self.tools.search_lookup(params)
        return result.model_dump()

    async def get_by_id(self, params: GetByIdParams) -> dict[str, Any]:
        """
        Fetch a single entry by canonical ID

        Useful for OpenRefine preview/extend operations
        """
        result: GetByIdResult = await self.tools.get_by_id(params)
        return result.model_dump()

    async def rerank(self, query: str, candidates: list[dict[str, Any]], k: int = 5) -> dict[str, Any]:
        """
        Optional cross-encoder reranking

        Not implemented in Phase 1 - returns NotImplementedError
        """
        # TODO Phase 4: Implement when reranker is deployed
        raise NotImplementedError("Reranking not yet implemented")

    async def normalize(self, text: str, ops: Optional[list[str]] = None) -> str:  # pylint: disable=unused-argument

        return normalize_text(text)
