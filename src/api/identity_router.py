"""SIMS Identity API router.

All endpoints are prefixed with ``/identity`` (registered in main.py).

Endpoints:
  POST   /identity/resolve                                         Resolve + bind a batch of source identities
  GET    /identity/binding-sets/{binding_set_uuid}                 Get binding set status
  POST   /identity/binding-sets/{binding_set_uuid}/confirm         Confirm a proposed binding set
  POST   /identity/binding-sets/{binding_set_uuid}/change-request  Associate a CR name
  POST   /identity/detect-change                                   Content-hash change detection
  GET    /identity/scopes                                          List known source scopes
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.configuration import get_config_provider, setup_config_store
from src.configuration.interface import ConfigLike
from src.identity.models import (
    BindingSetResponse,
    ChangeDetectionRequest,
    ChangeDetectionResult,
    ResolutionOutcome,
    ResolutionRequest,
    SourceScope,
)
from src.identity.policy import CAPABILITY_VERSION, IdentityPolicy
from src.identity.service import IdentityBindingConflict, IdentityService

identity_router = APIRouter(prefix="/identity", tags=["identity"])


# ---------------------------------------------------------------------------
# Shared dependencies
# ---------------------------------------------------------------------------


async def get_config_dep() -> ConfigLike:
    provider = get_config_provider()
    if not provider.is_configured():
        await setup_config_store()
    return provider.get_config()


def get_identity_service() -> IdentityService:
    """FastAPI dependency — returns a fresh IdentityService per request.

    The service is stateless (all state is in PostgreSQL); constructing
    one per request is cheap and avoids shared-state problems.
    """
    return IdentityService()


def get_identity_policy() -> IdentityPolicy:
    """FastAPI dependency — returns a fresh policy snapshot for capability checks."""
    return IdentityPolicy()


# ---------------------------------------------------------------------------
# Request / response schemas specific to the API layer
# ---------------------------------------------------------------------------


class ResolveRequest(BaseModel):
    """Request body for POST /identity/resolve."""

    scope_name: str = Field(
        description="Source Scope name, e.g. 'sead://reconciliation' or a provider URI."
    )
    submission_name: str = Field(
        description="Human-readable name for this submission batch."
    )
    requests: list[ResolutionRequest] = Field(
        description="One entry per domain entity to resolve.",
        min_length=1,
    )
    created_by: str | None = Field(default=None, description="Agent or user identifier for audit trail.")


class ResolveResponse(BaseModel):
    """Response body for POST /identity/resolve."""

    submission_uuid: UUID
    scope_uuid: UUID
    binding_set: BindingSetResponse
    outcomes: list[ResolutionOutcome]


class AssociateChangeRequestBody(BaseModel):
    change_request_name: str = Field(description="Sqitch change name to associate with this Binding Set.")


class EntityCapabilityResponse(BaseModel):
    """Published capability for one configured entity type."""

    entity_type: str
    entity_subtype: str
    bind_existing: bool
    allocate_new: bool
    auto_confirm: bool
    accept_uuid: bool


class CapabilitiesResponse(BaseModel):
    """Response body for GET /identity/capabilities."""

    version: str
    entities: list[EntityCapabilityResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _require_supported_operation(policy: IdentityPolicy, request: ResolutionRequest) -> None:
    """Raise HTTP 422 when *request* targets an unconfigured or unsupported operation."""
    operation = "bind_existing" if request.approved_aggregate_id is not None else "allocate_new"
    if request.entity_type not in policy.known_entity_types():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Entity type '{request.entity_type}' is not configured in SIMS",
        )
    if not policy.supports(request.entity_type, operation):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Operation '{operation}' is not supported for entity type '{request.entity_type}'",
        )


@identity_router.get(
    "/capabilities",
    response_model=CapabilitiesResponse,
    summary="List configured SIMS identity capabilities",
)
async def get_capabilities(
    policy: IdentityPolicy = Depends(get_identity_policy),
) -> CapabilitiesResponse:
    """Return the supported identity operations for each configured entity type.

    Capability support is derived from validated entity configuration. Unlisted
    entity types have no capabilities and are rejected by the resolve endpoint.
    """
    return CapabilitiesResponse(
        version=CAPABILITY_VERSION,
        entities=[
            EntityCapabilityResponse(
                entity_type=cap.entity_type,
                entity_subtype=cap.entity_subtype,
                bind_existing=cap.bind_existing,
                allocate_new=cap.allocate_new,
                auto_confirm=cap.auto_confirm,
                accept_uuid=cap.accept_uuid,
            )
            for cap in policy.get_capabilities()
        ],
    )


@identity_router.post(
    "/resolve",
    response_model=ResolveResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve and bind a batch of source identities",
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Approved aggregate ID conflicts with SIMS identity data or the source has a proposed binding"
        }
    },
)
async def resolve(
    body: ResolveRequest,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
    policy: IdentityPolicy = Depends(get_identity_policy),
) -> ResolveResponse:
    """Resolve and immediately bind a batch of domain entities.

    Steps performed atomically from the caller's perspective:
    1. Reject unconfigured entity types and unsupported operations.
    2. Upsert the Source Scope (creates it if unknown).
    3. Create a Submission within that scope.
    4. For each resolution request: upsert Source Identity, check for existing Binding.
    5. Bind all outcomes into a single Binding Set.
       - Provider-owned entities: auto-confirm.
       - Shared metadata entities: set is left in ``proposed`` state.

    Idempotent: submitting the same entities within the same scope always produces
    the same Source Identity records and, if already bound, the same Tracked Identity
    UUIDs (FR-12, FR-13).
    """
    for req in body.requests:
        _require_supported_operation(policy, req)

    scope = await service.get_or_create_scope(
        body.scope_name,
        created_by=body.created_by,
    )
    submission = await service.create_submission(
        scope_uuid=scope.scope_uuid,
        submission_name=body.submission_name,
        created_by=body.created_by,
    )

    outcomes: list[ResolutionOutcome] = []
    for req in body.requests:
        try:
            outcome = await service.resolve_identity(
                scope_uuid=scope.scope_uuid,
                request=req,
                submission_uuid=submission.submission_uuid,
                created_by=body.created_by,
            )
        except IdentityBindingConflict as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        outcomes.append(outcome)

    try:
        binding_set = await service.bind(
            submission_uuid=submission.submission_uuid,
            outcomes=outcomes,
            created_by=body.created_by,
        )
    except IdentityBindingConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ResolveResponse(
        submission_uuid=submission.submission_uuid,
        scope_uuid=scope.scope_uuid,
        binding_set=binding_set,
        outcomes=outcomes,
    )


@identity_router.get(
    "/binding-sets/{binding_set_uuid}",
    response_model=BindingSetResponse,
    summary="Get binding set status",
    responses={404: {"description": "Binding set not found"}},
)
async def get_binding_set(
    binding_set_uuid: UUID,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> BindingSetResponse:
    """Return the current state of a Binding Set.

    Path parameter: `binding_set_uuid` — UUID returned by ``POST /identity/resolve``.
    """
    result = await service.get_binding_set(binding_set_uuid)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Binding set {binding_set_uuid} not found")
    return result


@identity_router.post(
    "/binding-sets/{binding_set_uuid}/confirm",
    response_model=BindingSetResponse,
    summary="Confirm a proposed binding set",
    responses={404: {"description": "Binding set not found"}},
)
async def confirm_binding_set(
    binding_set_uuid: UUID,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> BindingSetResponse:
    """Manually confirm a Binding Set that was left in ``proposed`` state.

    Applies to shared-metadata sets where ``auto_confirm`` is false. No
    request body required — the binding set UUID in the path is sufficient.
    Idempotent for already-confirmed sets.
    """
    binding_set = await service.confirm_binding_set(binding_set_uuid)
    if binding_set is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Binding set {binding_set_uuid} not found")
    result = await service.get_binding_set(binding_set_uuid)
    assert result is not None
    return result


@identity_router.post(
    "/binding-sets/{binding_set_uuid}/change-request",
    response_model=BindingSetResponse,
    summary="Associate a Sqitch Change Request with a confirmed binding set",
    responses={404: {"description": "Binding set not found or not in confirmed state"}},
)
async def associate_change_request(
    binding_set_uuid: UUID,
    body: AssociateChangeRequestBody,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> BindingSetResponse:
    """Record a Sqitch Change Request name against a confirmed Binding Set (FR-25, FR-27).

    Example body: ``{"change_request_name": "deploy/2026-04-01/site-batch-1"}``.
    The binding set must already be in ``confirmed`` state.
    """
    binding_set = await service.associate_change_request(binding_set_uuid, body.change_request_name)
    if binding_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Binding set {binding_set_uuid} not found or not in confirmed state",
        )
    result = await service.get_binding_set(binding_set_uuid)
    assert result is not None
    return result


@identity_router.post(
    "/detect-change",
    response_model=ChangeDetectionResult,
    summary="Detect content change for a tracked identity",
    responses={404: {"description": "Tracked identity not found"}},
)
async def detect_change(
    body: ChangeDetectionRequest,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> ChangeDetectionResult:
    """Compare an incoming content hash against the stored hash (FR-24).

    Returns ``insert``, ``update``, or ``skip``.
    Example body: ``{"tracked_identity_uuid": "<uuid>", "content_hash": "<xxh64 hex>"}``.
    """
    try:
        return await service.detect_change(body)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@identity_router.get(
    "/scopes",
    response_model=list[SourceScope],
    summary="List all known source scopes",
)
async def list_scopes(
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> list[SourceScope]:
    """Return all registered Source Scopes."""
    return await service.list_scopes()
