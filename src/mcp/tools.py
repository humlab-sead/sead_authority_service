"""
MCP Tools - Core retrieval operations

Implements the essential MCP tools for hybrid search and lookup.
"""

import time
from typing import Any

from loguru import logger
from psycopg import AsyncConnection, sql

from src.configuration.resolve import ConfigValue

from .models import Candidate, GetByIdParams, GetByIdResult, RawScores, SearchLookupParams, SearchLookupResult


class MCPTools:
    """Implements MCP tool operations over SEAD authority database"""

    def __init__(self, connection: AsyncConnection):
        self.connection = connection
        self.schema = ConfigValue("table_specs", default={}).resolve()

    async def search_lookup(self, params: SearchLookupParams) -> SearchLookupResult:
        """
        Hybrid retrieval: trigram + semantic → blended candidates

        This is the core MCP tool for reconciliation.
        """
        if params.entity_type not in self.schema:
            raise ValueError(f"Unsupported entity type: {params.entity_type}")

        start_time = time.time()

        try:
            # TODO Phase 3: Call authority.search_*_hybrid() function
            # For now, fall back to existing fuzzy search
            candidates = await self._fallback_fuzzy_search(params)

            elapsed_ms = (time.time() - start_time) * 1000

            return SearchLookupResult(
                entity_type=params.entity_type,
                query=params.query,
                candidates=candidates,
                limits={
                    "k_fuzzy": params.k_fuzzy,
                    "k_sem": params.k_sem,
                    "k_final": params.k_final,
                },
                elapsed_ms=elapsed_ms,
            )

        except Exception as e:
            logger.error(f"search_lookup failed for table={params.entity_type}, query={params.query}: {e}")
            raise

    async def _fallback_fuzzy_search(self, params: SearchLookupParams) -> list[Candidate]:
        """
        Temporary fallback using existing fuzzy functions

        TODO: Replace with authority.search_*_hybrid() when Phase 3 is complete
        """

        # Use existing fuzzy function if available
        fuzzy_function_name = f"fuzzy_{params.entity_type}"

        query = sql.SQL("SELECT * FROM authority.{func}(%(q)s, %(n)s)").format(func=sql.Identifier(fuzzy_function_name))

        async with self.connection.cursor() as cursor:
            await cursor.execute(
                query,
                {
                    "q": params.query,
                    "n": params.k_final,
                },
            )
            rows = await cursor.fetchall()

            candidates = []
            for row in rows:
                # Assuming columns: id, label, name_sim
                # Adapt to your actual schema
                candidates.append(
                    Candidate(
                        id=str(row[0]),
                        value=row[1],
                        language=None,
                        active=True,
                        raw_scores=(
                            RawScores(
                                trgm=float(row[2]) if len(row) > 2 else 0.0,
                                sem=0.0,  # Not available yet
                                blend=float(row[2]) if len(row) > 2 else 0.0,
                            )
                            if params.return_raw_scores
                            else None
                        ),
                    )
                )

            return candidates

    async def get_by_id(self, params: GetByIdParams) -> GetByIdResult:
        """
        Fetch a single lookup entry by canonical ID

        Useful for preview/audit in OpenRefine
        """
        if params.entity_type not in self.schema:
            raise ValueError(f"Unsupported entity type: {params.entity_type}")

        table_spec = self.schema[params.entity_type]
        table_name = table_spec.get("table_name")
        id_column = table_spec.get("id_column")
        label_column = table_spec.get("label_column")

        query = sql.SQL(
            """
            SELECT {id_col} as id, {label_col} as value
            FROM public.{table}
            WHERE {id_col} = %(id)s
        """
        ).format(
            id_col=sql.Identifier(id_column),
            label_col=sql.Identifier(label_column),
            table=sql.Identifier(table_name),
        )

        async with self.connection.cursor() as cursor:
            await cursor.execute(query, {"id": params.id})
            row = await cursor.fetchone()

            if not row:
                raise ValueError(f"ID {params.id} not found in table {params.entity_type}")

            return GetByIdResult(
                id=str(row[0]),
                value=row[1],
                aliases=None,  # TODO: Add when aliases are available
                language=None,
                active=True,
                provenance=None,  # TODO: Add metadata if needed
                schema_version="0.1",
            )

    async def rerank(self, query: str, candidates: list[dict[str, Any]], k: int = 5) -> list[Candidate]:
        """Optional cross-encoder reranking"""
        raise NotImplementedError("Reranking not yet implemented - skip for Phase 1")
