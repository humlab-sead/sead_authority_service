"""
RAG Hybrid Reconciliation Strategy

Uses the embedded MCP server for small-prompt reconciliation:
1. MCP search_lookup → 5-10 candidates
2. LLM formats/validates with strict JSON
3. Returns scored matches to OpenRefine

This strategy follows the RAG architecture from the implementation checklist.
"""

from typing import Any

from loguru import logger

from src.configuration import ConfigValue, get_connection
from src.mcp import SEADMCPServer, SearchLookupParams
from src.strategies.query import BaseRepository
from src.strategies.strategy import ReconciliationStrategy, StrategySpecification


class RAGHybridReconciliationStrategy(ReconciliationStrategy):
    """
    Reconciliation strategy using MCP-based RAG pipeline

    Phase 1: Uses existing fuzzy search via MCP (hybrid search not yet implemented)
    Phase 3: Will use full hybrid retrieval (trigram + semantic)
    Phase 4: Optional cross-encoder reranking
    """

    def __init__(self, specification: StrategySpecification, repository_or_cls: type[BaseRepository] | BaseRepository) -> None:
        super().__init__(specification, repository_or_cls)

        # Feature flag to enable MCP
        self.use_mcp = ConfigValue("features.use_mcp_server", default=False).resolve()

        if self.use_mcp:
            logger.info(f"Initialized {self.__class__.__name__} with MCP server")
        else:
            logger.info(f"Initialized {self.__class__.__name__} without MCP (fallback mode)")

    async def find_candidates(
        self,
        query: str,
        properties: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Find candidates using MCP-based retrieval

        Flow:
        1. Call MCP search_lookup (gets small candidate set)
        2. (Optional) Call MCP rerank
        3. (Future) Send to LLM for formatting/validation
        4. Return scored matches

        For Phase 1, this delegates to MCP which uses existing fuzzy functions.
        """

        if not self.use_mcp:
            # Fallback to parent class (current strategy)
            logger.debug(f"MCP disabled, using fallback strategy for '{query}'")
            return await super().find_candidates(query, properties, limit)

        try:
            # Get MCP server instance
            async with await get_connection() as conn:
                mcp_server = SEADMCPServer(conn)

                k_fuzzy: int = ConfigValue("mcp.retrieval.k_fuzzy").resolve() or 30
                k_sem: int = ConfigValue("mcp.retrieval.k_sem").resolve() or 30
                # Prepare MCP search parameters
                search_params = SearchLookupParams(
                    entity_type=self.key,  # e.g., 'methods', 'modification_type'
                    query=query,
                    k_fuzzy=k_fuzzy,
                    k_sem=k_sem,
                    k_final=min(limit * 2, 20),  # Get a bit more than needed
                    return_raw_scores=True,
                    language=None,
                )

                # Call MCP search_lookup
                result = await mcp_server.search_lookup(search_params)

                # Convert MCP candidates to reconciliation format
                candidates = []
                for candidate in result["candidates"]:
                    candidates.append(
                        {
                            self.get_entity_id_field(): candidate["id"],
                            self.get_label_field(): candidate["value"],
                            "name_sim": candidate.get("raw_scores", {}).get("blend", 0.0) if candidate.get("raw_scores") else 0.0,
                            "language": candidate.get("language"),
                        }
                    )

                # Apply threshold
                min_threshold = ConfigValue("mcp.retrieval.min_score_threshold", default=0.6).resolve()
                candidates = [c for c in candidates if c["name_sim"] >= min_threshold]

                # Sort and limit
                candidates = sorted(candidates, key=lambda x: x["name_sim"], reverse=True)[:limit]

                logger.info(f"MCP search returned {len(candidates)} candidates for '{query}' (threshold={min_threshold})")

                return candidates

        except Exception as e:  # pylint: disable=broad-except
            logger.error(f"MCP search failed for '{query}': {e}")
            logger.info("Falling back to traditional strategy")
            return await super().find_candidates(query, properties, limit)


# Example: How to register this strategy
# In your strategy module initialization:
#
# from src.strategies.strategy import Strategies
# from .rag_hybrid import RAGHybridReconciliationStrategy
#
# @Strategies.register(key="methods")
# class MethodsReconciliationStrategy(RAGHybridReconciliationStrategy):
#     def __init__(self):
#         super().__init__(METHODS_SPECIFICATION, MethodsRepository)
