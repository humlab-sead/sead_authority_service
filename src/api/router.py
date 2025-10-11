"""
FastAPI router for SEAD Entity Reconciliation Service endpoints.
"""

import json
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from loguru import logger

# Not used: ReconBatchRequest, ReconBatchRequestHandler, ReconQueryRequest
from src.api.model import ReconBatchResponse, ReconQuery, ReconServiceManifest, SuggestEntityResponse, SuggestPropertyResponse, SuggestTypeResponse
from src.configuration import Config, ConfigValue, get_config_provider, setup_config_store
from src.metadata import get_reconcile_properties, get_reconciliation_metadata
from src.preview import render_preview
from src.reconcile import reconcile_queries
from src.strategies.strategy import Strategies
from src.suggest import render_flyout_preview, suggest_entities
from src.suggest import suggest_properties as suggest_properties_api
from src.suggest import suggest_types

# pylint: disable=unused-argument, redefined-builtin, too-many-locals, too-many-return-statements, too-many-branches


async def get_config_dependency() -> Config:
    if not get_config_provider().is_configured():
        logger.info("Config Store is not configured, setting up...")
        await setup_config_store()
    return get_config_provider().get_config()


router = APIRouter()


@router.get("/whoami")
async def whoami(request: Request):
    host = request.url.hostname
    port = request.url.port
    base = str(request.base_url)  # e.g. "http://localhost:8000/"
    # ASGI scope fallback
    server = request.scope.get("server")
    if server and (host is None or port is None):
        host, port = server[0], server[1]
    return {"host": host, "port": port, "base_url": base}


@router.get("/is_alive")
async def is_alive(config: Config = Depends(get_config_dependency)) -> dict[str, str]:
    """Health check endpoint"""
    return {"status": "alive"}


@router.get("/reconcile", response_model=ReconServiceManifest, response_model_exclude_none=True)
async def meta(request: Request, config: Config = Depends(get_config_dependency)) -> ReconServiceManifest:
    """
    OpenRefine reconciliation service metadata endpoint.

    Returns service configuration including supported entity types and properties
    that can be used for enhanced reconciliation matching.
    """
    # get hostname and port from request headers or ASGI scope
    return get_reconciliation_metadata(Strategies, base_url=request.base_url)


@router.post("/reconcile", response_model=ReconBatchResponse, response_model_exclude_none=True)
async def reconcile(request: Request, config: Config = Depends(get_config_dependency)) -> ReconBatchResponse:
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
        content_type = request.headers.get("content-type", "").lower()
        logger.info(f"Content-Type: {content_type}")

        queries: Any = None

        # Handle form-encoded data (what OpenRefine sends)
        if "application/x-www-form-urlencoded" in content_type:
            form_data = await request.form()
            logger.info(f"Form data keys: {list(form_data.keys())}")
            queries_str = form_data.get("queries")
            if queries_str:
                queries = json.loads(queries_str)
            else:
                logger.error("No 'queries' field in form data")
                return JSONResponse({"error": "No queries provided"}, status_code=400)
        else:
            # Handle JSON data (fallback)
            try:
                body = await request.body()
                if body:
                    payload = json.loads(body)
                    queries = payload.get("queries")
                else:
                    logger.error("Empty request body")
                    return JSONResponse({"error": "Empty request body"}, status_code=400)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return JSONResponse({"error": "Invalid JSON in request"}, status_code=400)

        # Handle queries as string (sometimes OpenRefine double-encodes)
        if isinstance(queries, str):
            logger.info("Queries is string, parsing again...")
            queries = json.loads(queries)

        if not isinstance(queries, dict) or not queries:
            logger.error("No queries found after parsing")
            return JSONResponse({"error": "No queries provided"}, status_code=400)

        # Validate and parse queries using Pydantic
        validated_queries = {}
        for query_id, query_data in queries.items():
            try:
                # Set default type if missing
                if "type" not in query_data:
                    logger.info(f"Adding default type 'site' to query {query_id}")
                    query_data["type"] = "site"

                # Validate using Pydantic model
                validated_query = ReconQuery.model_validate(query_data)
                validated_queries[query_id] = validated_query
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Invalid query {query_id}: {e}")
                return JSONResponse({"error": f"Invalid query {query_id}: {str(e)}"}, status_code=400)

        # Convert Pydantic objects back to dict for compatibility with existing reconcile_queries function
        queries_dict_for_processing = {}
        for query_id, validated_query in validated_queries.items():
            queries_dict_for_processing[query_id] = validated_query.model_dump(exclude_none=True)

        results: dict[str, Any] = await reconcile_queries(queries_dict_for_processing)

        response = ReconBatchResponse(root=results)
        return response

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Exception in reconcile endpoint: {e}", exc_info=True)
        return JSONResponse({"error": f"Server error: {str(e)}"}, status_code=500)


