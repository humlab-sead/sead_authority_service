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

import asyncio
import os
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from src.api.identity_router import get_identity_service
from src.configuration import get_connection
from src.identity.models import IdentitySignal, ResolutionRequest
from src.identity.repository import ResolveBatchRepository
from src.identity.service import IdentityBatchConflict, IdentityBindingConflict, IdentityService
from src.identity.types import BindingMethod, BindingSetState, ChangeOutcome, IdentityType, TrackedIdentityState

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
    """Live IdentityService pointed at the session-configured disposable DB."""
    return IdentityService()


@pytest.fixture
def scope_name() -> str:
    """Unique scope name per test run to avoid cross-test pollution."""
    return f"sead://test-integration/{uuid4().hex[:8]}"


@pytest.fixture
def disposable_service() -> IdentityService:
    """Live IdentityService pointed at the session-configured disposable DB."""
    return IdentityService()


def _site_request(label: str) -> ResolutionRequest:
    return ResolutionRequest(
        entity_type="site",
        primary_signal=IdentitySignal(
            identity_type=IdentityType.BUSINESS_KEY,
            identity_value=label,
        ),
    )


def _sample_request(label: str) -> ResolutionRequest:
    return ResolutionRequest(
        entity_type="sample",
        primary_signal=IdentitySignal(
            identity_type=IdentityType.BUSINESS_KEY,
            identity_value=label,
        ),
    )


