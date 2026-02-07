from typing import Any, Type

from loguru import logger

from src.configuration import get_config_provider
from src.strategies.strategy import ReconciliationStrategy, Strategies


async def reconcile_queries(queries: dict[str, Any]) -> dict[str, Any]:

    default_query_limit: int = get_config_provider().get_config().get("options:default_query_limit") or 10

    results: dict[str, Any] = {}

    logger.info(f"Processing {len(queries)} reconciliation queries")

    for query_id, query in queries.items():
        logger.info(f"Processing query {query_id}: {query}")

        if not (query.get("query") or "").strip():
            logger.info(f"Empty query for {query_id}, returning empty results")
            results[query_id] = {"result": []}
            continue

        if not query.get("type"):
            logger.error(f"Missing 'type' in query {query_id}")
            raise ValueError("Missing 'type' in query")

        entity_type: str = query.get("type")
        logger.info(f"Query {query_id} entity type: {entity_type}")

        if not Strategies.items.get(entity_type):
            logger.error(f"Unknown query type '{entity_type}' in query {query_id}. Available types: {list(Strategies.items.keys())}")
            raise ValueError(f"Unknown query type '{entity_type}' in query")

        strategy_cls: Type[ReconciliationStrategy] | None = Strategies.items.get(entity_type)
        if not strategy_cls:
            raise ValueError(f"Unknown entity type: {entity_type}")
        strategy: ReconciliationStrategy = strategy_cls()
        logger.info(f"Created strategy for {entity_type}: {type(strategy).__name__}")

        candidate_data: list[dict[str, Any]] = await strategy.find_candidates(
            query=query.get("query"),
            properties={p["pid"]: p["v"] for p in query.get("properties", []) if "pid" in p and "v" in p},
            limit=default_query_limit,
        )

        candidates = [strategy.as_candidate(data, query.get("query", "")) for data in candidate_data]

        # Log summary with match counts and score ranges
        if candidates:
            match_count = sum(1 for c in candidates if c.get("match"))
            scores = [c["score"] for c in candidates]
            logger.info(
                f"Found {len(candidates)} candidates for query {query_id}: "
                f"{match_count} auto-matches, scores: {min(scores):.1f}%-{max(scores):.1f}%"
            )
        else:
            logger.info(f"Found 0 candidates for query {query_id}")

        results[query_id] = {"result": candidates}

    logger.info(f"Reconciliation completed with {len(results)} results")
    return results
