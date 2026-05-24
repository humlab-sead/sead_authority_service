"""Unit tests for SIMS domain models and types."""

from datetime import datetime, timezone
from uuid import uuid4

from src.identity.models import (
    Binding,
    BindingSet,
    ChangeDetectionResult,
    IdentitySignal,
    RejectDiagnostics,
    ResolutionOutcome,
    ResolutionRequest,
    SourceIdentity,
    SourceIdentityKey,
    SourceScope,
    Submission,
    TrackedIdentity,
)
from src.identity.types import (
    BindingMethod,
    BindingSetState,
    ChangeOutcome,
    IdentityType,
    SubmissionStatus,
    TrackedIdentityState,
)

NOW = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)


class TestTypes:
    def test_identity_type_values(self):
        assert IdentityType.UUID == "uuid"
        assert IdentityType.BUSINESS_KEY == "business_key"
        assert IdentityType.PROVIDER_KEY == "provider_key"
        assert IdentityType.AUTHORITY_KEY == "authority_key"

    def test_submission_status_values(self):
        assert SubmissionStatus.PENDING == "pending"
        assert SubmissionStatus.COMPLETED == "completed"
        assert SubmissionStatus.FAILED == "failed"

    def test_tracked_identity_state_values(self):
        assert TrackedIdentityState.ALLOCATED == "allocated"
        assert TrackedIdentityState.PENDING_MATERIALIZATION == "pending_materialization"
        assert TrackedIdentityState.MATERIALIZED == "materialized"
        assert TrackedIdentityState.INVALIDATED == "invalidated"

    def test_binding_set_state_values(self):
        assert BindingSetState.PROPOSED == "proposed"
        assert BindingSetState.CONFIRMED == "confirmed"
        assert BindingSetState.REJECTED == "rejected"
        assert BindingSetState.SUPERSEDED == "superseded"
        assert BindingSetState.INVALIDATED == "invalidated"

    def test_binding_method_values(self):
        assert BindingMethod.EXACT_MATCH == "exact_match"
        assert BindingMethod.BUSINESS_KEY == "business_key"
        assert BindingMethod.UUID_ACCEPTED == "uuid_accepted"
        assert BindingMethod.UUID_MAPPED == "uuid_mapped"
        assert BindingMethod.MANUAL == "manual"
        assert BindingMethod.ALLOCATED == "allocated"

    def test_change_outcome_values(self):
        assert ChangeOutcome.INSERT == "insert"
        assert ChangeOutcome.UPDATE == "update"
        assert ChangeOutcome.SKIP == "skip"


class TestSourceScope:
    def test_minimal_construction(self):
        scope = SourceScope(scope_uuid=uuid4(), scope_name="test://scope", created_at=NOW)
        assert scope.parent_scope_uuid is None
        assert scope.description is None

    def test_hierarchical_scope(self):
        parent = uuid4()
        scope = SourceScope(
            scope_uuid=uuid4(),
            scope_name="test://child",
            parent_scope_uuid=parent,
            description="child scope",
            created_at=NOW,
        )
        assert scope.parent_scope_uuid == parent


class TestSubmission:
    def test_defaults(self):
        sub = Submission(
            submission_uuid=uuid4(),
            scope_uuid=uuid4(),
            submission_name="batch-001",
            created_at=NOW,
        )
        assert sub.status == SubmissionStatus.PENDING
        assert sub.completed_at is None

    def test_completed_submission(self):
        sub = Submission(
            submission_uuid=uuid4(),
            scope_uuid=uuid4(),
            submission_name="batch-001",
            status=SubmissionStatus.COMPLETED,
            created_at=NOW,
            completed_at=NOW,
        )
        assert sub.status == SubmissionStatus.COMPLETED
        assert sub.completed_at == NOW


class TestSourceIdentity:
    def test_construction(self):
        si = SourceIdentity(
            source_identity_uuid=uuid4(),
            scope_uuid=uuid4(),
            entity_type="site",
            created_at=NOW,
        )
        assert si.keys == []
        assert si.created_by is None

    def test_with_keys(self):
        si_uuid = uuid4()
        key = SourceIdentityKey(
            key_uuid=uuid4(),
            source_identity_uuid=si_uuid,
            key_type=IdentityType.BUSINESS_KEY,
            key_value="site_name=Nordic Site",
        )
        si = SourceIdentity(
            source_identity_uuid=si_uuid,
            scope_uuid=uuid4(),
            entity_type="site",
            created_at=NOW,
            keys=[key],
        )
        assert len(si.keys) == 1
        assert si.keys[0].key_value == "site_name=Nordic Site"
        assert si.keys[0].key_type == IdentityType.BUSINESS_KEY