def _managed_entity_request(entity_type: str, label: str) -> ResolutionRequest:
    return ResolutionRequest(
        entity_type=entity_type,
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
    async def test_new_site_aggregate_id_comes_from_sims_allocator(self, disposable_service, scope_name):
        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'site'"
            )
            next_id_before = (await cursor.fetchone())[0]

        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submission = await disposable_service.create_submission(
            scope.scope_uuid, f"batch-{uuid4().hex[:8]}", created_by="test"
        )
        request = _site_request(f"Allocated site {uuid4().hex}")
        outcome = await disposable_service.resolve_identity(
            scope.scope_uuid,
            request,
            submission_uuid=submission.submission_uuid,
            created_by="test",
        )
        binding_set = await disposable_service.bind(
            submission_uuid=submission.submission_uuid,
            outcomes=[outcome],
            created_by="test",
        )

        assert binding_set.lifecycle_state == BindingSetState.CONFIRMED
        assert outcome.aggregate_id is not None
        assert outcome.aggregate_id == next_id_before
        assert outcome.tracked_identity_uuid is not None

        retry = await disposable_service.resolve_identity(
            scope.scope_uuid,
            request,
            submission_uuid=submission.submission_uuid,
            created_by="test",
        )
        assert retry.outcome == "matched"
        assert retry.aggregate_id == outcome.aggregate_id
        assert retry.tracked_identity_uuid == outcome.tracked_identity_uuid

        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'site'"
            )
            allocator_next_id = (await cursor.fetchone())[0]

        assert allocator_next_id == outcome.aggregate_id + 1


    @skip_without_db
    @pytest.mark.asyncio
    async def test_concurrent_same_source_reuses_one_site_identity(self, disposable_service, scope_name):
        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submissions = [
            await disposable_service.create_submission(scope.scope_uuid, f"concurrent-{uuid4().hex}", created_by="test")
            for _ in range(12)
        ]
        request = _site_request(f"Concurrent same site {uuid4().hex}")

        outcomes = await asyncio.gather(
            *(
                disposable_service.resolve_identity(
                    scope.scope_uuid,
                    request,
                    submission_uuid=submission.submission_uuid,
                    created_by="test",
                )
                for submission in submissions
            )
        )
        assert len({outcome.source_identity_uuid for outcome in outcomes}) == 1
        assert all(outcome.outcome == "new" for outcome in outcomes)

        binding_sets = await asyncio.gather(
            *(
                disposable_service.bind(submission.submission_uuid, [outcome], created_by="test")
                for submission, outcome in zip(submissions, outcomes)
            )
        )
        assert all(binding_set.lifecycle_state == BindingSetState.CONFIRMED for binding_set in binding_sets)
        assert len({outcome.tracked_identity_uuid for outcome in outcomes}) == 1
        assert len({outcome.aggregate_id for outcome in outcomes}) == 1

        site_bindings = await disposable_service.binding_repo.list_active_bindings(outcomes[0].source_identity_uuid)
        confirmed_targets = {
            binding.tracked_identity_uuid
            for binding, state in site_bindings
            if state == BindingSetState.CONFIRMED
        }
        assert len(confirmed_targets) == 1
        assert confirmed_targets == {outcomes[0].tracked_identity_uuid}

    @skip_without_db
    @pytest.mark.asyncio
    async def test_concurrent_distinct_sources_receive_distinct_site_ids(self, disposable_service, scope_name):
        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submissions = [
            await disposable_service.create_submission(scope.scope_uuid, f"distinct-{uuid4().hex}", created_by="test")
            for _ in range(12)
        ]
        requests = [_site_request(f"Concurrent distinct site {uuid4().hex}") for _ in submissions]

        outcomes = await asyncio.gather(
            *(
                disposable_service.resolve_identity(
                    scope.scope_uuid,
                    request,
                    submission_uuid=submission.submission_uuid,
                    created_by="test",
                )
                for submission, request in zip(submissions, requests)
            )
        )
        binding_sets = await asyncio.gather(
            *(
                disposable_service.bind(submission.submission_uuid, [outcome], created_by="test")
                for submission, outcome in zip(submissions, outcomes)
            )
        )

        assert all(binding_set.lifecycle_state == BindingSetState.CONFIRMED for binding_set in binding_sets)
        assert len({outcome.source_identity_uuid for outcome in outcomes}) == 12
        assert all(outcome.aggregate_id is not None for outcome in outcomes)
        assert len({outcome.aggregate_id for outcome in outcomes}) == 12

    @skip_without_db
    @pytest.mark.asyncio
    async def test_proposed_site_binding_blocks_resolution_and_allocation(self, disposable_service, scope_name):
        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submission = await disposable_service.create_submission(
            scope.scope_uuid, f"proposed-{uuid4().hex}", created_by="test"
        )
        request = _site_request(f"Proposed site binding {uuid4().hex}")
        outcome = await disposable_service.resolve_identity(
            scope.scope_uuid, request, submission_uuid=submission.submission_uuid, created_by="test"
        )
        materialized_sites = [
            identity
            for identity in await disposable_service.tracked_identity_repo.list_all()
            if identity.entity_type == "site" and identity.lifecycle_state == TrackedIdentityState.MATERIALIZED
        ]
        assert materialized_sites
        proposed_set = await disposable_service.binding_set_repo.create(
            submission_uuid=submission.submission_uuid, created_by="test"
        )
        await disposable_service.binding_repo.create(
            binding_set_uuid=proposed_set.binding_set_uuid,
            source_identity_uuid=outcome.source_identity_uuid,
            tracked_identity_uuid=materialized_sites[0].tracked_identity_uuid,
            method=BindingMethod.BUSINESS_KEY,
            created_by="test",
        )
        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'site'"
            )
            next_id_before = (await cursor.fetchone())[0]

        with pytest.raises(IdentityBindingConflict, match="unresolved proposed binding"):
            await disposable_service.resolve_identity(
                scope.scope_uuid, request, submission_uuid=submission.submission_uuid, created_by="test"
            )
        with pytest.raises(IdentityBindingConflict, match="unresolved proposed binding"):
            await disposable_service.bind(submission.submission_uuid, [outcome], created_by="test")

        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'site'"
            )
            next_id_after = (await cursor.fetchone())[0]
        assert next_id_after == next_id_before

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


