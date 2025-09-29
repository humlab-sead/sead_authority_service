import json
import os
from typing import Any, Dict, List

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger
from psycopg.rows import dict_row

from configuration.config import Config
from configuration.inject import ConfigStore, ConfigValue
from render import render_preview
from strategies.interface import ReconciliationStrategy, Strategies
from utility import configure_logging, create_db_uri

AUTO_ACCEPT = float(os.environ.get("AUTO_ACCEPT_THRESHOLD", "0.90"))

ConfigStore.configure_context(source="config/config.yml", env_filename=".env", env_prefix="SEAD_AUTHORITY")


app = FastAPI(title="SEAD Entity Reconciliation Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/is_alive")
async def is_alive():
    return {"status": "alive"}

@app.on_event("startup")
async def startup():
    try:

        configure_logging(ConfigValue("logging").resolve() or {})

        cfg: Config = ConfigStore.config()
        dsn: str = create_db_uri(**cfg.get("options:database"))
        app.state.conn = await psycopg.AsyncConnection.connect(dsn)
        app.state.config = cfg

        cfg.add({"runtime:connection": app.state.conn})

    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    try:
        if hasattr(app.state, "conn") and app.state.conn:
            await app.state.conn.close()
    except Exception as e:  # pylint: disable=broad-except
        print(f"Error closing database connection: {e}")


@app.get("/reconcile")
async def meta():
    default_types: List[Dict[str, str]] = [{"id": entity_type, "name": entity_type} for entity_type in Strategies.items]
    id_base: str = ConfigValue("service:id_base").resolve()
    return {
        "name": "SEAD Entity Reconciliation",
        "identifierSpace": f"{id_base}",
        "schemaSpace": "http://www.w3.org/2004/02/skos/core#",
        "defaultTypes": default_types,
    }


def _as_candidate(entity_data: dict[str, Any], entity_type: str, strategy: ReconciliationStrategy) -> dict[str, Any]:
    """Convert entity data to OpenRefine candidate format"""
    entity_id: str = entity_data[strategy.get_entity_id_field()]
    label: str = entity_data[strategy.get_label_field()]
    score = float(entity_data.get("name_sim", 0))
    id_base: str = ConfigValue("service:id_base").resolve()
    candidate: dict[str, Any] = {
        "id": f"{id_base}{strategy.get_id_path()}/{entity_id}",
        "name": label,
        "score": min(100.0, round(score * 100, 2)),
        "match": bool(score >= AUTO_ACCEPT),
        "type": [{"id": entity_type, "name": entity_type}],
    }

    # Add additional metadata if available
    if "distance_km" in entity_data:
        candidate["distance_km"] = round(entity_data["distance_km"], 2)

    return candidate


@app.post("/reconcile")
async def reconcile(request: Request) -> JSONResponse:
    try:
        payload = await request.json()
        queries = payload.get("queries")
        if isinstance(queries, str):
            queries = json.loads(queries)

        if not queries:
            return JSONResponse({"error": "No queries provided"}, status_code=400)

        results: dict[str, Any] = {}
        async with app.state.conn.cursor(row_factory=dict_row) as cur:
            for query_id, query in queries.items():

                text: str = (query.get("query") or "").strip()
                if not text:
                    results[query_id] = {"result": []}
                    continue

                if not query.get("type"):
                    raise ValueError("Missing 'type' in query")

                entity_type: str = query.get("type")

                strategy: ReconciliationStrategy = Strategies.items[entity_type]

                candidate_data: list[dict[str, Any]] = await strategy.find_candidates(text, cur, limit=10)

                candidates: list[dict[str, Any]] = [_as_candidate(data, entity_type, strategy) for data in candidate_data]

                results[query_id] = {"result": candidates}

        return JSONResponse(results)

    except psycopg.Error as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON in request"}, status_code=400)
    except Exception as e:  # pylint: disable=broad-except
        return JSONResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)


@app.get("/reconcile/preview")
async def preview(
    id: str,  # pylint: disable=redefined-builtin
) -> HTMLResponse:

    id_base: str = ConfigValue("service:id_base").resolve()
    if not id.startswith(id_base):
        return HTMLResponse("Invalid ID format", status_code=400)

    parts: list[str] = id.replace(id_base, "").split("/")
    if len(parts) != 2:
        return HTMLResponse("Invalid ID path", status_code=400)

    try:
        html: str = await render_preview(id)
        return HTMLResponse(html)
    except ValueError as e:
        return HTMLResponse({"error": str(e)}, status_code=500)
