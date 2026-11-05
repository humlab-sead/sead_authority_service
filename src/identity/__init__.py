"""SIMS identity management module.

Provides identity policy, UUID allocation, and evidence tracing
for tracked SEAD entities. Runtime implementation of the SIMS design
(see docs/sims/ for design documentation).

Submodules:
- types:      Enums — IdentityType, SubmissionStatus, TrackedIdentityState, BindingSetState, etc.
- models:     Domain models and request/response DTOs
- repository: Async database repositories (one per table)
- policy:     Identity policy engine (per-entity-type rules)
- contracts:  Provider-scope business-key contracts and registration authorization
- service:    Core operations — resolve, bind, confirm, detect_change, associate_cr
"""

from src.identity.contracts import (
    ContractAuthorizationError,
    ContractRegistrationPolicy,
    IdentityContractConflict,
    IdentityContractRequired,
    is_provider_scope,
)
from src.identity.models import (
    Binding,
    BindingSet,
    BindingSetResponse,
    BindRequest,
    ChangeDetectionRequest,
    ChangeDetectionResult,
    EntityContractConflict,
    EntityContractDeclaration,
    EntityContractState,
    EntityKeyContract,
    IdentitySignal,
    RegisterScopeContractsRequest,
    RejectDiagnostics,
    ResolutionOutcome,
    ResolutionRequest,
    ScopeContractRegistration,
    SourceIdentity,
    SourceScope,
    Submission,
    TrackedIdentity,
)
from src.identity.policy import EntityPolicy, IdentityPolicy
from src.identity.repository import (
    BindingRepository,
    BindingSetRepository,
    ScopeEntityContractRepository,
    SourceIdentityRepository,
    SourceScopeRepository,
    SubmissionRepository,
    TrackedIdentityRepository,
)
from src.identity.service import IdentityService
from src.identity.types import (
    BindingMethod,
    BindingSetState,
    ChangeOutcome,
    IdentityType,
    SubmissionStatus,
    TrackedIdentityState,
)

__all__ = [
    # types
    "BindingMethod",
    "BindingSetState",
    "ChangeOutcome",
    "IdentityType",
    "SubmissionStatus",
    "TrackedIdentityState",
    # storage models
    "Binding",
    "BindingSet",
    "SourceIdentity",
    "SourceScope",
    "Submission",
    "TrackedIdentity",
    # DTOs
    "BindingSetResponse",
    "BindRequest",
    "ChangeDetectionRequest",
    "ChangeDetectionResult",
    "EntityContractConflict",
    "EntityContractDeclaration",
    "EntityContractState",
    "EntityKeyContract",
    "IdentitySignal",
    "RegisterScopeContractsRequest",
    "RejectDiagnostics",
    "ResolutionOutcome",
    "ResolutionRequest",
    "ScopeContractRegistration",
    # contracts
    "ContractAuthorizationError",
    "ContractRegistrationPolicy",
    "IdentityContractConflict",
    "IdentityContractRequired",
    "is_provider_scope",
    # policy
    "EntityPolicy",
    "IdentityPolicy",
    # repositories
    "BindingRepository",
    "BindingSetRepository",
    "ScopeEntityContractRepository",
    "SourceIdentityRepository",
    "SourceScopeRepository",
    "SubmissionRepository",
    "TrackedIdentityRepository",
    # service
    "IdentityService",
]