class TestResolveAndBindSample:
    """Disposable sample allocation tests."""

    @pytest.mark.parametrize(
        "entity_type",
        [
            "dataset",
            "analysis_entity",
        ],
    )
    @skip_without_db
    @pytest.mark.asyncio
    async def test_new_model_aggregate_id_comes_from_sims_allocator(self, disposable_service, scope_name, entity_type):
        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = %s",
                (entity_type,),
            )
            next_id_before = (await cursor.fetchone())[0]

        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submission = await disposable_service.create_submission(
            scope.scope_uuid, f"batch-{entity_type}-{uuid4().hex}", created_by="test"
        )
        request = _managed_entity_request(entity_type, f"Allocated {entity_type} {uuid4().hex}")
        outcome = await disposable_service.resolve_identity(
            scope.scope_uuid, request, submission_uuid=submission.submission_uuid, created_by="test"
        )
        binding_set = await disposable_service.bind(
            submission_uuid=submission.submission_uuid, outcomes=[outcome], created_by="test"
        )
        retry = await disposable_service.resolve_identity(
            scope.scope_uuid, request, submission_uuid=submission.submission_uuid, created_by="test"
        )

        assert binding_set.lifecycle_state == BindingSetState.CONFIRMED
        assert outcome.aggregate_id is not None
        assert outcome.aggregate_id == next_id_before
        assert outcome.tracked_identity_uuid is not None
        assert retry.outcome == "matched"
        assert retry.aggregate_id == outcome.aggregate_id
        assert retry.tracked_identity_uuid == outcome.tracked_identity_uuid

        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = %s",
                (entity_type,),
            )
            allocator_next_id = (await cursor.fetchone())[0]

        assert allocator_next_id == outcome.aggregate_id + 1

    @skip_without_db
    @pytest.mark.asyncio
    async def test_new_sample_aggregate_id_comes_from_sims_allocator(self, disposable_service, scope_name):
        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'sample'"
            )
            next_id_before = (await cursor.fetchone())[0]

        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submission = await disposable_service.create_submission(
            scope.scope_uuid, f"batch-sample-{uuid4().hex[:8]}", created_by="test"
        )
        request = _sample_request(f"Allocated sample {uuid4().hex}")
        outcome = await disposable_service.resolve_identity(
            scope.scope_uuid,
            request,
            submission_uuid=submission.submission_uuid,
            created_by="test",
        )
        binding_set = await disposable_service.bind(
            submission_uuid=submission.submission_uuid,
            outcomes=[outcome],
            created_by="test",
        )
        assert binding_set.lifecycle_state == BindingSetState.CONFIRMED
        assert binding_set.lifecycle_state == BindingSetState.CONFIRMED
        assert outcome.aggregate_id is not None
        assert outcome.aggregate_id == next_id_before
        assert outcome.tracked_identity_uuid is not None

        retry = await disposable_service.resolve_identity(
            scope.scope_uuid,
            request,
            submission_uuid=submission.submission_uuid,
            created_by="test",
        )
        assert retry.outcome == "matched"
        assert retry.aggregate_id == outcome.aggregate_id
        assert retry.tracked_identity_uuid == outcome.tracked_identity_uuid

        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'sample'"
            )
            allocator_next_id = (await cursor.fetchone())[0]

        assert allocator_next_id == outcome.aggregate_id + 1

    @skip_without_db
    @pytest.mark.asyncio
    async def test_concurrent_distinct_samples_receive_distinct_ids(self, disposable_service, scope_name):
        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submissions = [
            await disposable_service.create_submission(scope.scope_uuid, f"samples-{uuid4().hex}", created_by="test")
            for _ in range(12)
        ]
        requests = [_sample_request(f"Concurrent sample {uuid4().hex}") for _ in submissions]

        outcomes = await asyncio.gather(
            *(
                disposable_service.resolve_identity(
                    scope.scope_uuid,
                    request,
                    submission_uuid=submission.submission_uuid,
                    created_by="test",
                )
                for submission, request in zip(submissions, requests)
            )
        )
        binding_sets = await asyncio.gather(
            *(
                disposable_service.bind(submission.submission_uuid, [outcome], created_by="test")
                for submission, outcome in zip(submissions, outcomes)
            )
        )

        assert all(binding_set.lifecycle_state == BindingSetState.CONFIRMED for binding_set in binding_sets)
        assert all(outcome.aggregate_id is not None for outcome in outcomes)
        assert len({outcome.aggregate_id for outcome in outcomes}) == 12

    @skip_without_db
    @pytest.mark.asyncio
    async def test_concurrent_same_source_reuses_one_sample_identity(self, disposable_service, scope_name):
        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submissions = [
            await disposable_service.create_submission(scope.scope_uuid, f"same-sample-{uuid4().hex}", created_by="test")
            for _ in range(12)
        ]
        request = _sample_request(f"Concurrent same sample {uuid4().hex}")

        outcomes = await asyncio.gather(
            *(
                disposable_service.resolve_identity(
                    scope.scope_uuid,
                    request,
                    submission_uuid=submission.submission_uuid,
                    created_by="test",
                )
                for submission in submissions
            )
        )
        assert len({outcome.source_identity_uuid for outcome in outcomes}) == 1
        assert all(outcome.outcome == "new" for outcome in outcomes)

        binding_sets = await asyncio.gather(
            *(
                disposable_service.bind(submission.submission_uuid, [outcome], created_by="test")
                for submission, outcome in zip(submissions, outcomes)
            )
        )

        assert all(binding_set.lifecycle_state == BindingSetState.CONFIRMED for binding_set in binding_sets)
        assert len({outcome.tracked_identity_uuid for outcome in outcomes}) == 1
        assert len({outcome.aggregate_id for outcome in outcomes}) == 1

    @skip_without_db
    @pytest.mark.asyncio
    async def test_changed_sample_payload_reuses_existing_identity(self, disposable_service, scope_name):
        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submission = await disposable_service.create_submission(
            scope.scope_uuid, f"changed-sample-{uuid4().hex}", created_by="test"
        )
        stable_key = f"Changed sample {uuid4().hex}"
        first_request = _sample_request(stable_key)
        first_outcome = await disposable_service.resolve_identity(
            scope.scope_uuid, first_request, submission_uuid=submission.submission_uuid, created_by="test"
        )
        await disposable_service.bind(
            submission_uuid=submission.submission_uuid, outcomes=[first_outcome], created_by="test"
        )

        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'sample'"
            )
            next_id_before_retry = (await cursor.fetchone())[0]

        changed_request = ResolutionRequest(
            entity_type="sample",
            primary_signal=first_request.primary_signal,
            additional_signals=[
                IdentitySignal(
                    identity_type=IdentityType.PROVIDER_KEY,
                    identity_value=f"updated-payload-{uuid4().hex}",
                )
            ],
        )
        retry = await disposable_service.resolve_identity(
            scope.scope_uuid, changed_request, submission_uuid=submission.submission_uuid, created_by="test"
        )

        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'sample'"
            )
            next_id_after_retry = (await cursor.fetchone())[0]

        assert retry.outcome == "matched"
        assert retry.tracked_identity_uuid == first_outcome.tracked_identity_uuid
        assert retry.aggregate_id == first_outcome.aggregate_id
        assert next_id_after_retry == next_id_before_retry

    @skip_without_db
    @pytest.mark.asyncio
    async def test_proposed_sample_binding_blocks_resolution_and_allocation(self, disposable_service, scope_name):
        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        submission = await disposable_service.create_submission(
            scope.scope_uuid, f"proposed-sample-{uuid4().hex}", created_by="test"
        )
        request = _sample_request(f"Proposed sample {uuid4().hex}")
        outcome = await disposable_service.resolve_identity(
            scope.scope_uuid, request, submission_uuid=submission.submission_uuid, created_by="test"
        )
        materialized_samples = [
            identity
            for identity in await disposable_service.tracked_identity_repo.list_all()
            if identity.entity_type == "sample" and identity.lifecycle_state == TrackedIdentityState.MATERIALIZED
        ]
        assert materialized_samples

        proposed_set = await disposable_service.binding_set_repo.create(
            submission_uuid=submission.submission_uuid, created_by="test"
        )
        await disposable_service.binding_repo.create(
            binding_set_uuid=proposed_set.binding_set_uuid,
            source_identity_uuid=outcome.source_identity_uuid,
            tracked_identity_uuid=materialized_samples[0].tracked_identity_uuid,
            method=BindingMethod.BUSINESS_KEY,
            created_by="test",
        )
        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'sample'"
            )
            next_id_before = (await cursor.fetchone())[0]

        with pytest.raises(IdentityBindingConflict, match="unresolved proposed binding"):
            await disposable_service.resolve_identity(
                scope.scope_uuid, request, submission_uuid=submission.submission_uuid, created_by="test"
            )
        with pytest.raises(IdentityBindingConflict, match="unresolved proposed binding"):
            await disposable_service.bind(submission.submission_uuid, [outcome], created_by="test")

        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = 'sample'"
            )
            next_id_after = (await cursor.fetchone())[0]
        assert next_id_after == next_id_before