@router.get("/reconcile/properties")
async def suggest_properties(query: str = "", type: str = "", config: Config = Depends(get_config_dependency)) -> JSONResponse:
    """
    Property suggestion endpoint for OpenRefine.

    Returns available properties that can be used for enhanced reconciliation.
    OpenRefine calls this endpoint to populate property selection dropdowns.

    Args:
        query: Optional search term to filter properties
        type: Optional entity type to filter properties (e.g., "site", "taxon")

    Returns:
        JSON response with matching properties
    """
    # Get properties from registered strategies
    filtered_properties: list[dict[str, str]] | Any = get_reconcile_properties(Strategies, query, type)

    return JSONResponse({"properties": filtered_properties})


@router.get("/reconcile/preview")
async def preview(id: str, config: Config = Depends(get_config_dependency)) -> HTMLResponse:  # pylint: disable=redefined-builtin
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


# ============================================================================
# OpenRefine Suggest API Endpoints
# ============================================================================
# These endpoints enable autocomplete and inline tooltip previews in OpenRefine


@router.get("/suggest/entity", response_model=SuggestEntityResponse)
async def suggest_entity(prefix: str = "", type: str = "", config: Config = Depends(get_config_dependency)) -> SuggestEntityResponse:
    """
    Entity autocomplete endpoint for OpenRefine Suggest API.

    Returns entity suggestions as the user types, enabling autocomplete
    functionality in OpenRefine reconciliation dialogs.

    Args:
        prefix: The text prefix to match (minimum 2 characters)
        type: Optional entity type filter (e.g., 'site', 'location', 'taxon')

    Returns:
        JSON response with suggested entities in format:
        {
            "result": [
                {
                    "id": "https://w3id.org/sead/id/site/123",
                    "name": "Site Name",
                    "type": [{"id": "site", "name": "site"}],
                    "description": "Additional context",
                    "score": 95.5
                }
            ]
        }
    """
    try:
        items: dict[str, Any] = await suggest_entities(prefix=prefix, entity_type=type, limit=10)
        return SuggestEntityResponse(result=items.get("result", []))
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Error in suggest_entity: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/suggest/type", response_model=SuggestTypeResponse)
async def suggest_type(prefix: str = "", config: Config = Depends(get_config_dependency)) -> SuggestTypeResponse:
    """
    Type autocomplete endpoint for OpenRefine Suggest API.

    Returns entity type suggestions filtered by prefix.

    Args:
        prefix: Optional prefix to filter types

    Returns:
        JSON response with type suggestions:
        {
            "result": [
                {"id": "site", "name": "Site"},
                {"id": "taxon", "name": "Taxon"}
            ]
        }
    """
    try:
        result: dict[str, Any] = await suggest_types(prefix=prefix)
        return SuggestTypeResponse(result=result.get("result", []))
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Error in suggest_type: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/suggest/property", response_model=SuggestPropertyResponse)
async def suggest_property(prefix: str = "", type: str = "", config: Config = Depends(get_config_dependency)) -> SuggestPropertyResponse:
    """
    Property autocomplete endpoint for OpenRefine Suggest API.

    Returns property suggestions filtered by prefix and optional type.

    Args:
        prefix: Optional prefix to filter properties
        type: Optional entity type to filter properties

    Returns:
        JSON response with property suggestions:
        {
            "result": [
                {
                    "id": "coordinates",
                    "name": "Coordinates",
                    "description": "Geographic coordinates"
                }
            ]
        }
    """
    try:
        result: dict[str, Any] = await suggest_properties_api(prefix=prefix, entity_type=type)
        return SuggestPropertyResponse(result=result.get("result", []))
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Error in suggest_property: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/flyout/entity")
@router.post("/flyout/entity")
async def flyout_entity(id: str = "", config: Config = Depends(get_config_dependency)) -> JSONResponse:
    """
    Flyout/tooltip preview endpoint for OpenRefine Suggest API.

    Returns compact HTML preview for inline tooltip display when hovering
    over entity suggestions in OpenRefine. This enables the tooltip preview
    experience instead of opening a new browser tab.

    Args:
        id: Entity URI to preview (e.g., 'https://w3id.org/sead/id/site/123')

    Returns:
        JSON response with entity details:
        {
            "id": "https://w3id.org/sead/id/site/123",
            "html": "<div>...formatted HTML preview...</div>"
        }
    """
    try:
        if not id:
            return JSONResponse({"error": "Missing 'id' parameter"}, status_code=400)

        result: dict[str, Any] = await render_flyout_preview(id)
        return JSONResponse(result)
    except ValueError as e:  # pylint: disable=broad-exception-caught
        logger.warning(f"Invalid flyout request: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Error in flyout_entity: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
