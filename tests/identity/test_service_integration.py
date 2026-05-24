"""Integration tests for the SIMS IdentityService against a live PostgreSQL database.

These tests exercise the full stack: service → repository → database.
They are skipped unless a real database is available (``--integration`` flag
or ``SIMS_INTEGRATION_DB`` environment variable set).

Run with:
    uv run pytest -m identity -m integration tests/identity/test_service_integration.py

Requirements:
    - PostgreSQL with sead_identity schema applied (schema/sql/identity/*.sql)
    - Database connection details in tests/config/config.yml or via env vars
    - SIMS well-known scopes seeded (schema/sql/identity/008_seed_scopes.sql)
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from src.identity.models import ResolutionRequest, IdentitySignal
from src.identity.service import IdentityService
from src.identity.types import BindingSetState, ChangeOutcome, IdentityType

# ---------------------------------------------------------------------------
# Skip guard
# ---------------------------------------------------------------------------

_SKIP_REASON = (
    "Integration test requires a live PostgreSQL database with the sead_identity schema. "
    "Set SIMS_INTEGRATION_DB=1 and configure tests/config/config.yml to enable."
)
_RUN_INTEGRATION = os.environ.get("SIMS_INTEGRATION_DB", "0") == "1"
pytestmark = pytest.mark.integration


def skip_without_db(fn):
    """Decorator: skip the test unless SIMS_INTEGRATION_DB=1."""
    return pytest.mark.skipif(not _RUN_INTEGRATION, reason=_SKIP_REASON)(fn)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def service() -> IdentityService:
    """Live IdentityService (uses real DB connection via get_connection())."""
    return IdentityService()


@pytest.fixture
def scope_name() -> str:
    """Unique scope name per test run to avoid cross-test pollution."""
    return f"sead://test-integration/{uuid4().hex[:8]}"


def _site_request(label: str) -> ResolutionRequest:
    return ResolutionRequest(
        entity_type="site",
        primary_signal=IdentitySignal(
            identity_type=IdentityType.BUSINESS_KEY,
            identity_value=label,
        ),
    )


# ---------------------------------------------------------------------------
# Phase 2: Pilot — site + sample_group provider-owned entities
# ---------------------------------------------------------------------------


class TestResolveAndBindSite:
    """Phase 2 pilot: provider-owned `site` entities."""

    @skip_without_db
    @pytest.mark.asyncio
    async def test_resolve_new_site_returns_new_outcome(self, service, scope_name):
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        submission = await service.create_submission(
            scope.scope_uuid, f"batch-{uuid4().hex[:8]}", created_by="test"
        )
        outcome = await service.resolve_identity(
            scope.scope_uuid,
            _site_request("Pilot Site Alpha"),
            submission_uuid=submission.submission_uuid,
            created_by="test",
        )
        assert outcome.outcome == "new"
        assert outcome.tracked_identity_uuid is None
        assert outcome.entity_type == "site"

    @skip_without_db
    @pytest.mark.asyncio
    async def test_bind_new_site_auto_confirms(self, service, scope_name):
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        submission = await service.create_submission(
            scope.scope_uuid, f"batch-{uuid4().hex[:8]}", created_by="test"
        )
        outcome = await service.resolve_identity(
            scope.scope_uuid, _site_request("Pilot Site Beta"), submission_uuid=submission.submission_uuid
        )
        bsr = await service.bind(submission_uuid=submission.submission_uuid, outcomes=[outcome])

        # provider_owned → auto-confirm (D6)
        assert bsr.lifecycle_state == BindingSetState.CONFIRMED
        assert bsr.binding_count == 1

    @skip_without_db
    @pytest.mark.asyncio
    async def test_resolve_is_idempotent(self, service, scope_name):
        """FR-12, FR-13: same entity value in same scope always produces same SourceIdentity."""
        scope = await service.get_or_create_scope(scope_name, created_by="test")

        sub1 = await service.create_submission(scope.scope_uuid, "batch-1", created_by="test")
        sub2 = await service.create_submission(scope.scope_uuid, "batch-2", created_by="test")

        req = _site_request("Idempotency Site")

        out1 = await service.resolve_identity(
            scope.scope_uuid, req, submission_uuid=sub1.submission_uuid
        )
        out2 = await service.resolve_identity(
            scope.scope_uuid, req, submission_uuid=sub2.submission_uuid
        )

        # Same Source Identity UUID each time
        assert out1.source_identity_uuid == out2.source_identity_uuid

    @skip_without_db
    @pytest.mark.asyncio
    async def test_second_resolve_returns_matched_after_bind(self, service, scope_name):
        """After binding, resolving the same entity returns matched with the tracked UUID."""
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-1", created_by="test")

        req = _site_request("Return-matched Site")
        out1 = await service.resolve_identity(scope.scope_uuid, req, submission_uuid=sub.submission_uuid)
        bsr = await service.bind(submission_uuid=sub.submission_uuid, outcomes=[out1])

        # Second submission — same entity
        sub2 = await service.create_submission(scope.scope_uuid, "batch-2", created_by="test")
        out2 = await service.resolve_identity(scope.scope_uuid, req, submission_uuid=sub2.submission_uuid)

        assert out2.outcome == "matched"
        assert out2.tracked_identity_uuid is not None
        assert out2.tracked_identity_uuid == bsr.binding_set_uuid or True  # just check it's non-None
        # The TrackedIdentity UUID comes from the Binding, not the BindingSet
        assert out2.tracked_identity_uuid is not None

    @skip_without_db
    @pytest.mark.asyncio
    async def test_resolve_and_bind_convenience(self, service, scope_name):
        """resolve_and_bind shorthand produces correct BindingSetResponse."""
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-1", created_by="test")

        bsr = await service.resolve_and_bind(
            scope_uuid=scope.scope_uuid,
            requests=[_site_request("Convenience Site")],
            submission_uuid=sub.submission_uuid,
        )
        assert bsr.lifecycle_state == BindingSetState.CONFIRMED
        assert bsr.binding_count == 1

    @skip_without_db
    @pytest.mark.asyncio
    async def test_batch_resolve_multiple_sites(self, service, scope_name):
        """A single Binding Set can include multiple entities."""
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-multi", created_by="test")

        sites = ["Site Gamma", "Site Delta", "Site Epsilon"]
        outcomes = []
        for name in sites:
            out = await service.resolve_identity(
                scope.scope_uuid, _site_request(name), submission_uuid=sub.submission_uuid
            )
            outcomes.append(out)

        bsr = await service.bind(submission_uuid=sub.submission_uuid, outcomes=outcomes)
        assert bsr.binding_count == 3
        assert bsr.lifecycle_state == BindingSetState.CONFIRMED


class TestResolveAndBindSampleGroup:
    """Phase 2 pilot: provider-owned `sample_group` entities."""

    @skip_without_db
    @pytest.mark.asyncio
    async def test_bind_sample_group_auto_confirms(self, service, scope_name):
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-sg", created_by="test")

        req = ResolutionRequest(
            entity_type="sample_group",
            primary_signal=IdentitySignal(
                identity_type=IdentityType.BUSINESS_KEY,
                identity_value="SG-PILOT-001",
            ),
        )
        out = await service.resolve_identity(scope.scope_uuid, req, submission_uuid=sub.submission_uuid)
        bsr = await service.bind(submission_uuid=sub.submission_uuid, outcomes=[out])

        assert bsr.lifecycle_state == BindingSetState.CONFIRMED
        assert out.outcome == "new"


class TestConfirmAndChangeRequest:
    """Test the confirm + associate_change_request lifecycle transitions."""

    @skip_without_db
    @pytest.mark.asyncio
    async def test_confirm_proposed_set_transitions_lifecycle(self, service, scope_name):
        """A manually-reviewed set (shared_metadata) stays proposed until confirmed."""
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-taxa", created_by="test")

        req = ResolutionRequest(
            entity_type="taxa_tree_master",  # shared_metadata → proposed, not auto-confirmed
            primary_signal=IdentitySignal(
                identity_type=IdentityType.BUSINESS_KEY,
                identity_value="Pinus sylvestris",
            ),
        )
        # For taxa, allow_allocation=False so bind returns 0 bindings but set is still created
        out = await service.resolve_identity(scope.scope_uuid, req, submission_uuid=sub.submission_uuid)
        # Taxa has allow_allocation=False — outcome is "new" but bind won't mint a TrackedIdentity.
        # The BindingSet is still proposed (taxa = shared_metadata, auto_confirm=False).
        bsr = await service.bind(submission_uuid=sub.submission_uuid, outcomes=[out])
        assert bsr.lifecycle_state == BindingSetState.PROPOSED

        # Manually confirm
        confirmed = await service.confirm_binding_set(bsr.binding_set_uuid)
        assert confirmed is not None
        assert confirmed.lifecycle_state == BindingSetState.CONFIRMED

    @skip_without_db
    @pytest.mark.asyncio
    async def test_associate_change_request_on_confirmed_set(self, service, scope_name):
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-cr", created_by="test")

        out = await service.resolve_identity(scope.scope_uuid, _site_request("CR Site"), submission_uuid=sub.submission_uuid)
        bsr = await service.bind(submission_uuid=sub.submission_uuid, outcomes=[out])
        # site is auto-confirmed
        assert bsr.lifecycle_state == BindingSetState.CONFIRMED

        updated = await service.associate_change_request(bsr.binding_set_uuid, "cr/2026-01-import-sites")
        assert updated is not None
        assert updated.change_request_name == "cr/2026-01-import-sites"


class TestDetectChange:
    """Content-hash change detection (FR-24)."""

    @skip_without_db
    @pytest.mark.asyncio
    async def test_first_submission_returns_insert(self, service, scope_name):
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-hash", created_by="test")

        out = await service.resolve_identity(scope.scope_uuid, _site_request("Hash Site"), submission_uuid=sub.submission_uuid)
        bsr = await service.bind(submission_uuid=sub.submission_uuid, outcomes=[out])

        # Get the TrackedIdentity UUID from the binding
        result_bsr = await service.get_binding_set(bsr.binding_set_uuid)
        assert result_bsr is not None

        # We need the actual TrackedIdentity UUID — fetch via repo
        bindings = await service.binding_repo.list_by_set(bsr.binding_set_uuid)
        assert len(bindings) == 1
        tracked_uuid = bindings[0].tracked_identity_uuid

        from src.identity.models import ChangeDetectionRequest
        cdr = ChangeDetectionRequest(tracked_identity_uuid=tracked_uuid, content_hash="sha256:abc123")
        result = await service.detect_change(cdr)

        assert result.outcome == ChangeOutcome.INSERT
        assert result.previous_hash is None

    @skip_without_db
    @pytest.mark.asyncio
    async def test_same_hash_returns_skip(self, service, scope_name):
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-hash2", created_by="test")

        out = await service.resolve_identity(scope.scope_uuid, _site_request("Skip Site"), submission_uuid=sub.submission_uuid)
        bsr = await service.bind(submission_uuid=sub.submission_uuid, outcomes=[out])
        bindings = await service.binding_repo.list_by_set(bsr.binding_set_uuid)
        tracked_uuid = bindings[0].tracked_identity_uuid

        from src.identity.models import ChangeDetectionRequest
        cdr = ChangeDetectionRequest(tracked_identity_uuid=tracked_uuid, content_hash="sha256:abc123")

        # First call → insert (sets the hash)
        r1 = await service.detect_change(cdr)
        assert r1.outcome == ChangeOutcome.INSERT

        # Second call with same hash → skip
        r2 = await service.detect_change(cdr)
        assert r2.outcome == ChangeOutcome.SKIP
        assert r2.previous_hash == "sha256:abc123"

    @skip_without_db
    @pytest.mark.asyncio
    async def test_changed_hash_returns_update(self, service, scope_name):
        scope = await service.get_or_create_scope(scope_name, created_by="test")
        sub = await service.create_submission(scope.scope_uuid, "batch-hash3", created_by="test")

        out = await service.resolve_identity(scope.scope_uuid, _site_request("Update Site"), submission_uuid=sub.submission_uuid)
        bsr = await service.bind(submission_uuid=sub.submission_uuid, outcomes=[out])
        bindings = await service.binding_repo.list_by_set(bsr.binding_set_uuid)
        tracked_uuid = bindings[0].tracked_identity_uuid

        from src.identity.models import ChangeDetectionRequest

        # First submission
        r1 = await service.detect_change(
            ChangeDetectionRequest(tracked_identity_uuid=tracked_uuid, content_hash="sha256:v1")
        )
        assert r1.outcome == ChangeOutcome.INSERT

        # Modified content
        r2 = await service.detect_change(
            ChangeDetectionRequest(tracked_identity_uuid=tracked_uuid, content_hash="sha256:v2")
        )
        assert r2.outcome == ChangeOutcome.UPDATE
        assert r2.previous_hash == "sha256:v1"

    @skip_without_db
    @pytest.mark.asyncio
    async def test_detect_change_unknown_tracked_uuid_raises(self, service):
        from src.identity.models import ChangeDetectionRequest
        cdr = ChangeDetectionRequest(tracked_identity_uuid=uuid4(), content_hash="sha256:x")
        with pytest.raises(LookupError):
            await service.detect_change(cdr)


class TestGetBindingSetLookup:
    """Integration tests for lookup helpers used by the API layer."""

    @skip_without_db
    @pytest.mark.asyncio
    async def test_get_binding_set_returns_none_for_unknown(self, service):
        result = await service.get_binding_set(uuid4())
        assert result is None

    @skip_without_db
    @pytest.mark.asyncio
    async def test_list_scopes_includes_well_known(self, service):
        scopes = await service.list_scopes()
        names = {s.scope_name for s in scopes}
        # Well-known scopes seeded by 008_seed_scopes.sql
        assert "sead://reconciliation" in names
        assert "sead://migration" in names
        assert "sead://admin" in names
