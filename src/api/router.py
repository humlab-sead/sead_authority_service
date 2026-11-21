import json
from typing import Any, Union

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from loguru import logger
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

from src import suggest
from src.api.candidate_verification import (
    DATABASE_ERRORS,
    UnsupportedReadinessType,
    get_reconciliation_readiness,
    verify_candidate_batch,
)

# Not used: ReconBatchRequest, ReconBatchRequestHandler, ReconQueryRequest
from src.api.model import (
    ReconBatchResponse,
    ReconcileReadinessResponse,
    ReconQuery,
    ReconServiceManifest,
    RecordDetailsResponse,
    RecordListResponse,
    RecordSelectionErrorEnvelope,
    RecordSelectionTypesResponse,
    SuggestEntityResponse,
    SuggestPropertyResponse,
    SuggestTypeResponse,
    VerifyCandidatesRequest,
    VerifyCandidatesResponse,
)
from src.configuration import Config, ConfigValue, get_config_provider, setup_config_store
from src.configuration.interface import ConfigLike
from src.metadata import get_reconcile_properties, get_reconciliation_metadata
from src.preview import render_preview
from src.reconcile import UnsupportedReconciliationTypeError, reconcile_queries
from src.record_identifiers import POSTGRES_INTEGER_MAX, parse_record_uri
from src.record_selection import (
    RecordSelectionConfigurationError,
    RecordSelectionError,
    collect_browse_list,
    configured_id_base,
    discovery_types,
    encode_json,
    fetch_record_row,
    load_record_selection_policy,
    record_payload,
    resolve_id_path,
    search_interactive,
    validate_interactive_query,
    validate_record_selection_configuration,
)
from src.strategies.configured_classifier import initialize_classifiers
from src.strategies.site import MissingCandidateExistsQueryError
from src.strategies.strategy import Strategies

# pylint: disable=unused-argument, redefined-builtin, too-many-locals, too-many-return-statements, too-many-branches

# Widest digit string that can still fit a PostgreSQL ``integer`` primary key.
_POSTGRES_INTEGER_MAX_DIGITS: int = len(str(POSTGRES_INTEGER_MAX))


def _record_selection_error(exc: RecordSelectionError) -> JSONResponse:
    """Return the record-selection error envelope for a request-time error."""
    return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status_code)


def _configuration_error(exc: RecordSelectionConfigurationError) -> JSONResponse:
    """Return the record-selection error envelope for a configuration problem."""
    logger.exception("Record selection is misconfigured: {}", exc)
    return _record_selection_error(RecordSelectionError("configuration_error", "Record selection is misconfigured.", 500))


def _single_record_identifier(request: Request) -> tuple[str, str]:
    """Require exactly one non-blank ``id`` or ``target_id`` query parameter."""
    pairs: list[tuple[str, str]] = list(request.query_params.multi_items())
    if len(pairs) != 1:
        raise RecordSelectionError("invalid_request", "Provide exactly one of 'id' or 'target_id'.")
    name, value = pairs[0]
    if name not in {"id", "target_id"}:
        raise RecordSelectionError("invalid_request", "Provide exactly one of 'id' or 'target_id'.")
    if value is None or not value.strip():
        raise RecordSelectionError("invalid_request", f"The '{name}' value must not be blank.")
    return name, value


def _parse_record_target_id(value: str) -> int | None:
    """Parse a positive ASCII decimal target ID.

    Returns ``None`` when the digits cannot name a PostgreSQL ``integer`` record, so
    a very long request value is reported as absent instead of raising from ``int()``,
    which limits how many digits it converts at once.
    """
    if not value.isascii() or not value.isdecimal():
        raise RecordSelectionError("invalid_request", "The 'target_id' value must be a positive integer.")
    digits: str = value.lstrip("0")
    if not digits:
        raise RecordSelectionError("invalid_request", "The 'target_id' value must be a positive integer.")
    if len(digits) > _POSTGRES_INTEGER_MAX_DIGITS:
        return None
    target_id: int = int(digits)
    return target_id if target_id <= POSTGRES_INTEGER_MAX else None