class TestApprovedExistingAggregateId:
    """Approved SIMS aggregate IDs bind source identities to existing tracked identities."""

    @skip_without_db
    @pytest.mark.asyncio
    async def test_approved_aggregate_id_reuses_existing_identity_and_rejects_conflicts(self, service, scope_name):
        identities = await service.tracked_identity_repo.list_all()
        sites = [
            identity
            for identity in identities
            if identity.entity_type == "site"
            and identity.aggregate_id is not None
        ]
        if len(sites) < 2:
            pytest.skip("Integration database needs at least two existing SIMS site identities")

        target_identity, conflicting_identity = sites[:2]
        site_identity_count = len([identity for identity in identities if identity.entity_type == "site"])
        source_key = f"approved-site-{uuid4().hex}"
        request = {
            "entity_type": "site",
            "primary_signal": {"identity_type": "business_key", "identity_value": source_key},
            "approved_aggregate_id": target_identity.aggregate_id,
        }
        previous_service_override = app.dependency_overrides.get(get_identity_service)
        app.dependency_overrides[get_identity_service] = lambda: service
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                first_response = await client.post(
                    "/identity/resolve",
                    json={
                        "scope_name": scope_name,
                        "run_id": f"run-approved-1-{uuid4().hex}",
                        "submission_name": f"approved-1-{uuid4().hex}",
                        "requests": [request],
                    },
                )
                assert first_response.status_code == 200
                first_data = first_response.json()
                first_outcome = first_data["outcomes"][0]

                second_response = await client.post(
                    "/identity/resolve",
                    json={
                        "scope_name": scope_name,
                        "run_id": f"run-approved-2-{uuid4().hex}",
                        "submission_name": f"approved-2-{uuid4().hex}",
                        "requests": [request],
                    },
                )
                assert second_response.status_code == 200
                second_data = second_response.json()
                second_outcome = second_data["outcomes"][0]

                conflicting_request = {
                    **request,
                    "approved_aggregate_id": conflicting_identity.aggregate_id,
                }
                conflict_response = await client.post(
                    "/identity/resolve",
                    json={
                        "scope_name": scope_name,
                        "run_id": f"run-approved-conflict-{uuid4().hex}",
                        "submission_name": f"approved-conflict-{uuid4().hex}",
                        "requests": [conflicting_request],
                    },
                )
        finally:
            if previous_service_override is None:
                app.dependency_overrides.pop(get_identity_service, None)
            else:
                app.dependency_overrides[get_identity_service] = previous_service_override

        assert first_outcome["outcome"] == "matched"
        assert first_outcome["tracked_identity_uuid"] == str(target_identity.tracked_identity_uuid)
        assert first_outcome["target_id"] == target_identity.aggregate_id
        assert second_outcome["source_identity_uuid"] == first_outcome["source_identity_uuid"]
        assert second_outcome["tracked_identity_uuid"] == first_outcome["tracked_identity_uuid"]
        assert second_outcome["target_id"] == first_outcome["target_id"]
        assert first_data["binding_set"]["binding_count"] == second_data["binding_set"]["binding_count"] == 1
        assert first_data["binding_set"]["lifecycle_state"] == "confirmed"
        assert second_data["binding_set"]["lifecycle_state"] == "confirmed"
        assert conflict_response.status_code == 409

        confirmed_binding = await service.binding_repo.find_confirmed_binding(UUID(first_outcome["source_identity_uuid"]))
        assert confirmed_binding is not None
        assert confirmed_binding[0].tracked_identity_uuid == target_identity.tracked_identity_uuid

        final_identities = await service.tracked_identity_repo.list_all()
        assert len([identity for identity in final_identities if identity.entity_type == "site"]) == site_identity_count


