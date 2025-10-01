from typing import Any

from psycopg.rows import dict_row

from src.configuration.config import Config
from src.configuration.inject import ConfigStore, ConfigValue
from src.strategies.interface import ReconciliationStrategy, Strategies


async def reconcile_queries(queries: dict[str, Any]) -> dict[str, Any]:

    config: Config = ConfigStore.config("default")
    connection = config.get("runtime:connection")
    default_query_limit: int = config.get("options:default_query_limit") or 10

    results: dict[str, Any] = {}
    async with connection.cursor(row_factory=dict_row) as cursor:
        for query_id, query in queries.items():

            if not (query.get("query") or "").strip():
                results[query_id] = {"result": []}
                continue

            if not query.get("type"):
                raise ValueError("Missing 'type' in query")

            entity_type: str = query.get("type")

            if not Strategies.items.get(entity_type):
                raise ValueError(f"Unknown query type '{entity_type}' in query")

            strategy: ReconciliationStrategy = Strategies.items.get(entity_type)()

            candidate_data: list[dict[str, Any]] = await strategy.find_candidates(
                cursor=cursor,
                query=query.get("query"),
                properties={p["pid"]: p["v"] for p in query.get("properties", []) if "pid" in p and "v" in p},
                limit=default_query_limit,
            )

            results[query_id] = {"result": [strategy.as_candidate(data) for data in candidate_data]}
        return results
