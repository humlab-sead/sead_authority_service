# app.py
import json
import os
from typing import Any, Dict, List, Optional, Protocol

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from psycopg.rows import dict_row

# --- config ---
DB_DSN = os.environ.get("DB_DSN", "postgresql://sead_user:***@localhost:5432/sead")
AUTO_ACCEPT = float(os.environ.get("AUTO_ACCEPT_THRESHOLD", "0.90"))
ID_BASE = os.environ.get("ID_BASE", "https://w3id.org/sead/id/")

# --- Strategy Pattern for Entity-Specific Reconciliation ---


# Entity configuration with strategy classes
ENTITY_CONFIGS = {
    "Site": {
        "strategy_class": SiteReconciliationStrategy,
    },
    # Future entities
    # "Taxon": {
    #     "strategy_class": TaxonReconciliationStrategy,
    # }
}

app = FastAPI(title="SEAD Entity Reconciliation")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.on_event("startup")
async def startup():
    try:
        app.state.conn = await psycopg.AsyncConnection.connect(DB_DSN)
        # Initialize strategy instances
        app.state.strategies = {
            entity_type: config["strategy_class"]()
            for entity_type, config in ENTITY_CONFIGS.items()
        }
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise


@app.on_event("shutdown")
async def shutdown():
    try:
        if hasattr(app.state, "conn") and app.state.conn:
            await app.state.conn.close()
    except Exception as e:
        print(f"Error closing database connection: {e}")


@app.get("/reconcile")
async def meta():
    default_types = [
        {"id": entity_type, "name": entity_type}
        for entity_type in ENTITY_CONFIGS.keys()
    ]
    return {
        "name": "SEAD Entity Reconciliation",
        "identifierSpace": f"{ID_BASE}",
        "schemaSpace": "http://www.w3.org/2004/02/skos/core#",
        "defaultTypes": default_types,
    }


def _as_candidate(
    entity_data: Dict[str, Any], entity_type: str, strategy: ReconciliationStrategy
) -> Dict[str, Any]:
    """Convert entity data to OpenRefine candidate format"""
    entity_id = entity_data[strategy.get_entity_id_field()]
    label = entity_data[strategy.get_label_field()]
    score = float(entity_data.get("name_sim", 0))

    candidate = {
        "id": f"{ID_BASE}{strategy.get_id_path()}/{entity_id}",
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
async def reconcile(request: Request):
    try:
        payload = await request.json()
        queries = payload.get("queries")
        if isinstance(queries, str):
            queries = json.loads(queries)

        if not queries:
            return JSONResponse({"error": "No queries provided"}, status_code=400)

        results: Dict[str, Any] = {}
        async with app.state.conn.cursor(row_factory=dict_row) as cur:
            for qid, q in queries.items():
                text = (q.get("query") or "").strip()
                if not text:
                    results[qid] = {"result": []}
                    continue

                # Determine entity type and get strategy
                entity_type = q.get("type", "Site")
                if entity_type not in ENTITY_CONFIGS:
                    entity_type = "Site"

                strategy = app.state.strategies[entity_type]

                # Use strategy to find candidates
                candidate_data = await strategy.find_candidates(text, cur, limit=10)

                # Convert to OpenRefine format
                candidates = [
                    _as_candidate(data, entity_type, strategy)
                    for data in candidate_data
                ]

                results[qid] = {"result": candidates}

        return JSONResponse(results)

    except psycopg.Error as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)
    except json.JSONDecodeError as e:
        return JSONResponse({"error": "Invalid JSON in request"}, status_code=400)
    except Exception as e:
        return JSONResponse(
            {"error": f"Internal server error: {str(e)}"}, status_code=500
        )


@app.get("/reconcile/preview")
async def preview(id: str):

    if not id.startswith(ID_BASE):
        return ValueError("Invalid ID format", status_code=400)

    parts: List[str] = id.replace(ID_BASE, "").split("/")
    if len(parts) != 2:
        return ValueError("Invalid ID path", status_code=400)

    try:
        html: str = await preview(id)
        return HTMLResponse(html)
    except ValueError as e:
        return HTMLResponse({"error": str(e)}, status_code=e.status_code)

    return HTMLResponse(
        f"<div style='padding:8px;font:14px system-ui'>SEAD Entity: {id}</div>"
    )
