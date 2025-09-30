"""
FastAPI router for SEAD Entity Reconciliation Service endpoints.
"""

import json
from typing import Any

import psycopg
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.configuration.inject import ConfigValue
from src.reconcile import reconcile_queries
from src.render import render_preview
from strategies.interface import Strategies

router = APIRouter()


@router.get("/is_alive")
async def is_alive() -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "alive"}


@router.get("/reconcile")
async def meta():
    """
    OpenRefine reconciliation service metadata endpoint.

    Returns service configuration including supported entity types and properties
    that can be used for enhanced reconciliation matching.
    """
    default_types: list[dict[str, str]] = [{"id": entity_type, "name": entity_type} for entity_type in Strategies.items]
    id_base: str = ConfigValue("service:id_base").resolve()

    return {
        "name": "SEAD Entity Reconciliation",
        "identifierSpace": f"{id_base}",
        "schemaSpace": "http://www.w3.org/2004/02/skos/core#",
        "defaultTypes": default_types,
        "extend": {
            "propose_properties": {"service_url": f"{id_base}reconcile", "service_path": "/properties"},
            "property_settings": [
                {
                    "name": "latitude",
                    "label": "Latitude",
                    "type": "number",
                    "help_text": "Geographic latitude in decimal degrees (WGS84)",
                    "settings": {"min": -90.0, "max": 90.0, "precision": 6},
                },
                {
                    "name": "longitude",
                    "label": "Longitude",
                    "type": "number",
                    "help_text": "Geographic longitude in decimal degrees (WGS84)",
                    "settings": {"min": -180.0, "max": 180.0, "precision": 6},
                },
                {"name": "country", "label": "Country", "type": "string", "help_text": "Country name where the site is located"},
                {"name": "national_id", "label": "National Site ID", "type": "string", "help_text": "Official national site identifier or registration number"},
                {"name": "place_name", "label": "Place Name", "type": "string", "help_text": "Geographic place, locality, or administrative area name"},
            ],
        },
    }


@router.post("/reconcile")
async def reconcile(request: Request) -> JSONResponse:
    """
    OpenRefine reconciliation endpoint for batch queries.

    This endpoint receives batch reconciliation requests from OpenRefine and returns
    matching candidates for each query. OpenRefine sends queries in a specific JSON
    format that this endpoint processes.

    Request Body Structure:
    ----------------------
    The request must contain a JSON object with a "queries" field that can be either:
    1. A JSON object containing query definitions
    2. A JSON string that needs to be parsed (OpenRefine sometimes does this)

    Queries Object Format:
    ---------------------
    {
        "queries": {
            "q0": {
                "query": "Site name to search for",
                "type": "Site",
                "limit": 10,
                "type_strict": "any"
            },
            "q1": {
                "query": "Another site name",
                "type": "Site"
            }
        }
    }

    Query Fields:
    -------------
    - query (required): The text string to reconcile/match against
    - type (required): Entity type to search for (e.g., "Site", "Taxon")
    - limit (optional): Maximum number of results to return (default: 10)
    - type_strict (optional): How strictly to enforce type matching ("any", "all", "should")

    Extended Query Format (with properties):
    ---------------------------------------
    OpenRefine can also send additional properties for enhanced matching:
    {
        "q0": {
            "query": "Uppsala",
            "type": "Site",
            "properties": [
                {
                    "pid": "coordinates",
                    "v": "59.8586,17.6389"
                },
                {
                    "pid": "country",
                    "v": "Sweden"
                }
            ]
        }
    }

    Response Format:
    ---------------
    Returns a JSON object with results for each query ID:
    {
        "q0": {
            "result": [
                {
                    "id": "https://w3id.org/sead/id/site/123",
                    "name": "Uppsala Site",
                    "score": 95.5,
                    "match": true,
                    "type": [{"id": "Site", "name": "Site"}],
                    "distance_km": 1.2
                }
            ]
        },
        "q1": {
            "result": []
        }
    }

    Candidate Fields:
    ----------------
    - id: Unique identifier URI for the entity
    - name: Human-readable name/label
    - score: Matching confidence score (0-100)
    - match: Boolean indicating high-confidence match (score >= threshold)
    - type: Array of type objects with id and name
    - distance_km: Optional distance in kilometers (for geographic entities)

    Error Responses:
    ---------------
    Returns appropriate HTTP status codes with error details:
    - 400: Missing queries, invalid JSON format
    - 500: Database errors, internal server errors
    """
    try:
        payload = await request.json()
        queries = payload.get("queries")
        if isinstance(queries, str):
            queries = json.loads(queries)

        if not queries:
            return JSONResponse({"error": "No queries provided"}, status_code=400)

        results: dict[str, Any] = await reconcile_queries(queries)

        return JSONResponse(results)

    except psycopg.Error as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON in request"}, status_code=400)
    except Exception as e:  # pylint: disable=broad-except
        return JSONResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)


@router.get("/reconcile/properties")
async def suggest_properties(query: str = "") -> JSONResponse:
    """
    Property suggestion endpoint for OpenRefine.

    Returns available properties that can be used for enhanced reconciliation.
    OpenRefine calls this endpoint to populate property selection dropdowns.

    Args:
        query: Optional search term to filter properties

    Returns:
        JSON response with matching properties
    """
    # Define all supported properties for SEAD entities
    all_properties: list[dict[str, str]] = [
        {
            "id": "latitude",
            "name": "Latitude",
            "type": "number",
            "description": "Geographic latitude in decimal degrees (WGS84)",
        },
        {
            "id": "longitude",
            "name": "Longitude",
            "type": "number",
            "description": "Geographic longitude in decimal degrees (WGS84)",
        },
        {
            "id": "country",
            "name": "Country",
            "type": "string",
            "description": "Country name where the site is located",
        },
        {
            "id": "national_id",
            "name": "National Site ID",
            "type": "string",
            "description": "Official national site identifier or registration number",
        },
        {
            "id": "place_name",
            "name": "Place Name",
            "type": "string",
            "description": "Geographic place, locality, or administrative area name",
        },
    ]

    # Filter properties based on query if provided
    if query:
        query_lower = query.lower()
        filtered_properties = [
            prop
            for prop in all_properties
            if query_lower in prop["id"].lower() or query_lower in prop["name"].lower() or query_lower in prop["description"].lower()
        ]
    else:
        filtered_properties: list[dict[str, str]] = all_properties

    return JSONResponse({"properties": filtered_properties})


@router.get("/reconcile/preview")
async def preview(
    id: str,  # pylint: disable=redefined-builtin
) -> HTMLResponse:
    """Preview endpoint for OpenRefine reconciliation results"""
    id_base: str = ConfigValue("options:id_base").resolve()
    if not id.startswith(id_base):
        return HTMLResponse("Invalid ID format", status_code=400)

    parts: list[str] = id.replace(id_base, "").split("/")
    if len(parts) != 2:
        return HTMLResponse("Invalid ID path", status_code=400)

    try:
        html: str = await render_preview(id)
        return HTMLResponse(html)
    except ValueError as e:
        return HTMLResponse(f"Error: {str(e)}", status_code=500)