async def _read_interactive_queries(request: Request) -> Any:
    """Read the raw query mapping for a marked interactive request."""
    content_type: str = request.headers.get("content-type", "").lower()
    payload: Any = None
    try:
        if "application/x-www-form-urlencoded" in content_type:
            form_data = await request.form()
            raw: UploadFile | str | None = form_data.get("queries")
            if not isinstance(raw, str) or not raw.strip():
                raise RecordSelectionError("invalid_request", "No queries provided.")
            return json.loads(raw)
        body: bytes = await request.body()
        if not body:
            raise RecordSelectionError("invalid_request", "Empty request body.")
        payload = json.loads(body)
    except RecordSelectionError:  # pylint: disable=try-except-raise
        raise
    except (ValueError, UnicodeDecodeError) as exc:
        # ``json.loads`` raises a plain ``ValueError`` for an integer literal that
        # exceeds the interpreter's digit limit, not only ``JSONDecodeError``.
        raise RecordSelectionError("invalid_request", "Invalid JSON in request.") from exc

    if not isinstance(payload, dict):
        raise RecordSelectionError("invalid_request", "No queries provided.")
    queries: Any = payload.get("queries")
    if isinstance(queries, str):
        try:
            queries = json.loads(queries)
        except ValueError as exc:
            raise RecordSelectionError("invalid_request", "Invalid JSON in queries.") from exc
    return queries


async def _handle_interactive_search(request: Request) -> Response:
    """Handle a marked interactive search without changing unmarked batch behavior."""
    try:
        raw_queries: Any = await _read_interactive_queries(request)
        policy = load_record_selection_policy()
        query_id, entity_type, limit, query_text = validate_interactive_query(raw_queries, policy)
        result: dict[str, Any] = await search_interactive(entity_type, query_text, limit)
        return JSONResponse({query_id: result})
    except RecordSelectionError as exc:
        return _record_selection_error(exc)
    except RecordSelectionConfigurationError as exc:
        return _configuration_error(exc)
    except DATABASE_ERRORS as exc:
        logger.exception("Interactive record selection failed because the SEAD database is unavailable: {}", exc)
        return _record_selection_error(RecordSelectionError("database_unavailable", "SEAD database is unavailable.", 503))


async def get_config_dependency() -> ConfigLike:
    if not get_config_provider().is_configured():
        logger.info("Config Store is not configured, setting up...")
        await setup_config_store()
        initialize_classifiers()
        validate_record_selection_configuration()
    return get_config_provider().get_config()


router = APIRouter()


@router.get("/whoami")
async def whoami(request: Request):  # -> dict[str, Any]:
    host: None | str = request.url.hostname
    port: int | None = request.url.port
    base = str(request.host)  # type: ignore[assignment]
    # ASGI scope fallback
    server = request.scope.get("server")
    if server and (host is None or port is None):
        host, port = server[0], server[1]
    return {"host": host, "port": port, "base": base}


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
    metadata: dict[str, Any] = get_reconciliation_metadata(Strategies, host=str(request.base_url))
    manifest: ReconServiceManifest = ReconServiceManifest(**metadata)
    return ReconServiceManifest.model_validate(manifest)


@router.post(
    "/reconcile/verify-candidates",
    response_model=VerifyCandidatesResponse,
    response_model_exclude_none=True,
)
async def verify_candidates(
    body: VerifyCandidatesRequest,
    config: Config = Depends(get_config_dependency),
) -> VerifyCandidatesResponse:
    """Check candidate site IDs against SEAD without writing SIMS identity data."""
    try:
        return VerifyCandidatesResponse(results=await verify_candidate_batch(body.items))
    except MissingCandidateExistsQueryError as exc:
        logger.exception("Candidate verification is misconfigured: {}", exc)
        raise HTTPException(status_code=500, detail="Candidate verification is misconfigured") from exc
    except DATABASE_ERRORS as exc:
        logger.exception("Candidate verification failed because the SEAD database is unavailable: {}", exc)
        raise HTTPException(status_code=503, detail="SEAD database is unavailable") from exc


