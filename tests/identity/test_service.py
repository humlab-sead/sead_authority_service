"""Unit tests for IdentityService — no database required.

All repositories and the policy are replaced with AsyncMock / MagicMock
instances. This tests the service orchestration logic in isolation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
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
    SourceIdentity,
    SourceScope,
)
from src.identity.policy import EntityPolicy, IdentityPolicy
from src.identity.types import (
    BindingMethod,
    BindingSetState,
    ChangeOutcome,
    IdentityType,
    SubmissionStatus,
    TrackedIdentityState,
)

NOW = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Test fixtures & helpers
# ---------------------------------------------------------------------------

SCOPE_UUID = uuid4()
SUBMISSION_UUID = uuid4()
SOURCE_IDENTITY_UUID = uuid4()
TRACKED_UUID = uuid4()
BINDING_SET_UUID = uuid4()
BINDING_UUID = uuid4()


def _make_source_identity(identity_type: str = "business_key") -> SourceIdentity:
    return SourceIdentity(
        source_identity_uuid=SOURCE_IDENTITY_UUID,
        scope_uuid=SCOPE_UUID,
        entity_type="site",
        identity_type=IdentityType(identity_type),
        identity_value="ABC-001",
        created_at=NOW,
    )


def _make_tracked_identity(state: str = "allocated") -> MagicMock:
    t = MagicMock()
    t.tracked_identity_uuid = TRACKED_UUID
    t.entity_type = "site"
    t.lifecycle_state = TrackedIdentityState(state)
    t.content_hash = None
    return t


def _make_binding(method: str = "business_key") -> Binding:
    return Binding(
        binding_uuid=BINDING_UUID,
        binding_set_uuid=BINDING_SET_UUID,
        source_identity_uuid=SOURCE_IDENTITY_UUID,
        tracked_identity_uuid=TRACKED_UUID,
        method=BindingMethod(method),
        created_at=NOW,
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
    policy.get_entity_policy = MagicMock(side_effect=side_effect or (lambda et: _provider_owned_policy(et)))
    return policy


def _make_service(
    scope_repo=None,
    submission_repo=None,
    source_identity_repo=None,
    tracked_identity_repo=None,
    binding_set_repo=None,
    binding_repo=None,
    policy=None,
):
    from src.identity.service import IdentityService

    return IdentityService(
        scope_repo=scope_repo or AsyncMock(),
        submission_repo=submission_repo or AsyncMock(),
        source_identity_repo=source_identity_repo or AsyncMock(),
        tracked_identity_repo=tracked_identity_repo or AsyncMock(),
        binding_set_repo=binding_set_repo or AsyncMock(),
        binding_repo=binding_repo or AsyncMock(),
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

        service = _make_service(scope_repo=scope_repo)
        result = await service.get_or_create_scope("sead://admin")

        assert result.scope_name == "sead://admin"
        scope_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_scope_if_missing(self) -> None:
        new_scope = SourceScope(scope_uuid=SCOPE_UUID, scope_name="test://new", created_at=NOW)
        scope_repo = AsyncMock()
        scope_repo.get_by_name.return_value = None
        scope_repo.create.return_value = new_scope

        service = _make_service(scope_repo=scope_repo)
        result = await service.get_or_create_scope("test://new")

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
    async def test_returns_new_when_no_existing_binding(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        source_identity_repo.link_to_submission = AsyncMock()

        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        service = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        outcome = await service.resolve_identity(SCOPE_UUID, self._request(), submission_uuid=SUBMISSION_UUID)

        assert outcome.outcome == "new"
        assert outcome.tracked_identity_uuid is None
        assert outcome.source_identity_uuid == SOURCE_IDENTITY_UUID

    @pytest.mark.asyncio
    async def test_returns_matched_when_binding_exists(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        source_identity_repo.link_to_submission = AsyncMock()

        existing_binding = _make_binding()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = (existing_binding, "confirmed")

        service = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        outcome = await service.resolve_identity(SCOPE_UUID, self._request())

        assert outcome.outcome == "matched"
        assert outcome.tracked_identity_uuid == TRACKED_UUID

    @pytest.mark.asyncio
    async def test_links_to_submission_when_provided(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        service = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        await service.resolve_identity(SCOPE_UUID, self._request(), submission_uuid=SUBMISSION_UUID)

        source_identity_repo.link_to_submission.assert_called_once_with(SUBMISSION_UUID, SOURCE_IDENTITY_UUID)

    @pytest.mark.asyncio
    async def test_does_not_link_when_no_submission(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        service = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        await service.resolve_identity(SCOPE_UUID, self._request(), submission_uuid=None)

        source_identity_repo.link_to_submission.assert_not_called()

    @pytest.mark.asyncio
    async def test_entity_type_on_outcome(self) -> None:
        source_identity_repo = AsyncMock()
        source_identity_repo.create_or_get.return_value = _make_source_identity()
        binding_repo = AsyncMock()
        binding_repo.find_confirmed_binding.return_value = None

        service = _make_service(source_identity_repo=source_identity_repo, binding_repo=binding_repo)
        outcome = await service.resolve_identity(SCOPE_UUID, self._request())

        assert outcome.entity_type == "site"


# ---------------------------------------------------------------------------
# bind
# ---------------------------------------------------------------------------


class TestBind:
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

        service = _make_service(
            binding_set_repo=binding_set_repo,
            tracked_identity_repo=tracked_identity_repo,
            source_identity_repo=source_identity_repo,
            binding_repo=binding_repo,
        )
        result = await service.bind(SUBMISSION_UUID, [self._new_outcome()])

        tracked_identity_repo.mint.assert_called_once_with(entity_type="site", created_by=None)
        assert isinstance(result, BindingSetResponse)

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

        service = _make_service(
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
        policy = _mock_policy(side_effect=lambda et: _shared_metadata_policy(et))
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

        service = _make_service(
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

        service = _make_service(
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

        service = _make_service(
            binding_set_repo=binding_set_repo,
            tracked_identity_repo=tracked_identity_repo,
            binding_repo=binding_repo,
            policy=policy,
        )
        result = await service.bind(SUBMISSION_UUID, [outcome])

        tracked_identity_repo.mint.assert_not_called()
        binding_repo.create.assert_not_called()
        assert result.binding_count == 0

    @pytest.mark.asyncio
    async def test_bind_raises_on_empty_outcomes(self) -> None:
        service = _make_service()
        with pytest.raises(ValueError, match="at least one"):
            await service.bind(SUBMISSION_UUID, [])

    @pytest.mark.asyncio
    async def test_binding_method_is_business_key_for_business_key_identity(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.create.return_value = _make_binding_set("proposed")
        binding_set_repo.transition.return_value = _make_binding_set("confirmed")

        source_identity_repo = AsyncMock()
        source_identity_repo.get.return_value = _make_source_identity("business_key")

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("business_key")

        outcome = ResolutionOutcome(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            entity_type="site",
            outcome="matched",
            tracked_identity_uuid=TRACKED_UUID,
        )
        service = _make_service(
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
        source_identity_repo.get.return_value = _make_source_identity("uuid")

        binding_repo = AsyncMock()
        binding_repo.create.return_value = _make_binding("uuid_accepted")

        outcome = ResolutionOutcome(
            source_identity_uuid=SOURCE_IDENTITY_UUID,
            entity_type="site",
            outcome="matched",
            tracked_identity_uuid=TRACKED_UUID,
        )
        service = _make_service(
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

        service = _make_service(binding_set_repo=binding_set_repo)
        result = await service.confirm_binding_set(BINDING_SET_UUID)

        binding_set_repo.transition.assert_called_once_with(BINDING_SET_UUID, BindingSetState.CONFIRMED)
        assert result is confirmed_set

    @pytest.mark.asyncio
    async def test_confirm_returns_none_when_not_found(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.transition.return_value = None

        service = _make_service(binding_set_repo=binding_set_repo)
        result = await service.confirm_binding_set(BINDING_SET_UUID)

        assert result is None


# ---------------------------------------------------------------------------
# associate_change_request
# ---------------------------------------------------------------------------


class TestAssociateChangeRequest:
    @pytest.mark.asyncio
    async def test_associates_cr_name(self) -> None:
        updated_set = _make_binding_set("confirmed")
        updated_set = BindingSet(
            **{**updated_set.model_dump(), "change_request_name": "2026-04-04-add-site"}
        )
        binding_set_repo = AsyncMock()
        binding_set_repo.associate_change_request.return_value = updated_set

        service = _make_service(binding_set_repo=binding_set_repo)
        result = await service.associate_change_request(BINDING_SET_UUID, "2026-04-04-add-site")

        binding_set_repo.associate_change_request.assert_called_once_with(BINDING_SET_UUID, "2026-04-04-add-site")
        assert result.change_request_name == "2026-04-04-add-site"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found_or_not_confirmed(self) -> None:
        binding_set_repo = AsyncMock()
        binding_set_repo.associate_change_request.return_value = None

        service = _make_service(binding_set_repo=binding_set_repo)
        result = await service.associate_change_request(BINDING_SET_UUID, "some-cr")

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

        service = _make_service(tracked_identity_repo=tracked_identity_repo)
        result = await service.detect_change(self._request("abc123"))

        assert result.outcome == ChangeOutcome.INSERT
        assert result.previous_hash is None
        tracked_identity_repo.update_content_hash.assert_called_once_with(TRACKED_UUID, "abc123")

    @pytest.mark.asyncio
    async def test_skip_when_hash_unchanged(self) -> None:
        tracked = _make_tracked_identity()
        tracked.content_hash = "abc123"

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = tracked

        service = _make_service(tracked_identity_repo=tracked_identity_repo)
        result = await service.detect_change(self._request("abc123"))

        assert result.outcome == ChangeOutcome.SKIP
        assert result.previous_hash == "abc123"
        tracked_identity_repo.update_content_hash.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_when_hash_differs(self) -> None:
        tracked = _make_tracked_identity()
        tracked.content_hash = "old_hash"

        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = tracked

        service = _make_service(tracked_identity_repo=tracked_identity_repo)
        result = await service.detect_change(self._request("new_hash"))

        assert result.outcome == ChangeOutcome.UPDATE
        assert result.previous_hash == "old_hash"
        tracked_identity_repo.update_content_hash.assert_called_once_with(TRACKED_UUID, "new_hash")

    @pytest.mark.asyncio
    async def test_raises_when_tracked_identity_not_found(self) -> None:
        tracked_identity_repo = AsyncMock()
        tracked_identity_repo.get.return_value = None

        service = _make_service(tracked_identity_repo=tracked_identity_repo)
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

        service = _make_service(binding_set_repo=binding_set_repo)
        result = await service.get_binding_set(BINDING_SET_UUID)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_response_with_binding_count(self) -> None:
        bs = _make_binding_set("confirmed")
        binding_set_repo = AsyncMock()
        binding_set_repo.get.return_value = bs

        binding_repo = AsyncMock()
        binding_repo.list_by_set.return_value = [_make_binding(), _make_binding()]

        service = _make_service(binding_set_repo=binding_set_repo, binding_repo=binding_repo)
        result = await service.get_binding_set(BINDING_SET_UUID)

        assert result is not None
        assert result.binding_count == 2
        assert result.lifecycle_state == BindingSetState.CONFIRMED
