"""SIMS Identity API router.

All endpoints are prefixed with ``/identity`` (registered in main.py).

Endpoints:
  POST   /identity/resolve                                         Resolve + bind a batch of source identities
  GET    /identity/binding-sets/{binding_set_uuid}                 Get binding set status
  POST   /identity/binding-sets/{binding_set_uuid}/confirm         Confirm a proposed binding set
  POST   /identity/binding-sets/{binding_set_uuid}/change-request  Associate a CR name
  POST   /identity/detect-change                                   Content-hash change detection
  GET    /identity/scopes                                          List known source scopes
  POST   /identity/scope-contracts                                 Register provider-scope business-key contracts
  GET    /identity/scope-contracts                                 List provider-scope business-key contracts
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.configuration import get_config_provider, setup_config_store
from src.configuration.interface import ConfigLike
from src.identity.contracts import (
    ContractAuthorizationError,
    ContractRegistrationPolicy,
    IdentityContractConflict,
    IdentityContractRequired,
)
from src.identity.models import (
    BindingSetResponse,
    ChangeDetectionRequest,
    ChangeDetectionResult,
    EntityKeyContract,
    RegisterScopeContractsRequest,
    ResolutionOutcome,
    ResolutionRequest,
    ScopeContractRegistration,
    SourceScope,
)
from src.identity.policy import CAPABILITY_VERSION, IdentityPolicy
from src.identity.service import IdentityBatchConflict, IdentityBindingConflict, IdentityService

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


def get_contract_registration_policy() -> ContractRegistrationPolicy:
    """FastAPI dependency — returns the configured contract registration allowlist."""
    return ContractRegistrationPolicy.from_config()


# ---------------------------------------------------------------------------
# Request / response schemas specific to the API layer
# ---------------------------------------------------------------------------


class ResolveRequest(BaseModel):
    """Request body for POST /identity/resolve."""

    scope_name: str = Field(description="Source Scope name, e.g. 'sead://reconciliation' or a provider URI.")
    run_id: str = Field(description="Stable idempotency key for this batch, scoped to the source scope. Reused across retries.")
    submission_name: str = Field(description="Human-readable name for this submission batch.")
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
            "description": (
                "Approved aggregate ID conflicts, a proposed binding is unresolved, " "or the run key was reused with a different payload"
            )
        }
    },
)
async def resolve(
    body: ResolveRequest,
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
    policy: IdentityPolicy = Depends(get_identity_policy),
) -> ResolveResponse:
    """Resolve and bind a batch of domain entities atomically.

    The run key ``(scope_name, run_id)`` makes the batch idempotent:
    1. Reject unconfigured entity types and unsupported operations.
    2. Replay the stored result when the same run key and payload fingerprint recur.
    3. Reject a reused run key whose payload differs.
    4. Otherwise resolve and bind the batch in one transaction and persist the result.

    Idempotent: submitting the same entities within the same scope and run always
    produces the same Source Identity records and, if already bound, the same
    Tracked Identity UUIDs (FR-12, FR-13).
    """
    for req in body.requests:
        _require_supported_operation(policy, req)

    try:
        result = await service.resolve_batch(
            scope_name=body.scope_name,
            submission_name=body.submission_name,
            run_id=body.run_id,
            requests=body.requests,
            created_by=body.created_by,
        )
    except IdentityBatchConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IdentityBindingConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except IdentityContractRequired as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ResolveResponse(
        submission_uuid=result.submission_uuid,
        scope_uuid=result.scope_uuid,
        binding_set=result.binding_set,
        outcomes=result.outcomes,
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


@identity_router.post(
    "/scope-contracts",
    response_model=ScopeContractRegistration,
    status_code=status.HTTP_200_OK,
    summary="Register provider-scope business-key contracts",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Caller is not authorized for this provider scope"},
        status.HTTP_409_CONFLICT: {"description": "A submitted key list differs from the registered key list"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The scope is not a provider scope or a declaration is invalid"},
    },
)
async def register_scope_contracts(
    body: RegisterScopeContractsRequest,
    x_sims_caller: str | None = Header(default=None, alias="X-SIMS-Caller"),
    x_sims_caller_token: str | None = Header(default=None, alias="X-SIMS-Caller-Token"),
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
    registration_policy: ContractRegistrationPolicy = Depends(get_contract_registration_policy),
) -> ScopeContractRegistration:
    """Register the ordered business-key list of each entity type in one provider scope.

    The caller must be listed in ``identity.contract_registration.callers`` and
    must send the matching token in ``X-SIMS-Caller-Token``. A caller can only
    register scopes that start with one of its configured ``scope_prefixes``.

    The operation is idempotent: an exact ordered match returns ``state``
    ``existing``. A different key list or key order returns HTTP 409 with the
    registered and submitted lists, and writes nothing.
    """
    try:
        caller_name: str = registration_policy.authorize(x_sims_caller, x_sims_caller_token, body.scope_name)
    except ContractAuthorizationError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        return await service.register_scope_contracts(
            scope_name=body.scope_name,
            entities=body.entities,
            created_by=body.created_by or caller_name,
        )
    except IdentityContractConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(exc),
                "conflicts": [conflict.model_dump(mode="json") for conflict in exc.conflicts],
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@identity_router.get(
    "/scope-contracts",
    response_model=list[EntityKeyContract],
    summary="List provider-scope business-key contracts",
)
async def list_scope_contracts(
    scope_name: str = Query(description="Provider scope name, e.g. 'provider://gbif/occurrence'."),
    _config: ConfigLike = Depends(get_config_dep),
    service: IdentityService = Depends(get_identity_service),
) -> list[EntityKeyContract]:
    """Return the registered contracts for one scope name.

    An unknown scope returns an empty list.
    """
    return await service.list_scope_contracts(scope_name)