@router.get("/reconcile/readiness", response_model=ReconcileReadinessResponse)
async def reconciliation_readiness(
    type: str,
    config: Config = Depends(get_config_dependency),
) -> ReconcileReadinessResponse:
    """Check whether a reconciliation type can run its database-backed match query."""
    try:
        return await get_reconciliation_readiness(type)
    except UnsupportedReadinessType as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/reconcile", response_model=ReconBatchResponse, response_model_exclude_none=True)
async def reconcile(request: Request, config: Config = Depends(get_config_dependency)) -> Union[ReconBatchResponse, JSONResponse]:
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
    if (request.headers.get("x-record-selection") or "").strip().lower() == "interactive":
        return await _handle_interactive_search(request)  # type: ignore

    try:
        content_type = request.headers.get("content-type", "").lower()
        logger.info(f"Content-Type: {content_type}")

        queries: Any = None

        # Handle form-encoded data (what OpenRefine sends)
        if "application/x-www-form-urlencoded" in content_type:
            form_data = await request.form()
            logger.info(f"Form data keys: {list(form_data.keys())}")
            queries_str: UploadFile | str | None = form_data.get("queries")
            assert isinstance(queries_str, (str)), "Invalid 'queries' field type in form data"
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

    except UnsupportedReconciliationTypeError as exc:
        logger.info("Unsupported reconciliation type: {}", exc)
        return JSONResponse({"error": str(exc)}, status_code=422)
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
    id_base: str = ConfigValue("options:id_base").resolve() or ""
    if not id.startswith(id_base):
        return HTMLResponse("Invalid ID format", status_code=400)

    parts: list[str] = id.replace(id_base, "").split("/")
    if len(parts) != 2:
        return HTMLResponse("Invalid ID path", status_code=400)

    try:
        html = await render_preview(id)
        return HTMLResponse(html)
    except ValueError as e:
        return HTMLResponse(f"Error: {str(e)}", status_code=500)


# ============================================================================
# Record selection (discovery, lists, details)
# ============================================================================
# `GET /records/types` is declared before `GET /records/{type}` so the static
# discovery route is not captured by the type path parameter.


@router.get("/records/types", response_model=RecordSelectionTypesResponse)
async def record_selection_types(config: Config = Depends(get_config_dependency)) -> RecordSelectionTypesResponse:
    """Return independent record-selection capabilities for the pilot types."""
    return RecordSelectionTypesResponse(types=discovery_types())  # type: ignore


@router.get(
    "/records/{type}/details",
    response_model=RecordDetailsResponse,
    response_model_exclude_none=True,
    responses={
        404: {"description": "Record not found", "model": RecordSelectionErrorEnvelope},
        422: {"description": "Invalid or unsupported request", "model": RecordSelectionErrorEnvelope},
        503: {"description": "SEAD database unavailable", "model": RecordSelectionErrorEnvelope},
    },
)
async def record_details(
    request: Request, type: str, config: Config = Depends(get_config_dependency)
) -> Response:  # pylint: disable=redefined-builtin
    """Return one record by URI (`id`) or positive integer ID (`target_id`)."""
    try:
        policy = load_record_selection_policy()
        flags = policy.flags_for(type)
        id_base: str = configured_id_base()
        identifier, raw_value = _single_record_identifier(request)
        if identifier == "id":
            if not flags.details:
                raise RecordSelectionError("unsupported_capability", f"Details lookup by URI is not enabled for '{type}'.")
            target_id = parse_record_uri(raw_value, type, id_base)
            if target_id is None:
                raise RecordSelectionError("invalid_request", "The 'id' value is not a valid record URI for this type.")
        else:
            if not flags.identifier_search:
                raise RecordSelectionError("unsupported_capability", f"Identifier lookup is not enabled for '{type}'.")
            target_id = _parse_record_target_id(raw_value)

        row = await fetch_record_row(type, target_id) if target_id is not None else None
        if row is None:
            raise RecordSelectionError("record_not_found", "No record exists for the requested identifier.", 404)

        body: bytes = encode_json({"item": record_payload(type, row, id_base, resolve_id_path(type))})
        return Response(content=body, media_type="application/json")
    except RecordSelectionError as exc:
        return _record_selection_error(exc)
    except RecordSelectionConfigurationError as exc:
        return _configuration_error(exc)
    except DATABASE_ERRORS as exc:
        logger.exception("Record details lookup failed because the SEAD database is unavailable: {}", exc)
        return _record_selection_error(RecordSelectionError("database_unavailable", "SEAD database is unavailable.", 503))


