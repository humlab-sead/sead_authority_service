"""Disposable-database tests for reconciliation verification and approved bindings."""

from __future__ import annotations

import asyncio
import os
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient, Response
from psycopg import sql

from main import app
from src.api.identity_router import get_identity_service
from src.api.model import CandidateVerificationItem
from src.candidate_verification import _configured_id_base, get_reconciliation_readiness, verify_candidate_batch
from src.configuration import get_connection
from src.identity.models import IdentitySignal, ResolutionRequest, TrackedIdentity
from src.identity.repository import ResolveBatchRepository
from src.identity.service import IdentityBindingConflict, IdentityService
from src.identity.types import IdentityType, TrackedIdentityState
from src.reconcile import reconcile_queries

_RUN_INTEGRATION = os.environ.get("SIMS_INTEGRATION_DB", "0") == "1"
_SKIP_REASON = (
    "Integration test requires the helper-owned 127.0.0.1:55432/sead_staging database. "
    "Set SIMS_INTEGRATION_DB=1 and configure its connection variables."
)
pytestmark = pytest.mark.integration


async def _sims_row_counts() -> tuple[int, int, int, int, int]:
    async with get_connection() as connection, connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT
                (SELECT count(*) FROM sead_identity.tracked_identities),
                (SELECT count(*) FROM sead_identity.submissions),
                (SELECT count(*) FROM sead_identity.binding_sets),
                (SELECT count(*) FROM sead_identity.bindings),
                (SELECT count(*) FROM sead_identity.resolve_batches)
            """
        )
        return await cursor.fetchone()


async def _create_materialized_site(service: IdentityService) -> TrackedIdentity:
    identity = await service.tracked_identity_repo.mint("site", created_by="phase4 integration test")
    materialized = await service.tracked_identity_repo.update_lifecycle_state(
        identity.tracked_identity_uuid,
        TrackedIdentityState.MATERIALIZED,
    )
    assert materialized is not None
    return materialized


def _approved_request(aggregate_id: int, identity_key: str) -> dict:
    return {
        "entity_type": "site",
        "primary_signal": {"identity_type": "business_key", "identity_value": identity_key},
        "approved_aggregate_id": aggregate_id,
    }


async def _resolve_via_api(service: IdentityService, payload: dict) -> Response:
    previous_override = app.dependency_overrides.get(get_identity_service)
    app.dependency_overrides[get_identity_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/identity/resolve", json=payload)
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_identity_service, None)
        else:
            app.dependency_overrides[get_identity_service] = previous_override


@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_SKIP_REASON)
@pytest.mark.asyncio
async def test_site_match_candidate_and_readiness_round_trip() -> None:
    async with get_connection() as connection, connection.cursor() as cursor:
        await cursor.execute("SELECT to_regprocedure('authority.fuzzy_site(text,integer)')")
        function_row = await cursor.fetchone()
        assert function_row is not None and function_row[0] is not None, (
            "authority.fuzzy_site(text,integer) is missing from the helper-owned database; "
            "deploy it through the generated schema procedure before rerunning V-3"
        )

        await cursor.execute(
            """
            SELECT site_id, label
            FROM authority.site
            WHERE label IS NOT NULL AND btrim(label) <> ''
            ORDER BY site_id
            LIMIT 1
            """
        )
        site_row = await cursor.fetchone()
        assert site_row is not None, "The helper-owned database must contain a site with a label."
        site_id, label = site_row
        await cursor.execute("SELECT COALESCE(MAX(site_id), 0) + 1 FROM authority.site")
        missing_site_id = (await cursor.fetchone())[0]

    id_base = _configured_id_base()
    assert id_base is not None
    expected_candidate_id = f"{id_base}site/{site_id}"
    before_counts = await _sims_row_counts()

    matches = await reconcile_queries({"q0": {"query": label, "type": "site", "limit": 100}})
    candidate = next((item for item in matches["q0"]["result"] if item["id"] == expected_candidate_id), None)
    assert candidate is not None, f"The real site match query did not return {expected_candidate_id}."

    results = await verify_candidate_batch(
        [
            CandidateVerificationItem(type="site", id=expected_candidate_id),
            CandidateVerificationItem(type="site", id=f"{id_base}site/{missing_site_id}"),
            CandidateVerificationItem(type="site", id=f"{id_base}other/{site_id}"),
            CandidateVerificationItem(type="sample_group", id=f"{id_base}sample_group/{site_id}"),
        ]
    )
    readiness = await get_reconciliation_readiness("site")
    after_counts = await _sims_row_counts()

    assert [result.outcome for result in results] == ["exists", "not_found", "invalid_candidate", "unsupported_type"]
    assert results[0].entity_type == "site"
    assert results[0].aggregate_id == site_id
    assert readiness.ready is True
    assert readiness.reason is None
    assert after_counts == before_counts


@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_SKIP_REASON)
@pytest.mark.asyncio
async def test_readiness_reports_missing_site_match_function() -> None:
    async with get_connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT to_regprocedure('authority.fuzzy_site(text,integer)')")
            function_row = await cursor.fetchone()
            assert (
                function_row is not None and function_row[0] is not None
            ), "Install authority.fuzzy_site(text,integer) in the helper-owned database before running V-3."
            await cursor.execute("SAVEPOINT reconciliation_readiness_missing_function")
            temporary_name = f"fuzzy_site_phase4_missing_{uuid4().hex}"
            await cursor.execute(
                sql.SQL("ALTER FUNCTION authority.fuzzy_site(text, integer) RENAME TO {}").format(sql.Identifier(temporary_name))
            )

        try:
            readiness = await get_reconciliation_readiness("site")
            assert readiness.ready is False
            assert readiness.reason is not None
            assert "match function" in readiness.reason
        finally:
            async with connection.cursor() as cursor:
                await cursor.execute("ROLLBACK TO SAVEPOINT reconciliation_readiness_missing_function")
                await cursor.execute("RELEASE SAVEPOINT reconciliation_readiness_missing_function")
                await cursor.execute("SELECT to_regprocedure('authority.fuzzy_site(text,integer)')")
                restored_function = await cursor.fetchone()
                assert restored_function is not None and restored_function[0] is not None


@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_SKIP_REASON)
@pytest.mark.asyncio
async def test_approved_id_states_replay_and_confirmed_binding() -> None:
    service = IdentityService()
    tracked_identity = await service.tracked_identity_repo.mint("site", created_by="phase4 integration test")
    scope_name = f"sead://phase4/{uuid4().hex}"

    for state in (
        TrackedIdentityState.ALLOCATED,
        TrackedIdentityState.PENDING_MATERIALIZATION,
        TrackedIdentityState.INVALIDATED,
    ):
        updated = await service.tracked_identity_repo.update_lifecycle_state(tracked_identity.tracked_identity_uuid, state)
        assert updated is not None
        before_counts = await _sims_row_counts()
        run_id = f"rejected-{state.value}-{uuid4().hex}"
        payload = {
            "scope_name": scope_name,
            "run_id": run_id,
            "submission_name": f"rejected-{state.value}",
            "requests": [_approved_request(tracked_identity.aggregate_id, f"{state.value}-{uuid4().hex}")],
        }

        response = await _resolve_via_api(service, payload)

        assert response.status_code == 409
        assert "must be materialized" in response.json()["detail"]
        assert await _sims_row_counts() == before_counts
        assert await ResolveBatchRepository().find(scope_name, run_id) is None

    async with get_connection() as connection, connection.cursor() as cursor:
        await cursor.execute(
            "SELECT COALESCE(MAX(aggregate_id), 0) + 1 FROM sead_identity.tracked_identities WHERE entity_type = %s",
            ("site",),
        )
        missing_aggregate_id = (await cursor.fetchone())[0]

    missing_response = await _resolve_via_api(
        service,
        {
            "scope_name": scope_name,
            "run_id": f"missing-{uuid4().hex}",
            "submission_name": "missing-approved-site",
            "requests": [_approved_request(missing_aggregate_id, f"missing-{uuid4().hex}")],
        },
    )
    assert missing_response.status_code == 409
    assert "No SIMS site tracked identity" in missing_response.json()["detail"]

    materialized = await _create_materialized_site(service)
    identity_key = f"materialized-{uuid4().hex}"
    payload = {
        "scope_name": scope_name,
        "run_id": f"materialized-{uuid4().hex}",
        "submission_name": "materialized-approved-site",
        "requests": [_approved_request(materialized.aggregate_id, identity_key)],
    }

    first_response = await _resolve_via_api(service, payload)
    replay_response = await _resolve_via_api(service, payload)
    assert first_response.status_code == 200
    assert first_response.json()["outcomes"][0]["target_id"] == materialized.aggregate_id
    assert replay_response.status_code == 200
    assert replay_response.json()["binding_set"]["binding_set_uuid"] == first_response.json()["binding_set"]["binding_set_uuid"]

    await service.tracked_identity_repo.update_lifecycle_state(materialized.tracked_identity_uuid, TrackedIdentityState.INVALIDATED)
    before_rejected_reuse = await _sims_row_counts()
    invalidated_replay = await _resolve_via_api(service, payload)
    confirmed_binding_reuse = await _resolve_via_api(
        service,
        {
            **payload,
            "run_id": f"confirmed-reuse-{uuid4().hex}",
            "submission_name": "confirmed-binding-reuse",
        },
    )

    assert invalidated_replay.status_code == 409
    assert confirmed_binding_reuse.status_code == 409
    assert await _sims_row_counts() == before_rejected_reuse


@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_SKIP_REASON)
@pytest.mark.asyncio
async def test_approved_state_change_between_resolution_and_binding_is_rejected() -> None:
    service = IdentityService()
    tracked_identity = await _create_materialized_site(service)
    scope = await service.get_or_create_scope(f"sead://phase4/stale/{uuid4().hex}", created_by="test")
    request = ResolutionRequest(
        entity_type="site",
        approved_aggregate_id=tracked_identity.aggregate_id,
        primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value=f"stale-{uuid4().hex}"),
    )
    outcome = await service.resolve_identity(scope.scope_uuid, request)
    assert outcome.outcome == "matched"

    await service.tracked_identity_repo.update_lifecycle_state(tracked_identity.tracked_identity_uuid, TrackedIdentityState.INVALIDATED)
    before_counts = await _sims_row_counts()

    with pytest.raises(IdentityBindingConflict, match="must be materialized"):
        await service.bind(None, [outcome], approved_aggregate_ids=[tracked_identity.aggregate_id])

    assert await _sims_row_counts() == before_counts


@pytest.mark.skipif(not _RUN_INTEGRATION, reason=_SKIP_REASON)
@pytest.mark.asyncio
async def test_binding_state_row_lock_serializes_lifecycle_update() -> None:
    service = IdentityService()
    tracked_identity = await _create_materialized_site(service)
    scope = await service.get_or_create_scope(f"sead://phase4/lock/{uuid4().hex}", created_by="test")
    outcome = await service.resolve_identity(
        scope.scope_uuid,
        ResolutionRequest(
            entity_type="site",
            approved_aggregate_id=tracked_identity.aggregate_id,
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value=f"lock-{uuid4().hex}"),
        ),
    )

    row_locked = asyncio.Event()
    allow_binding = asyncio.Event()
    update_task: asyncio.Task | None = None
    original_lock = service.tracked_identity_repo.lock_for_binding

    async def pause_after_lock(tracked_uuid: UUID, entity_type: str, aggregate_id: int) -> TrackedIdentity | None:
        identity = await original_lock(tracked_uuid, entity_type, aggregate_id)
        row_locked.set()
        await allow_binding.wait()
        return identity

    service.tracked_identity_repo.lock_for_binding = pause_after_lock
    bind_task = asyncio.create_task(service.bind(None, [outcome], approved_aggregate_ids=[tracked_identity.aggregate_id]))
    try:
        await asyncio.wait_for(row_locked.wait(), timeout=10)
        update_task = asyncio.create_task(
            service.tracked_identity_repo.update_lifecycle_state(
                tracked_identity.tracked_identity_uuid,
                TrackedIdentityState.INVALIDATED,
            )
        )
        completed, _ = await asyncio.wait({update_task}, timeout=0.2)
        update_was_blocked = not completed
    finally:
        allow_binding.set()

    binding_set = await bind_task
    assert update_task is not None
    updated_identity = await update_task
    assert binding_set.binding_count == 1
    assert update_was_blocked
    assert updated_identity is not None
    assert updated_identity.lifecycle_state == TrackedIdentityState.INVALIDATED
