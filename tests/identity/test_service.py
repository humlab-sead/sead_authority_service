"""Unit tests for IdentityService — no database required.

All repositories and the policy are replaced with AsyncMock / MagicMock
instances. This tests the service orchestration logic in isolation.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from unittest.mock import DEFAULT, AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.identity.models import (
    Binding,
    BindingSet,
    BindingSetResponse,
    ChangeDetectionRequest,
    ChangeDetectionResult,
    IdentitySignal,
    ResolutionOutcome,
    ResolutionRequest,
    ResolveBatchRecord,
    ResolveBatchResult,
    SourceIdentity,
    SourceIdentityKey,
    SourceScope,
)
from src.identity.policy import EntityPolicy, IdentityPolicy
from src.identity.service import IdentityBatchConflict, IdentityBindingConflict, IdentityService, _request_fingerprint
from src.identity.types import (
    BindingMethod,
    BindingSetState,
    ChangeOutcome,
    IdentityType,
    TrackedIdentityState,
)

NOW = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Test fixtures & helpers
# ---------------------------------------------------------------------------

SCOPE_UUID: UUID = uuid4()
SUBMISSION_UUID: UUID = uuid4()
SOURCE_IDENTITY_UUID: UUID = uuid4()
TRACKED_UUID: UUID = uuid4()
BINDING_SET_UUID: UUID = uuid4()
BINDING_UUID: UUID = uuid4()


def _make_source_identity() -> SourceIdentity:
    return SourceIdentity(
        source_identity_uuid=SOURCE_IDENTITY_UUID,
        scope_uuid=SCOPE_UUID,
        entity_type="site",
        created_at=NOW,
    )


def _make_tracked_identity(state: str = "allocated") -> MagicMock:
    t = MagicMock()
    t.tracked_identity_uuid = TRACKED_UUID
    t.entity_type = "site"
    t.lifecycle_state = TrackedIdentityState(state)
    t.aggregate_id = None
    t.content_hash = None
    return t


def _make_binding(method: str = "business_key") -> Binding:
    return Binding(
        binding_uuid=BINDING_UUID,
        binding_set_uuid=BINDING_SET_UUID,
        source_identity_uuid=SOURCE_IDENTITY_UUID,
        tracked_identity_uuid=TRACKED_UUID,
        method=BindingMethod(method),
    )


def _make_binding_set(state: str = "proposed") -> BindingSet:
    return BindingSet(
        binding_set_uuid=BINDING_SET_UUID,
        submission_uuid=SUBMISSION_UUID,
        lifecycle_state=BindingSetState(state),
        created_at=NOW,
    )


def _provider_owned_policy(entity_type: str = "site") -> EntityPolicy:
    return EntityPolicy(
        entity_type=entity_type,
        entity_subtype="provider_owned",
        accept_uuid=False,
        allow_allocation=True,
        auto_confirm=True,
    )


def _shared_metadata_policy(entity_type: str = "taxa") -> EntityPolicy:
    return EntityPolicy(
        entity_type=entity_type,
        entity_subtype="shared_metadata",
        accept_uuid=True,
        allow_allocation=False,
        auto_confirm=False,
    )


def _mock_policy(side_effect=None) -> MagicMock:
    policy = MagicMock(spec=IdentityPolicy)
    policy.get_entity_policy = MagicMock(side_effect=side_effect or _provider_owned_policy)
    policy.known_entity_types.return_value = ["site"]
    return policy


def _make_service(
    scope_repo=None,
    submission_repo=None,
    source_identity_repo=None,
    tracked_identity_repo=None,
    binding_set_repo=None,
    binding_repo=None,
    resolve_batch_repo=None,
    policy=None,
):

    source_identity_repo = source_identity_repo or AsyncMock()
    binding_repo = binding_repo or AsyncMock()
    if source_identity_repo.lock_for_binding._mock_return_value is DEFAULT:  # type: ignore ; pylint: disable=protected-access
        source_identity_repo.lock_for_binding.return_value = None
    if binding_repo.list_active_bindings._mock_return_value is DEFAULT:  # type: ignore ; pylint: disable=protected-access
        binding_repo.list_active_bindings.return_value = []
    return IdentityService(
        scope_repo=scope_repo or AsyncMock(),
        submission_repo=submission_repo or AsyncMock(),
        source_identity_repo=source_identity_repo,
        tracked_identity_repo=tracked_identity_repo or AsyncMock(),
        binding_set_repo=binding_set_repo or AsyncMock(),
        binding_repo=binding_repo,
        resolve_batch_repo=resolve_batch_repo or AsyncMock(),
        policy=policy or _mock_policy(),
    )


# ---------------------------------------------------------------------------
# Scope helpers
# ---------------------------------------------------------------------------


class TestGetOrCreateScope:
    @pytest.mark.asyncio
    async def test_returns_existing_scope(self) -> None:
        existing = SourceScope(scope_uuid=SCOPE_UUID, scope_name="sead://admin", created_at=NOW)
        scope_repo = AsyncMock()
        scope_repo.get_by_name.return_value = existing

        service: IdentityService = _make_service(scope_repo=scope_repo)
        result: SourceScope = await service.get_or_create_scope("sead://admin")

        assert result.scope_name == "sead://admin"
        scope_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_scope_if_missing(self) -> None:
        new_scope = SourceScope(scope_uuid=SCOPE_UUID, scope_name="test://new", created_at=NOW)
        scope_repo = AsyncMock()
        scope_repo.get_by_name.return_value = None
        scope_repo.create.return_value = new_scope

        service: IdentityService = _make_service(scope_repo=scope_repo)
        result: SourceScope = await service.get_or_create_scope("test://new")

        assert result.scope_name == "test://new"
        scope_repo.create.assert_called_once()


# ---------------------------------------------------------------------------
# resolve_identity
# ---------------------------------------------------------------------------


class TestResolveIdentity:
    def _request(self) -> ResolutionRequest:
        return ResolutionRequest(
            entity_type="site",
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value="ABC-001"),
        )

    @pytest.mark.asyncio
    async def test_approved_aggregate_id_resolves_existing_identity(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        source_identity_repo.link_to_submission = AsyncMock()

        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        tracked_identity = _make_tracked_identity("allocated")
        tracked_identity.aggregate_id = 4321
        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.find_by_aggregate_id.return_value = tracked_identity

        service: IdentityService = _make_service(
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
            tracked_identity_repo=tracked_identity_repo,
        )
        request = ResolutionRequest(
            entity_type="site",
            approved_aggregate_id=4321,
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value="ABC-001"),
        )

        outcome = await service.resolve_identity(SCOPE_UUID, request, submission_uuid=SUBMISSION_UUID)

        assert outcome.outcome == "matched"
        assert outcome.tracked_identity_uuid == TRACKED_UUID
        assert outcome.aggregate_id == 4321
        tracked_identity_repo.find_by_aggregate_id.assert_awaited_once_with("site", 4321)
        tracked_identity_repo.mint.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approved_aggregate_id_without_sims_identity_conflicts(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        source_identity_repo.link_to_submission = AsyncMock()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None
        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.find_by_aggregate_id.return_value = None
        service: IdentityService = _make_service(
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
            tracked_identity_repo=tracked_identity_repo,
        )
        request = ResolutionRequest(
            entity_type="site",
            approved_aggregate_id=4321,
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value="ABC-001"),
        )

        with pytest.raises(IdentityBindingConflict, match="refusing to allocate"):
            await service.resolve_identity(SCOPE_UUID, request, submission_uuid=SUBMISSION_UUID)

    @pytest.mark.asyncio
    async def test_approved_aggregate_id_for_unlisted_entity_is_rejected_before_writes(self) -> None:
        source_identity_repo = AsyncMock()
        binding_repo = AsyncMock()
        tracked_identity_repo = AsyncMock()
        policy = _mock_policy()
        policy.known_entity_types.return_value = []
        service: IdentityService = _make_service(
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
            tracked_identity_repo=tracked_identity_repo,
            policy=policy,
        )
        request = ResolutionRequest(
            entity_type="unlisted_site_variant",
            approved_aggregate_id=4321,
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value="ABC-001"),
        )

        with pytest.raises(IdentityBindingConflict, match="not configured"):
            await service.resolve_identity(SCOPE_UUID, request, submission_uuid=SUBMISSION_UUID)

        source_identity_repo.create_or_get.assert_not_awaited()
        tracked_identity_repo.find_by_aggregate_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_approved_aggregate_id_conflicting_with_confirmed_binding_is_rejected(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        source_identity_repo.link_to_submission = AsyncMock()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = (_make_binding(), BindingSetState.CONFIRMED)
        tracked_identity = _make_tracked_identity("materialized")
        tracked_identity.aggregate_id = 4321
        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = tracked_identity
        service: IdentityService = _make_service(
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
            tracked_identity_repo=tracked_identity_repo,
        )
        request = ResolutionRequest(
            entity_type="site",
            approved_aggregate_id=9876,
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value="ABC-001"),
        )

        with pytest.raises(IdentityBindingConflict, match="already bound"):
            await service.resolve_identity(SCOPE_UUID, request, submission_uuid=SUBMISSION_UUID)

        tracked_identity_repo.find_by_aggregate_id.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_new_when_no_existing_binding(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        source_identity_repo.link_to_submission = AsyncMock()

        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        service: IdentityService = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        outcome: ResolutionOutcome = await service.resolve_identity(SCOPE_UUID, self._request(), submission_uuid=SUBMISSION_UUID)

        assert outcome.outcome == "new"
        assert outcome.tracked_identity_uuid is None
        assert outcome.aggregate_id is None
        assert outcome.source_identity_uuid == SOURCE_IDENTITY_UUID

    @pytest.mark.asyncio
    async def test_returns_matched_when_binding_exists(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        source_identity_repo.link_to_submission = AsyncMock()

        existing_binding = _make_binding()
        tracked_identity = _make_tracked_identity("materialized")
        tracked_identity.aggregate_id = 4321
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = (existing_binding, "confirmed")

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = tracked_identity

        service: IdentityService = _make_service(
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
            tracked_identity_repo=tracked_identity_repo,
        )
        outcome: ResolutionOutcome = await service.resolve_identity(SCOPE_UUID, self._request())

        assert outcome.outcome == "matched"
        assert outcome.tracked_identity_uuid == TRACKED_UUID
        assert outcome.aggregate_id == 4321

    @pytest.mark.asyncio
    async def test_rejects_unresolved_proposed_binding(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        binding_repo = AsyncMock()
        binding_repo.list_active_bindings.return_value = [(_make_binding(), BindingSetState.PROPOSED)]
        tracked_identity_repo = AsyncMock()
        service = _make_service(
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
            tracked_identity_repo=tracked_identity_repo,
        )

        with pytest.raises(IdentityBindingConflict, match="unresolved proposed binding"):
            await service.resolve_identity(SCOPE_UUID, self._request(), submission_uuid=SUBMISSION_UUID)

        binding_repo.find_confirmed_binding.assert_not_awaited()
        tracked_identity_repo.mint.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_matched_with_null_aggregate_id_when_identity_has_no_value(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        source_identity_repo.link_to_submission = AsyncMock()

        existing_binding = _make_binding()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = (existing_binding, "confirmed")

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = _make_tracked_identity("allocated")

        service: IdentityService = _make_service(
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
            tracked_identity_repo=tracked_identity_repo,
        )
        outcome: ResolutionOutcome = await service.resolve_identity(SCOPE_UUID, self._request())

        assert outcome.outcome == "matched"
        assert outcome.tracked_identity_uuid == TRACKED_UUID
        assert outcome.aggregate_id is None

    @pytest.mark.asyncio
    async def test_links_to_submission_when_provided(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        service: IdentityService = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        await service.resolve_identity(SCOPE_UUID, self._request(), submission_uuid=SUBMISSION_UUID)

        source_identity_repo.link_to_submission.assert_called_once_with(SUBMISSION_UUID, SOURCE_IDENTITY_UUID)

    @pytest.mark.asyncio
    async def test_does_not_link_when_no_submission(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        service: IdentityService = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        await service.resolve_identity(SCOPE_UUID, self._request(), submission_uuid=None)

        source_identity_repo.link_to_submission.assert_not_called()

    @pytest.mark.asyncio
    async def test_entity_type_on_outcome(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        service: IdentityService = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        outcome: ResolutionOutcome = await service.resolve_identity(SCOPE_UUID, self._request())

        assert outcome.entity_type == "site"


# ---------------------------------------------------------------------------
# resolve_batch — atomic, idempotent batch orchestration
# ---------------------------------------------------------------------------


class TestResolveBatch:
    @pytest.fixture(autouse=True)
    def _mock_transaction(self, monkeypatch) -> None:
        @contextlib.asynccontextmanager
        async def no_database_transaction():
            yield None

        monkeypatch.setattr("src.identity.service.get_connection", no_database_transaction)

    def _requests(self) -> list[ResolutionRequest]:
        return [
            ResolutionRequest(
                entity_type="site",
                primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value="ABC-001"),
            )
        ]

    @pytest.mark.asyncio
    async def test_replays_stored_result_for_same_fingerprint(self) -> None:
        stored = ResolveBatchResult(
            submission_uuid=SUBMISSION_UUID,
            scope_uuid=SCOPE_UUID,
            binding_set=BindingSetResponse(
                binding_set_uuid=BINDING_SET_UUID,
                submission_uuid=SUBMISSION_UUID,
                lifecycle_state=BindingSetState.CONFIRMED,
                change_request_name=None,
                binding_count=1,
                created_at=NOW,
            ),
            outcomes=[],
        )
        fingerprint = _request_fingerprint("test-batch", self._requests())
        resolve_batch_repo = AsyncMock()
        resolve_batch_repo.find.return_value = ResolveBatchRecord(
            scope_name="sead://reconciliation",
            run_id="run-001",
            request_fingerprint=fingerprint,
            result=stored,
            created_at=NOW,
        )

        service: IdentityService = _make_service(resolve_batch_repo=resolve_batch_repo)
        result = await service.resolve_batch("sead://reconciliation", "test-batch", "run-001", self._requests())

        assert result == stored
        resolve_batch_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_changed_payload_conflicts(self) -> None:
        resolve_batch_repo = AsyncMock()
        resolve_batch_repo.find.return_value = ResolveBatchRecord(
            scope_name="sead://reconciliation",
            run_id="run-001",
            request_fingerprint="stale-fingerprint",
            result=ResolveBatchResult(
                submission_uuid=SUBMISSION_UUID,
                scope_uuid=SCOPE_UUID,
                binding_set=BindingSetResponse(
                    binding_set_uuid=BINDING_SET_UUID,
                    submission_uuid=SUBMISSION_UUID,
                    lifecycle_state=BindingSetState.CONFIRMED,
                    change_request_name=None,
                    binding_count=1,
                    created_at=NOW,
                ),
                outcomes=[],
            ),
            created_at=NOW,
        )

        service: IdentityService = _make_service(resolve_batch_repo=resolve_batch_repo)
        with pytest.raises(IdentityBatchConflict, match="different payload"):
            await service.resolve_batch("sead://reconciliation", "test-batch", "run-001", self._requests())

    @pytest.mark.asyncio
    async def test_persists_result_after_successful_batch(self) -> None:
        scope_repo = AsyncMock()
        scope_repo.get_by_name.return_value = None
        scope_repo.create.return_value = SourceScope(scope_uuid=SCOPE_UUID, scope_name="sead://reconciliation", created_at=NOW)
        submission_repo = AsyncMock()
        submission_repo.create.return_value = MagicMock(submission_uuid=SUBMISSION_UUID)

        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()

        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        tracked_identity_repo = AsyncMock()
        tracked = _make_tracked_identity("allocated")
        tracked.aggregate_id = 9001
        tracked_identity_repo.mint.return_value = tracked

        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")

        resolve_batch_repo = AsyncMock()
        resolve_batch_repo.find.return_value = None

        service: IdentityService = _make_service(
            scope_repo=scope_repo,
            submission_repo=submission_repo,
            source_identity_repo=source_identity_repo,
            tracked_identity_repo=tracked_identity_repo,
            binding_set_repo=binding_set_repo,
            binding_repo=binding_repo,
            resolve_batch_repo=resolve_batch_repo,
        )

        result = await service.resolve_batch("sead://reconciliation", "test-batch", "run-001", self._requests())

        resolve_batch_repo.acquire_run_lock.assert_awaited_once_with("sead://reconciliation", "run-001")
        resolve_batch_repo.create.assert_awaited_once()
        assert result.submission_uuid == SUBMISSION_UUID
        assert result.outcomes[0].aggregate_id == 9001


# ---------------------------------------------------------------------------
# bind
# ---------------------------------------------------------------------------


class TestBind:
    @pytest.fixture(autouse=True)
    def _mock_transaction(self, monkeypatch) -> None:
        @contextlib.asynccontextmanager
        async def no_database_transaction():
            yield None

        monkeypatch.setattr("src.identity.service.get_connection", no_database_transaction)

    def _new_outcome(self) -> ResolutionOutcome:
        return ResolutionOutcome(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            entity_type="site",
            outcome="new",
            tracked_identity_uuid=None,
        )

    def _matched_outcome(self) -> ResolutionOutcome:
        return ResolutionOutcome(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            entity_type="site",
            outcome="matched",
            tracked_identity_uuid=TRACKED_UUID,
        )

    @pytest.mark.asyncio
    async def test_bind_new_outcome_mints_tracked_identity(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.mint.return_value = _make_tracked_identity("allocated")

        source_identity_repo = AsyncMock()
        source_identity_repo.get.return_value = _make_source_identity()

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("allocated")

        service: IdentityService = _make_service(
            binding_set_repo=binding_set_repo,
            tracked_identity_repo=tracked_identity_repo,
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
        )
        result: BindingSetResponse = await service.bind(SUBMISSION_UUID, [self._new_outcome()])

        tracked_identity_repo.mint.assert_called_once_with(entity_type="site", created_by=None)
        assert isinstance(result, BindingSetResponse)

    @pytest.mark.asyncio
    async def test_bind_new_outcome_populates_aggregate_fields_from_tracked_identity(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")

        tracked_identity = _make_tracked_identity("materialized")
        tracked_identity.aggregate_id = 4321
        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.mint.return_value = tracked_identity

        source_identity_repo = AsyncMock()
        source_identity_repo.get.return_value = _make_source_identity()

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("allocated")

        outcome = self._new_outcome()
        service: IdentityService = _make_service(
            binding_set_repo=binding_set_repo,
            tracked_identity_repo=tracked_identity_repo,
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
        )

        await service.bind(SUBMISSION_UUID, [outcome])

        assert outcome.tracked_identity_uuid == TRACKED_UUID
        assert outcome.aggregate_id == 4321

    @pytest.mark.asyncio
    async def test_bind_new_outcome_auto_confirms_for_provider_owned(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.mint.return_value = _make_tracked_identity()

        source_identity_repo = AsyncMock()
        source_identity_repo.get.return_value = _make_source_identity()

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("allocated")

        service: IdentityService = _make_service(
            binding_set_repo=binding_set_repo,
            tracked_identity_repo=tracked_identity_repo,
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
        )
        result = await service.bind(SUBMISSION_UUID, [self._new_outcome()])

        binding_set_repo.transition.assert_called_once_with(BINDING_SET_UUID, BindingSetState.CONFIRMED)
        assert result.lifecycle_state == BindingSetState.CONFIRMED

    @pytest.mark.asyncio
    async def test_bind_does_not_auto_confirm_for_shared_metadata(self) -> None:
        policy = _mock_policy(side_effect=_shared_metadata_policy)
        outcome = ResolutionOutcome(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            entity_type="taxa",
            outcome="matched",
            tracked_identity_uuid=TRACKED_UUID,
        )

        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")

        source_identity_repo = AsyncMock()
        source_identity_repo.get.return_value = _make_source_identity()

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("business_key")

        service: IdentityService = _make_service(
            binding_set_repo=binding_set_repo,
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
            policy=policy,
        )
        result = await service.bind(SUBMISSION_UUID, [outcome])

        # transition should NOT be called since auto_confirm=False
        binding_set_repo.transition.assert_not_called()
        assert result.lifecycle_state == BindingSetState.PROPOSED

    @pytest.mark.asyncio
    async def test_bind_matched_outcome_uses_existing_tracked_identity(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")

        source_identity_repo = AsyncMock()
        source_identity_repo.get.return_value = _make_source_identity()

        tracked_identity_repo = AsyncMock()

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("business_key")

        service: IdentityService = _make_service(
            binding_set_repo=binding_set_repo,
            source_identity_repo=source_identity_repo,
            tracked_identity_repo=tracked_identity_repo,
            binding_repo=binding_repo,
        )
        await service.bind(SUBMISSION_UUID, [self._matched_outcome()])

        # Should NOT mint a new tracked identity
        tracked_identity_repo.mint.assert_not_called()
        # Should create a binding to the existing TRACKED_UUID
        call_kwargs = binding_repo.create.call_args.kwargs
        assert call_kwargs["tracked_identity_uuid"] == TRACKED_UUID

    @pytest.mark.asyncio
    async def test_bind_allocation_blocked_by_policy_skips_binding(self) -> None:
        policy = _mock_policy(
            side_effect=lambda et: EntityPolicy(
                entity_type=et,
                entity_subtype="shared_metadata",
                accept_uuid=True,
                allow_allocation=False,  # ← blocked
                auto_confirm=False,
            )
        )
        outcome = ResolutionOutcome(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            entity_type="taxa",
            outcome="new",
            tracked_identity_uuid=None,
        )

        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")

        tracked_identity_repo = AsyncMock()
        binding_repo = AsyncMock()

        service: IdentityService = _make_service(
            binding_set_repo=binding_set_repo,
            tracked_identity_repo=tracked_identity_repo,
            binding_repo=binding_repo,
            policy=policy,
        )
        result: BindingSetResponse = await service.bind(SUBMISSION_UUID, [outcome])

        tracked_identity_repo.mint.assert_not_called()
        binding_repo.create.assert_not_called()
        assert result.binding_count == 0

    @pytest.mark.asyncio
    async def test_bind_raises_on_empty_outcomes(self) -> None:
        service = _make_service()
        with pytest.raises(ValueError, match="at least one"):
            await service.bind(SUBMISSION_UUID, [])

    @pytest.mark.asyncio
    async def test_bind_reuses_confirmed_identity_for_stale_new_outcome(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")
        existing_binding = _make_binding()
        binding_repo = AsyncMock()
        binding_repo.list_active_bindings.return_value = [(existing_binding, BindingSetState.CONFIRMED)]
        binding_repo.create.return_value = existing_binding
        tracked = _make_tracked_identity("allocated")
        tracked.aggregate_id = 4321
        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = tracked

        outcome = self._new_outcome()
        service = _make_service(
            binding_repo=binding_repo,
            binding_set_repo=binding_set_repo,
            tracked_identity_repo=tracked_identity_repo,
        )
        await service.bind(SUBMISSION_UUID, [outcome])

        tracked_identity_repo.mint.assert_not_awaited()
        assert outcome.outcome == "matched"
        assert outcome.tracked_identity_uuid == TRACKED_UUID
        assert outcome.aggregate_id == 4321
        assert binding_repo.create.await_args.kwargs["tracked_identity_uuid"] == TRACKED_UUID

    @pytest.mark.asyncio
    async def test_bind_rejects_proposed_binding_before_creating_set_or_allocating(self) -> None:
        binding_set_repo = AsyncMock()
        binding_repo = AsyncMock()
        binding_repo.list_active_bindings.return_value = [(_make_binding(), BindingSetState.PROPOSED)]
        tracked_identity_repo = AsyncMock()
        service = _make_service(
            binding_repo=binding_repo,
            binding_set_repo=binding_set_repo,
            tracked_identity_repo=tracked_identity_repo,
        )

        with pytest.raises(IdentityBindingConflict, match="unresolved proposed binding"):
            await service.bind(SUBMISSION_UUID, [self._new_outcome()])

        binding_set_repo.create.assert_not_awaited()
        tracked_identity_repo.mint.assert_not_awaited()
        binding_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_binding_method_is_business_key_for_business_key_identity(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")

        source_identity_repo = AsyncMock()
        source_identity_repo.get.return_value = _make_source_identity()

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("business_key")

        outcome = ResolutionOutcome(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            entity_type="site",
            outcome="matched",
            tracked_identity_uuid=TRACKED_UUID,
        )
        service: IdentityService = _make_service(
            binding_set_repo=binding_set_repo,
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
        )
        await service.bind(SUBMISSION_UUID, [outcome])

        call_kwargs = binding_repo.create.call_args.kwargs
        assert call_kwargs["method"] == BindingMethod.BUSINESS_KEY

    @pytest.mark.asyncio
    async def test_binding_method_is_uuid_accepted_for_uuid_identity(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")

        source_identity_repo = AsyncMock()
        source_identity_repo.get.return_value = SourceIdentity(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            scope_uuid=SCOPE_UUID,
            entity_type="site",
            created_at=NOW,
            keys=[
                SourceIdentityKey(
                    key_uuid=uuid4(),
                    source_identity_uuid=SOURCE_IDENTITY_UUID,
                    key_type=IdentityType.UUID,
                    key_value="550e8400-e29b-41d4-a716-446655440000",
                )
            ],
        )

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("uuid_accepted")

        outcome = ResolutionOutcome(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            entity_type="site",
            outcome="matched",
            tracked_identity_uuid=TRACKED_UUID,
        )
        service: IdentityService = _make_service(
            binding_set_repo=binding_set_repo,
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
        )
        await service.bind(SUBMISSION_UUID, [outcome])

        call_kwargs = binding_repo.create.call_args.kwargs
        assert call_kwargs["method"] == BindingMethod.UUID_ACCEPTED


# ---------------------------------------------------------------------------
# confirm_binding_set
# ---------------------------------------------------------------------------


class TestConfirmBindingSet:
    @pytest.mark.asyncio
    async def test_confirm_calls_transition(self) -> None:
        confirmed_set = _make_binding_set("confirmed")
        binding_set_repo = AsyncMock()
        binding_set_repo.transition.return_value = confirmed_set

        service: IdentityService = _make_service(binding_set_repo=binding_set_repo)
        result: BindingSet | None = await service.confirm_binding_set(BINDING_SET_UUID)

        binding_set_repo.transition.assert_called_once_with(BINDING_SET_UUID, BindingSetState.CONFIRMED)
        assert result is confirmed_set

    @pytest.mark.asyncio
    async def test_confirm_returns_none_when_not_found(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.transition.return_value = None

        service: IdentityService = _make_service(binding_set_repo=binding_set_repo)
        result: BindingSet | None = await service.confirm_binding_set(BINDING_SET_UUID)

        assert result is None


# ---------------------------------------------------------------------------
# associate_change_request
# ---------------------------------------------------------------------------


class TestAssociateChangeRequest:
    @pytest.mark.asyncio
    async def test_associates_cr_name(self) -> None:
        updated_set = _make_binding_set("confirmed")
        updated_set = BindingSet(**{**updated_set.model_dump(), "change_request_name": "2026-04-04-add-site"})
        binding_set_repo = AsyncMock()
        binding_set_repo.associate_change_request.return_value = updated_set

        service: IdentityService = _make_service(binding_set_repo=binding_set_repo)
        result: BindingSet | None = await service.associate_change_request(BINDING_SET_UUID, "2026-04-04-add-site")

        binding_set_repo.associate_change_request.assert_called_once_with(BINDING_SET_UUID, "2026-04-04-add-site")
        assert result is not None
        assert result.change_request_name == "2026-04-04-add-site"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found_or_not_confirmed(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.associate_change_request.return_value = None

        service: IdentityService = _make_service(binding_set_repo=binding_set_repo)
        result: BindingSet | None = await service.associate_change_request(BINDING_SET_UUID, "some-cr")

        assert result is None


# ---------------------------------------------------------------------------
# detect_change
# ---------------------------------------------------------------------------


class TestDetectChange:
    def _request(self, content_hash: str = "abc123") -> ChangeDetectionRequest:
        return ChangeDetectionRequest(
            tracked_identity_uuid=TRACKED_UUID,
            content_hash=content_hash,
        )

    @pytest.mark.asyncio
    async def test_insert_when_no_prior_hash(self) -> None:
        tracked = _make_tracked_identity()
        tracked.content_hash = None

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = tracked

        service: IdentityService = _make_service(tracked_identity_repo=tracked_identity_repo)
        result: ChangeDetectionResult = await service.detect_change(self._request("abc123"))

        assert result.outcome == ChangeOutcome.INSERT
        assert result.previous_hash is None
        tracked_identity_repo.update_content_hash.assert_called_once_with(TRACKED_UUID, "abc123")

    @pytest.mark.asyncio
    async def test_skip_when_hash_unchanged(self) -> None:
        tracked = _make_tracked_identity()
        tracked.content_hash = "abc123"

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = tracked

        service: IdentityService = _make_service(tracked_identity_repo=tracked_identity_repo)
        result: ChangeDetectionResult = await service.detect_change(self._request("abc123"))

        assert result.outcome == ChangeOutcome.SKIP
        assert result.previous_hash == "abc123"
        tracked_identity_repo.update_content_hash.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_when_hash_differs(self) -> None:
        tracked = _make_tracked_identity()
        tracked.content_hash = "old_hash"

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = tracked

        service: IdentityService = _make_service(tracked_identity_repo=tracked_identity_repo)
        result: ChangeDetectionResult = await service.detect_change(self._request("new_hash"))

        assert result.outcome == ChangeOutcome.UPDATE
        assert result.previous_hash == "old_hash"
        tracked_identity_repo.update_content_hash.assert_called_once_with(TRACKED_UUID, "new_hash")

    @pytest.mark.asyncio
    async def test_raises_when_tracked_identity_not_found(self) -> None:
        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = None

        service: IdentityService = _make_service(tracked_identity_repo=tracked_identity_repo)
        with pytest.raises(LookupError, match=str(TRACKED_UUID)):
            await service.detect_change(self._request("abc123"))


# ---------------------------------------------------------------------------
# get_binding_set
# ---------------------------------------------------------------------------


class TestGetBindingSet:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.get.return_value = None

        service: IdentityService = _make_service(binding_set_repo=binding_set_repo)
        result: BindingSetResponse | None = await service.get_binding_set(BINDING_SET_UUID)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_response_with_binding_count(self) -> None:
        bs = _make_binding_set("confirmed")
        binding_set_repo = AsyncMock()
        binding_set_repo.get.return_value = bs

        binding_repo = AsyncMock()
        binding_repo.list_by_set.return_value = [_make_binding(), _make_binding()]

        service: IdentityService = _make_service(binding_set_repo=binding_set_repo, binding_repo=binding_repo)
        result: BindingSetResponse | None = await service.get_binding_set(BINDING_SET_UUID)

        assert result is not None
        assert result.binding_count == 2
        assert result.lifecycle_state == BindingSetState.CONFIRMED