@router.get(
    "/records/{type}",
    response_model=RecordListResponse,
    responses={
        409: {"description": "List too large to browse", "model": RecordSelectionErrorEnvelope},
        422: {"description": "Invalid or unsupported request", "model": RecordSelectionErrorEnvelope},
        503: {"description": "SEAD database unavailable", "model": RecordSelectionErrorEnvelope},
    },
)
async def record_list(
    request: Request, type: str, config: Config = Depends(get_config_dependency)
) -> Response:  # pylint: disable=redefined-builtin
    """Return the complete projected record list for one type, or an explicit too-large error."""
    try:
        if list(request.query_params.multi_items()):
            raise RecordSelectionError("invalid_request", "The record list does not accept query parameters.")
        policy = load_record_selection_policy()
        flags = policy.flags_for(type)
        if not flags.browse:
            raise RecordSelectionError("unsupported_capability", f"Browse is not enabled for '{type}'.")
        body: bytes = await collect_browse_list(type, policy)
        return Response(content=body, media_type="application/json")
    except RecordSelectionError as exc:
        return _record_selection_error(exc)
    except RecordSelectionConfigurationError as exc:
        return _configuration_error(exc)
    except DATABASE_ERRORS as exc:
        logger.exception("Record list failed because the SEAD database is unavailable: {}", exc)
        return _record_selection_error(RecordSelectionError("database_unavailable", "SEAD database is unavailable.", 503))


# ============================================================================
# OpenRefine Suggest API Endpoints
# ============================================================================
# These endpoints enable autocomplete and inline tooltip previews in OpenRefine


@router.get("/suggest/entity", response_model=SuggestEntityResponse)
async def suggest_entity(
    prefix: str = "", type: str = "", config: Config = Depends(get_config_dependency)
) -> Union[SuggestEntityResponse, JSONResponse]:
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
        items: dict[str, Any] = await suggest.suggest_entities(prefix=prefix, entity_type=type, limit=10)
        return SuggestEntityResponse(result=items.get("result", []))
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Error in suggest_entity: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/suggest/type", response_model=SuggestTypeResponse)
async def suggest_type(prefix: str = "", config: Config = Depends(get_config_dependency)) -> Union[SuggestTypeResponse, JSONResponse]:
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
        result: dict[str, Any] = await suggest.suggest_types(prefix=prefix)
        return SuggestTypeResponse(result=result.get("result", []))
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Error in suggest_type: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/suggest/property", response_model=SuggestPropertyResponse)
async def suggest_property(
    prefix: str = "", type: str = "", config: Config = Depends(get_config_dependency)
) -> Union[SuggestPropertyResponse, JSONResponse]:
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
        result: dict[str, Any] = await suggest.suggest_properties(prefix=prefix, entity_type=type)
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

        result: dict[str, Any] = await suggest.render_flyout_preview(id)
        return JSONResponse(result)
    except ValueError as e:  # pylint: disable=broad-exception-caught
        logger.warning(f"Invalid flyout request: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(f"Error in flyout_entity: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
