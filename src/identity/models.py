"""Domain models for the SIMS identity module.

Maps directly to the CM concepts and storage structures defined in:
  docs/SIMS/design/CONCEPTUAL_MODEL.md
  docs/SIMS/design/IMPLEMENTATION_VIEW.md § Storage Design
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
    scope_name: str = Field(description="Unique URI-style identifier, e.g. 'sead://admin' or 'provider://gbif'.")
    parent_scope_uuid: UUID | None = Field(default=None, description="Parent scope for hierarchical namespacing; None for root scopes.")
    description: str | None = None
    created_at: datetime
    created_by: str | None = None


class Submission(BaseModel):
    """A delivered batch or ingest event within a single Source Scope."""

    submission_uuid: UUID
    scope_uuid: UUID
    submission_name: str = Field(description="Human-readable label for the batch or ingest event.")
    status: SubmissionStatus = Field(default=SubmissionStatus.PENDING, description="Lifecycle state: PENDING → COMPLETED or FAILED.")
    created_at: datetime
    created_by: str | None = None
    completed_at: datetime | None = Field(default=None, description="Set when status transitions to COMPLETED or FAILED.")


class SourceIdentity(BaseModel):
    """Header record: provider's claim about one domain entity within a Source Scope.

    Identity evidence (keys) live in SourceIdentityKey rows linked by source_identity_uuid.
    The ``keys`` field is populated when the identity is fetched together with its keys;
    it is empty for bare header lookups.
    """

    source_identity_uuid: UUID
    scope_uuid: UUID
    entity_type: str = Field(description="SEAD entity type, e.g. 'site', 'sample_group', 'taxa_tree_master'.")
    created_at: datetime
    created_by: str | None = None
    keys: list["SourceIdentityKey"] = Field(default_factory=list, description="Identity evidence keys; empty for bare header lookups, populated by repository joins.")


class SourceIdentityKey(BaseModel):
    """One identity key associated with a Source Identity.

    A source identity may carry multiple key types (e.g. a UUID and a business key).
    Uniqueness is enforced per (source_identity_uuid, key_type).
    """

    key_uuid: UUID
    source_identity_uuid: UUID
    key_type: IdentityType = Field(description="Discriminator: 'uuid', 'business_key', 'provider_key', or 'authority_key'.")
    key_value: str = Field(description="Serialised key value, e.g. 'site_name=Nordic Site' or a UUID string.")


class TrackedIdentity(BaseModel):
    """SEAD-side identity anchor for a domain entity.

    tracked_identity_uuid IS the SEAD universal identity (FR-1).
    sead_internal_id maps to the relational PK once materialized (FR-2).
    content_hash supports aggregate-level change detection (FR-24).
    """

    tracked_identity_uuid: UUID = Field(description="Universal SEAD identity UUID (FR-1). Stable across schema migrations.")
    entity_type: str = Field(description="SEAD entity type, e.g. 'site', 'sample_group'.")
    sead_internal_id: int | None = Field(default=None, description="Relational PK in the target SEAD table; set when lifecycle_state is MATERIALIZED (FR-2).")
    content_hash: str | None = Field(default=None, description="Deterministic aggregate content hash for change detection (FR-24).")
    lifecycle_state: TrackedIdentityState = Field(default=TrackedIdentityState.ALLOCATED, description="ALLOCATED → MATERIALIZED → RETIRED lifecycle.")
    created_at: datetime
    created_by: str | None = None
    materialized_at: datetime | None = Field(default=None, description="Timestamp when sead_internal_id was first assigned.")


class BindingSet(BaseModel):
    """Atomic batch of Bindings. The governance unit for lifecycle and Change Request reference.

    All Bindings within a set are confirmed or rejected together (FR-26).
    """

    binding_set_uuid: UUID
    submission_uuid: UUID | None = None
    lifecycle_state: BindingSetState = Field(default=BindingSetState.PROPOSED, description="PROPOSED → CONFIRMED governance lifecycle (FR-26).")
    change_request_name: str | None = Field(default=None, description="Sqitch change request name linking this set to a schema migration (FR-25).")
    created_at: datetime
    created_by: str | None = None
    confirmed_at: datetime | None = Field(default=None, description="Timestamp of lifecycle transition to CONFIRMED.")


class Binding(BaseModel):
    """One source-to-tracked identity correspondence within a Binding Set."""

    binding_uuid: UUID
    binding_set_uuid: UUID
    source_identity_uuid: UUID
    tracked_identity_uuid: UUID
    method: BindingMethod = Field(description="How the correspondence was established: UUID match, business key, exact match, or allocation.")
    provenance: dict | None = Field(default=None, description="Audit evidence: match score, matched field, applied policy, etc.")


# ---------------------------------------------------------------------------
# Request / response DTOs — used by service operations and API endpoints
# ---------------------------------------------------------------------------


class IdentitySignal(BaseModel):
    """An identity signal submitted for resolution."""

    identity_type: IdentityType = Field(description="Key type discriminator driving lookup strategy.")
    identity_value: str = Field(description="Serialised key value, e.g. 'site_name=Nordic Site'.")
    signals: dict | None = Field(
        default=None,
        description="Additional evidence: authority keys, alternative identifiers.",
    )


class ResolutionRequest(BaseModel):
    """Input to the Resolve Identity operation.

    Represents one domain entity submitted for identity resolution within a scope.
    """

    entity_type: str = Field(description="SEAD entity type, e.g. 'site', 'taxa_tree_master'.")
    primary_signal: IdentitySignal = Field(description="The main identity key used for idempotency lookup (FR-12).")
    additional_signals: list[IdentitySignal] = Field(default_factory=list, description="Optional supplementary keys that are also stored, e.g. an authority UUID alongside a business key.")


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
    resolution_outcomes: list[ResolutionOutcome] = Field(description="Outcomes from resolve_identity calls to package into a single Binding Set.")


class BindingSetResponse(BaseModel):
    """API response representing a Binding Set and its current state."""

    binding_set_uuid: UUID
    submission_uuid: UUID | None
    lifecycle_state: BindingSetState
    change_request_name: str | None
    binding_count: int = Field(description="Number of source↔tracked Binding rows within this set.")
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