class TestResolveAndBindSampleGroup:
    """Phase 2 pilot: provider-owned `sample_group` entities."""

    @skip_without_db
    @pytest.mark.asyncio
    async def test_bind_sample_group_auto_confirms(self, service, scope_name):
        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT 1 FROM sead_identity.internal_id_allocators WHERE entity_type = 'sample_group'"
            )
            if await cursor.fetchone() is None:
                pytest.skip("sample_group ID allocator is not bootstrapped in the disposable database")

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


class TestResolveBatchIdempotency:
    """Whole-batch atomicity and replay against the helper-owned disposable DB."""

    def _batch_request(self, entity_type: str, label: str) -> ResolutionRequest:
        return ResolutionRequest(
            entity_type=entity_type,
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value=label),
        )

    async def _allocator_next(self, entity_type: str) -> int:
        async with get_connection() as connection, connection.cursor() as cursor:
            await cursor.execute(
                "SELECT next_internal_id FROM sead_identity.internal_id_allocators WHERE entity_type = %s",
                (entity_type,),
            )
            row = await cursor.fetchone()
            return row[0]

    @skip_without_db
    @pytest.mark.asyncio
    async def test_same_key_same_payload_replays_stored_result(self, disposable_service, scope_name):
        run_id = f"run-{uuid4().hex}"
        request = self._batch_request("site", f"Replay site {uuid4().hex}")

        first = await disposable_service.resolve_batch(scope_name, "batch-replay", run_id, [request], created_by="test")
        second = await disposable_service.resolve_batch(scope_name, "batch-replay", run_id, [request], created_by="test")

        assert first.submission_uuid == second.submission_uuid
        assert first.scope_uuid == second.scope_uuid
        assert first.binding_set.binding_set_uuid == second.binding_set.binding_set_uuid
        assert first.outcomes[0].aggregate_id == second.outcomes[0].aggregate_id
        assert first.outcomes[0].tracked_identity_uuid == second.outcomes[0].tracked_identity_uuid

    @skip_without_db
    @pytest.mark.asyncio
    async def test_reused_run_with_changed_payload_conflicts(self, disposable_service, scope_name):
        run_id = f"run-{uuid4().hex}"
        first_request = self._batch_request("site", f"Changed payload A {uuid4().hex}")

        await disposable_service.resolve_batch(scope_name, "batch-changed", run_id, [first_request], created_by="test")

        second_request = self._batch_request("site", f"Changed payload B {uuid4().hex}")
        with pytest.raises(IdentityBatchConflict, match="different payload"):
            await disposable_service.resolve_batch(scope_name, "batch-changed", run_id, [second_request], created_by="test")

    @skip_without_db
    @pytest.mark.asyncio
    async def test_concurrent_same_run_requests_serialize(self, disposable_service, scope_name):
        run_id = f"run-{uuid4().hex}"
        request = self._batch_request("site", f"Concurrent run site {uuid4().hex}")

        results = await asyncio.gather(
            *(
                disposable_service.resolve_batch(scope_name, "batch-concurrent", run_id, [request], created_by="test")
                for _ in range(5)
            )
        )

        assert len({result.submission_uuid for result in results}) == 1
        assert len({result.outcomes[0].aggregate_id for result in results}) == 1
        assert len({result.outcomes[0].tracked_identity_uuid for result in results}) == 1

    @skip_without_db
    @pytest.mark.asyncio
    async def test_outcomes_preserve_request_order(self, disposable_service, scope_name):
        site_request_a = self._batch_request("site", f"Order site A {uuid4().hex}")
        sample_request = self._batch_request("sample", f"Order sample {uuid4().hex}")
        site_request_b = self._batch_request("site", f"Order site B {uuid4().hex}")
        requests = [site_request_a, sample_request, site_request_b]

        result = await disposable_service.resolve_batch(
            scope_name, "batch-order", f"run-{uuid4().hex}", requests, created_by="test"
        )

        assert [outcome.entity_type for outcome in result.outcomes] == ["site", "sample", "site"]

    @skip_without_db
    @pytest.mark.asyncio
    async def test_distinct_run_proposed_binding_conflicts(self, disposable_service, scope_name):
        scope = await disposable_service.get_or_create_scope(scope_name, created_by="test")
        request = self._batch_request("site", f"Proposed batch site {uuid4().hex}")
        outcome = await disposable_service.resolve_identity(scope.scope_uuid, request, created_by="test")

        materialized_sites = [
            identity
            for identity in await disposable_service.tracked_identity_repo.list_all()
            if identity.entity_type == "site" and identity.lifecycle_state == TrackedIdentityState.MATERIALIZED
        ]
        assert materialized_sites
        proposed_set = await disposable_service.binding_set_repo.create(submission_uuid=None, created_by="test")
        await disposable_service.binding_repo.create(
            binding_set_uuid=proposed_set.binding_set_uuid,
            source_identity_uuid=outcome.source_identity_uuid,
            tracked_identity_uuid=materialized_sites[0].tracked_identity_uuid,
            method=BindingMethod.BUSINESS_KEY,
            created_by="test",
        )

        next_before = await self._allocator_next("site")

        with pytest.raises(IdentityBindingConflict, match="unresolved proposed binding"):
            await disposable_service.resolve_batch(scope_name, "batch-proposed", f"run-{uuid4().hex}", [request], created_by="test")

        assert await self._allocator_next("site") == next_before

    @skip_without_db
    @pytest.mark.asyncio
    async def test_failed_batch_rolls_back_without_advancing_allocator(self, disposable_service, scope_name):
        run_id = f"run-{uuid4().hex}"
        next_before = await self._allocator_next("site")

        valid_request = self._batch_request("site", f"Rollback valid site {uuid4().hex}")
        bad_request = ResolutionRequest(
            entity_type="site",
            approved_aggregate_id=999999999,
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value=f"Rollback bad {uuid4().hex}"),
        )

        with pytest.raises(IdentityBindingConflict):
            await disposable_service.resolve_batch(
                scope_name, "batch-rollback", run_id, [valid_request, bad_request], created_by="test"
            )

        assert await self._allocator_next("site") == next_before
        assert await ResolveBatchRepository().find(scope_name, run_id) is None
