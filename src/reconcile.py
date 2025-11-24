from typing import Any, Type

from loguru import logger

from src.configuration import get_config_provider, get_connection
from src.strategies.strategy import ReconciliationStrategy, Strategies


async def reconcile_queries(queries: dict[str, Any]) -> dict[str, Any]:

    default_query_limit: int = get_config_provider().get_config().get("options:default_query_limit") or 10

    results: dict[str, Any] = {}
    _ = await get_connection()

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

        logger.info(f"Found {len(candidate_data)} candidates for query {query_id}")
        results[query_id] = {"result": [strategy.as_candidate(data, query.get("query", "")) for data in candidate_data]}

    logger.info(f"Reconciliation completed with {len(results)} results")
    return results