class TestTrackedIdentity:
    def test_defaults(self):
        ti = TrackedIdentity(
            tracked_identity_uuid=uuid4(),
            entity_type="site",
            created_at=NOW,
        )
        assert ti.lifecycle_state == TrackedIdentityState.ALLOCATED
        assert ti.sead_internal_id is None
        assert ti.content_hash is None

    def test_materialized(self):
        ti = TrackedIdentity(
            tracked_identity_uuid=uuid4(),
            entity_type="site",
            sead_internal_id=4321,
            lifecycle_state=TrackedIdentityState.MATERIALIZED,
            content_hash="abc123",
            created_at=NOW,
            materialized_at=NOW,
        )
        assert ti.sead_internal_id == 4321
        assert ti.content_hash == "abc123"


class TestBindingSet:
    def test_defaults(self):
        bs = BindingSet(binding_set_uuid=uuid4(), created_at=NOW)
        assert bs.lifecycle_state == BindingSetState.PROPOSED
        assert bs.submission_uuid is None
        assert bs.change_request_name is None

    def test_confirmed_with_cr(self):
        bs = BindingSet(
            binding_set_uuid=uuid4(),
            submission_uuid=uuid4(),
            lifecycle_state=BindingSetState.CONFIRMED,
            change_request_name="deploy/2026-04-04-identity-pilot",
            created_at=NOW,
            confirmed_at=NOW,
        )
        assert bs.lifecycle_state == BindingSetState.CONFIRMED
        assert bs.change_request_name is not None
        assert bs.change_request_name.startswith("deploy/")


class TestBinding:
    def test_construction(self):
        b = Binding(
            binding_uuid=uuid4(),
            binding_set_uuid=uuid4(),
            source_identity_uuid=uuid4(),
            tracked_identity_uuid=uuid4(),
            method=BindingMethod.BUSINESS_KEY,
        )
        assert b.provenance is None

    def test_with_provenance(self):
        b: Binding = Binding(
            binding_uuid=uuid4(),
            binding_set_uuid=uuid4(),
            source_identity_uuid=uuid4(),
            tracked_identity_uuid=uuid4(),
            method=BindingMethod.EXACT_MATCH,
            provenance={"match_score": 1.0, "field": "site_uuid"},
        )
        assert b.provenance is not None
        assert b.provenance["match_score"] == 1.0


class TestResolutionRequest:
    def test_construction(self):
        req = ResolutionRequest(
            entity_type="site",
            primary_signal=IdentitySignal(
                identity_type=IdentityType.BUSINESS_KEY,
                identity_value="site_name=Nordic Site",
            ),
        )
        assert req.additional_signals == []

    def test_with_additional_signals(self):
        req = ResolutionRequest(
            entity_type="location",
            primary_signal=IdentitySignal(
                identity_type=IdentityType.BUSINESS_KEY,
                identity_value="location_name=Sweden",
            ),
            additional_signals=[
                IdentitySignal(
                    identity_type=IdentityType.AUTHORITY_KEY,
                    identity_value="geonames:2661886",
                )
            ],
        )
        assert len(req.additional_signals) == 1


class TestResolutionOutcome:
    def test_defaults(self):
        outcome = ResolutionOutcome(
            source_identity_uuid=uuid4(),
            entity_type="site",
            outcome="new",
        )

        assert outcome.tracked_identity_uuid is None
        assert outcome.target_id is None

    def test_with_target_id(self):
        outcome = ResolutionOutcome(
            source_identity_uuid=uuid4(),
            entity_type="site",
            outcome="matched",
            tracked_identity_uuid=uuid4(),
            target_id=4321,
        )

        assert outcome.target_id == 4321


class TestChangeDetection:
    def test_insert_outcome(self):
        result = ChangeDetectionResult(
            tracked_identity_uuid=uuid4(),
            outcome=ChangeOutcome.INSERT,
            previous_hash=None,
        )
        assert result.outcome == ChangeOutcome.INSERT

    def test_update_outcome(self):
        result = ChangeDetectionResult(
            tracked_identity_uuid=uuid4(),
            outcome=ChangeOutcome.UPDATE,
            previous_hash="oldhash",
        )
        assert result.previous_hash == "oldhash"

    def test_skip_outcome(self):
        result = ChangeDetectionResult(
            tracked_identity_uuid=uuid4(),
            outcome=ChangeOutcome.SKIP,
            previous_hash="samehash",
        )
        assert result.outcome == ChangeOutcome.SKIP


class TestRejectDiagnostics:
    def test_construction(self):
        diag = RejectDiagnostics(
            entity_type="method",
            identity_value="AMS Dating",
            identity_type=IdentityType.BUSINESS_KEY,
            reason="No matching SEAD method found for shared metadata entity.",
        )
        assert diag.suggestions == []

    def test_with_suggestions(self):
        diag = RejectDiagnostics(
            entity_type="method",
            identity_value="AMS Dating",
            identity_type=IdentityType.BUSINESS_KEY,
            reason="No matching SEAD method found.",
            suggestions=["AMS", "Radiocarbon dating (AMS)"],
        )
        assert len(diag.suggestions) == 2
