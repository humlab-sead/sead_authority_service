"""Domain models for the SIMS identity module.

Maps directly to the CM concepts and storage structures defined in:
  docs/sims/CONCEPTUAL_MODEL.md
  docs/sims/IMPLEMENTATION_VIEW.md § Storage Design
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.identity.types import (
    BindingMethod,
    BindingSetState,
    ChangeOutcome,
    IdentityType,
    SubmissionStatus,
    TrackedIdentityState,
)


# ---------------------------------------------------------------------------
# Storage models — mirror the database tables
# ---------------------------------------------------------------------------


class SourceScope(BaseModel):
    """External namespace within which Source Identities are unique."""

    scope_uuid: UUID
    scope_name: str
    parent_scope_uuid: UUID | None = None
    description: str | None = None
    created_at: datetime
    created_by: str | None = None


class Submission(BaseModel):
    """A delivered batch or ingest event within a single Source Scope."""

    submission_uuid: UUID
    scope_uuid: UUID
    submission_name: str
    status: SubmissionStatus = SubmissionStatus.PENDING
    created_at: datetime
    created_by: str | None = None
    completed_at: datetime | None = None


class SourceIdentity(BaseModel):
    """Persistent identity for a domain entity as expressed within a Source Scope.

    Carries all identity signals supplied by the provider. Uniqueness is enforced
    per (scope_uuid, entity_type, identity_type, identity_value).
    """

    source_identity_uuid: UUID
    scope_uuid: UUID
    entity_type: str
    identity_type: IdentityType
    identity_value: str
    identity_signals: dict | None = None
    created_at: datetime
    created_by: str | None = None


class TrackedIdentity(BaseModel):
    """SEAD-side identity anchor for a domain entity.

    tracked_identity_uuid IS the SEAD universal identity (FR-1).
    sead_internal_id maps to the relational PK once materialized (FR-2).
    content_hash supports aggregate-level change detection (FR-24).
    """

    tracked_identity_uuid: UUID
    entity_type: str
    sead_internal_id: int | None = None
    content_hash: str | None = None
    lifecycle_state: TrackedIdentityState = TrackedIdentityState.ALLOCATED
    created_at: datetime
    created_by: str | None = None
    materialized_at: datetime | None = None


class BindingSet(BaseModel):
    """Atomic batch of Bindings. The governance unit for lifecycle and Change Request reference.

    All Bindings within a set are confirmed or rejected together (FR-26).
    """

    binding_set_uuid: UUID
    submission_uuid: UUID | None = None
    lifecycle_state: BindingSetState = BindingSetState.PROPOSED
    change_request_name: str | None = None
    created_at: datetime
    created_by: str | None = None
    confirmed_at: datetime | None = None


class Binding(BaseModel):
    """One source-to-tracked identity correspondence within a Binding Set."""

    binding_uuid: UUID
    binding_set_uuid: UUID
    source_identity_uuid: UUID
    tracked_identity_uuid: UUID
    method: BindingMethod
    provenance: dict | None = None


# ---------------------------------------------------------------------------
# Request / response DTOs — used by service operations and API endpoints
# ---------------------------------------------------------------------------


class IdentitySignal(BaseModel):
    """An identity signal submitted for resolution."""

    identity_type: IdentityType
    identity_value: str
    signals: dict | None = Field(
        default=None,
        description="Additional evidence: authority keys, alternative identifiers.",
    )


class ResolutionRequest(BaseModel):
    """Input to the Resolve Identity operation.

    Represents one domain entity submitted for identity resolution within a scope.
    """

    entity_type: str
    primary_signal: IdentitySignal
    additional_signals: list[IdentitySignal] = Field(default_factory=list)


class ResolutionOutcome(BaseModel):
    """Output of a single entity resolution within a Resolve call."""

    source_identity_uuid: UUID
    entity_type: str
    outcome: str = Field(description="'matched' or 'new'")
    tracked_identity_uuid: UUID | None = Field(
        default=None,
        description="Set when outcome is 'matched'. For 'new', set after Bind.",
    )


class BindRequest(BaseModel):
    """Input to the Bind operation: resolution outcomes to package into a Binding Set."""

    submission_uuid: UUID
    resolution_outcomes: list[ResolutionOutcome]


class BindingSetResponse(BaseModel):
    """API response representing a Binding Set and its current state."""

    binding_set_uuid: UUID
    submission_uuid: UUID | None
    lifecycle_state: BindingSetState
    change_request_name: str | None
    binding_count: int
    created_at: datetime
    confirmed_at: datetime | None = None


class ChangeDetectionRequest(BaseModel):
    """Input to the Detect Change operation."""

    tracked_identity_uuid: UUID
    content_hash: str = Field(description="Deterministic aggregate content hash computed by the submitting system.")


class ChangeDetectionResult(BaseModel):
    """Output of the Detect Change operation."""

    tracked_identity_uuid: UUID
    outcome: ChangeOutcome
    previous_hash: str | None = Field(default=None, description="The previously stored hash, if any.")


class RejectDiagnostics(BaseModel):
    """Diagnostic payload returned when a submission is rejected due to unmatched entities."""

    entity_type: str
    identity_value: str
    identity_type: IdentityType
    reason: str
    suggestions: list[str] = Field(default_factory=list, description="Candidate matches for manual review.")
