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
from src.identity.service import IdentityService

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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@identity_router.post(
    "/resolve",
    response_model=ResolveResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve and bind a batch of source identities",
)
async def resolve(
    body: ResolveRequest,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> ResolveResponse:
    """Resolve and immediately bind a batch of domain entities.

    Steps performed atomically from the caller's perspective:
    1. Upsert the Source Scope (creates it if unknown).
    2. Create a Submission within that scope.
    3. For each resolution request: upsert Source Identity, check for existing Binding.
    4. Bind all outcomes into a single Binding Set.
       - Provider-owned entities: auto-confirm.
       - Shared metadata entities: set is left in ``proposed`` state.

    Idempotent: submitting the same entities within the same scope always produces
    the same Source Identity records and, if already bound, the same Tracked Identity
    UUIDs (FR-12, FR-13).
    """
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
        outcome = await service.resolve_identity(
            scope_uuid=scope.scope_uuid,
            request=req,
            submission_uuid=submission.submission_uuid,
            created_by=body.created_by,
        )
        outcomes.append(outcome)

    binding_set = await service.bind(
        submission_uuid=submission.submission_uuid,
        outcomes=outcomes,
        created_by=body.created_by,
    )

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
)
async def get_binding_set(
    binding_set_uuid: UUID,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> BindingSetResponse:
    """Return the current state of a Binding Set."""
    result = await service.get_binding_set(binding_set_uuid)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Binding set {binding_set_uuid} not found")
    return result


@identity_router.post(
    "/binding-sets/{binding_set_uuid}/confirm",
    response_model=BindingSetResponse,
    summary="Confirm a proposed binding set",
)
async def confirm_binding_set(
    binding_set_uuid: UUID,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> BindingSetResponse:
    """Manually confirm a Binding Set that was left in ``proposed`` state.

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
)
async def associate_change_request(
    binding_set_uuid: UUID,
    body: AssociateChangeRequestBody,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> BindingSetResponse:
    """Record a Sqitch Change Request name against a confirmed Binding Set (FR-25, FR-27)."""
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
)
async def detect_change(
    body: ChangeDetectionRequest,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> ChangeDetectionResult:
    """Compare an incoming content hash against the stored hash (FR-24).

    Returns ``insert``, ``update``, or ``skip``.
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
