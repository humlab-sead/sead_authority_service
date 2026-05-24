"""SIMS identity management module.

Provides identity policy, UUID allocation, and evidence tracing
for tracked SEAD entities. Runtime implementation of the SIMS design
(see docs/sims/ for design documentation).

Submodules:
- types:      Enums — IdentityType, SubmissionStatus, TrackedIdentityState, BindingSetState, etc.
- models:     Domain models and request/response DTOs
- repository: Async database repositories (one per table)
- policy:     Identity policy engine (per-entity-type rules)
- service:    Core operations — resolve, bind, confirm, detect_change, associate_cr
"""

from src.identity.models import (
    Binding,
    BindingSet,
    BindingSetResponse,
    BindRequest,
    ChangeDetectionRequest,
    ChangeDetectionResult,
    IdentitySignal,
    RejectDiagnostics,
    ResolutionOutcome,
    ResolutionRequest,
    SourceIdentity,
    SourceScope,
    Submission,
    TrackedIdentity,
)
from src.identity.policy import EntityPolicy, IdentityPolicy
from src.identity.repository import (
    BindingRepository,
    BindingSetRepository,
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
    "IdentitySignal",
    "RejectDiagnostics",
    "ResolutionOutcome",
    "ResolutionRequest",
    # policy
    "EntityPolicy",
    "IdentityPolicy",
    # repositories
    "BindingRepository",
    "BindingSetRepository",
    "SourceIdentityRepository",
    "SourceScopeRepository",
    "SubmissionRepository",
    "TrackedIdentityRepository",
    # service
    "IdentityService",
]
