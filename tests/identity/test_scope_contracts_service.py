"""Unit tests for provider-scope contract operations on IdentityService.

Repositories are replaced with AsyncMock instances and the database connection
is patched, so no live database is required.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.identity.contracts import IdentityContractConflict, IdentityContractRequired
from src.identity.models import (
    BindingSetResponse,
    EntityContractDeclaration,
    EntityKeyContract,
    IdentitySignal,
    ResolutionOutcome,
    ResolutionRequest,
    SourceScope,
)
from src.identity.service import IdentityService
from src.identity.types import BindingSetState, IdentityType

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)

SCOPE_UUID: UUID = uuid4()
PROVIDER_SCOPE = "provider://gbif/occurrence"
INTERNAL_SCOPE = "sead://reconciliation"


@contextlib.asynccontextmanager
async def _fake_get_connection():
    """Stand in for the shared connection context manager."""
    yield MagicMock()


def _patch_connection():
    return patch(
        "src.identity.service.get_connection",
        side_effect=lambda: _fake_get_connection(),  # pylint: disable=unnecessary-lambda
    )


def _make_contract(entity_type: str, business_keys: list[str]) -> EntityKeyContract:
    return EntityKeyContract(
        contract_uuid=uuid4(),
        scope_uuid=SCOPE_UUID,
        entity_type=entity_type,
        business_keys=business_keys,
        created_at=NOW,
    )


def _make_service(registered: list[EntityKeyContract] | None = None, *, scope_exists: bool = False) -> IdentityService:
    scope_repo = AsyncMock()
    scope_repo.get_by_name = AsyncMock(
        return_value=SourceScope(scope_uuid=SCOPE_UUID, scope_name=PROVIDER_SCOPE, created_at=NOW) if scope_exists else None
    )
    scope_repo.create = AsyncMock(return_value=SourceScope(scope_uuid=SCOPE_UUID, scope_name=PROVIDER_SCOPE, created_at=NOW))

    contract_repo = AsyncMock()
    contract_repo.lock_scope = AsyncMock(return_value=None)
    contract_repo.list_by_scope = AsyncMock(return_value=list(registered or []))
    contract_repo.list_by_scope_name = AsyncMock(return_value=list(registered or []))
    contract_repo.create = AsyncMock(
        side_effect=lambda scope_uuid, entity_type, business_keys, created_by=None: _make_contract(entity_type, list(business_keys))
    )

    return IdentityService(
        scope_repo=scope_repo,
        contract_repo=contract_repo,
        submission_repo=AsyncMock(),
        source_identity_repo=AsyncMock(),
        tracked_identity_repo=AsyncMock(),
        binding_set_repo=AsyncMock(),
        binding_repo=AsyncMock(),
        resolve_batch_repo=AsyncMock(),
        policy=MagicMock(),
    )


def _declaration(entity_type: str, keys: list[str]) -> EntityContractDeclaration:
    return EntityContractDeclaration(entity_type=entity_type, business_keys=keys)


# ---------------------------------------------------------------------------
# register_scope_contracts
# ---------------------------------------------------------------------------


class TestRegisterScopeContracts:
    @pytest.mark.asyncio
    async def test_creates_missing_scope_and_contract(self) -> None:
        service = _make_service()
        with _patch_connection():
            result = await service.register_scope_contracts(
                PROVIDER_SCOPE,
                [_declaration("site", ["site_name", "country"])],
                created_by="shape-shifter",
            )

        assert result.scope_name == PROVIDER_SCOPE
        assert result.scope_uuid == SCOPE_UUID
        assert [state.state for state in result.entities] == ["created"]
        assert result.entities[0].business_keys == ["site_name", "country"]
        service.contract_repo.create.assert_awaited_once_with(
            scope_uuid=SCOPE_UUID,
            entity_type="site",
            business_keys=["site_name", "country"],
            created_by="shape-shifter",
        )
        service.contract_repo.lock_scope.assert_awaited_once_with(SCOPE_UUID)

    @pytest.mark.asyncio
    async def test_repeated_identical_registration_is_idempotent(self) -> None:
        registered = [_make_contract("site", ["site_name", "country"])]
        service = _make_service(registered, scope_exists=True)
        with _patch_connection():
            result = await service.register_scope_contracts(PROVIDER_SCOPE, [_declaration("site", ["site_name", "country"])])

        assert [state.state for state in result.entities] == ["existing"]
        service.contract_repo.create.assert_not_awaited()
        service.scope_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_different_key_order_is_a_conflict_without_writes(self) -> None:
        registered = [_make_contract("site", ["site_name", "country"])]
        service = _make_service(registered, scope_exists=True)

        with _patch_connection(), pytest.raises(IdentityContractConflict) as excinfo:
            await service.register_scope_contracts(PROVIDER_SCOPE, [_declaration("site", ["country", "site_name"])])

        assert excinfo.value.conflicts[0].entity_type == "site"
        assert excinfo.value.conflicts[0].registered == ["site_name", "country"]
        assert excinfo.value.conflicts[0].submitted == ["country", "site_name"]
        service.contract_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_one_conflict_blocks_creation_of_other_entities(self) -> None:
        registered = [_make_contract("site", ["site_name"])]
        service = _make_service(registered, scope_exists=True)

        with _patch_connection(), pytest.raises(IdentityContractConflict):
            await service.register_scope_contracts(
                PROVIDER_SCOPE,
                [_declaration("site", ["site_name", "country"]), _declaration("sample_group", ["sample_group_name"])],
            )

        service.contract_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_entities_are_created_next_to_existing_ones(self) -> None:
        registered = [_make_contract("site", ["site_name"])]
        service = _make_service(registered, scope_exists=True)

        with _patch_connection():
            result = await service.register_scope_contracts(
                PROVIDER_SCOPE,
                [_declaration("site", ["site_name"]), _declaration("sample_group", ["sample_group_name"])],
            )

        assert [(state.entity_type, state.state) for state in result.entities] == [
            ("site", "existing"),
            ("sample_group", "created"),
        ]
        service.contract_repo.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_internal_scope_registration_is_rejected(self) -> None:
        service = _make_service()

        with _patch_connection(), pytest.raises(ValueError, match="provider scopes only"):
            await service.register_scope_contracts(INTERNAL_SCOPE, [_declaration("site", ["site_name"])])

        service.contract_repo.lock_scope.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_repeated_entity_type_in_request_is_rejected(self) -> None:
        service = _make_service()

        with _patch_connection(), pytest.raises(ValueError, match="more than once"):
            await service.register_scope_contracts(
                PROVIDER_SCOPE,
                [_declaration("site", ["site_name"]), _declaration("site", ["other_key"])],
            )

        service.scope_repo.get_by_name.assert_not_awaited()


# ---------------------------------------------------------------------------
# require_registered_contracts
# ---------------------------------------------------------------------------


class TestRequireRegisteredContracts:
    @pytest.mark.asyncio
    async def test_internal_scope_needs_no_contract(self) -> None:
        service = _make_service()

        await service.require_registered_contracts(INTERNAL_SCOPE, ["site"])

        service.contract_repo.list_by_scope_name.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_provider_scope_with_complete_contracts_passes(self) -> None:
        service = _make_service([_make_contract("site", ["site_name"]), _make_contract("sample_group", ["sample_group_name"])])

        await service.require_registered_contracts(PROVIDER_SCOPE, ["site", "sample_group", "site"])

        service.contract_repo.list_by_scope_name.assert_awaited_once_with(PROVIDER_SCOPE)

    @pytest.mark.asyncio
    async def test_provider_scope_without_contract_is_rejected(self) -> None:
        service = _make_service([])

        with pytest.raises(IdentityContractRequired) as excinfo:
            await service.require_registered_contracts(PROVIDER_SCOPE, ["site", "sample_group"])

        assert excinfo.value.missing_entity_types == ["site", "sample_group"]

    @pytest.mark.asyncio
    async def test_only_missing_entity_types_are_reported(self) -> None:
        service = _make_service([_make_contract("site", ["site_name"])])

        with pytest.raises(IdentityContractRequired) as excinfo:
            await service.require_registered_contracts(PROVIDER_SCOPE, ["site", "sample_group"])

        assert excinfo.value.missing_entity_types == ["sample_group"]


# ---------------------------------------------------------------------------
# resolve_batch enforcement
# ---------------------------------------------------------------------------


class TestResolveBatchContractEnforcement:
    @staticmethod
    def _request(entity_type: str = "site") -> ResolutionRequest:
        return ResolutionRequest(
            entity_type=entity_type,
            primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value="label"),
        )

    @pytest.mark.asyncio
    async def test_provider_batch_without_contract_stops_before_writes(self) -> None:
        service = _make_service([])

        with _patch_connection(), pytest.raises(IdentityContractRequired):
            await service.resolve_batch(PROVIDER_SCOPE, "batch", "run-1", [self._request()])

        service.resolve_batch_repo.find.assert_not_awaited()
        service.submission_repo.create.assert_not_awaited()
        service.source_identity_repo.create_or_get.assert_not_awaited()
        service.binding_set_repo.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_padded_provider_scope_is_normalized_before_lookup_and_write(self) -> None:
        service = _make_service([_make_contract("site", ["site_name"])])
        service.resolve_batch_repo.find.return_value = None
        service.get_or_create_scope = AsyncMock(return_value=SourceScope(scope_uuid=SCOPE_UUID, scope_name=PROVIDER_SCOPE, created_at=NOW))
        service.create_submission = AsyncMock(return_value=MagicMock(submission_uuid=SCOPE_UUID))
        service.resolve_identity = AsyncMock(
            return_value=ResolutionOutcome(source_identity_uuid=uuid4(), entity_type="site", outcome="matched")
        )
        service.bind = AsyncMock(
            return_value=BindingSetResponse(
                binding_set_uuid=uuid4(),
                submission_uuid=SCOPE_UUID,
                lifecycle_state=BindingSetState.CONFIRMED,
                change_request_name=None,
                binding_count=1,
                created_at=NOW,
            )
        )

        with _patch_connection():
            await service.resolve_batch(f" {PROVIDER_SCOPE} ", "batch", "run-1", [self._request()])

        service.resolve_batch_repo.acquire_run_lock.assert_awaited_once_with(PROVIDER_SCOPE, "run-1")
        service.contract_repo.list_by_scope_name.assert_awaited_once_with(PROVIDER_SCOPE)
        service.resolve_batch_repo.find.assert_awaited_once_with(PROVIDER_SCOPE, "run-1")
        service.get_or_create_scope.assert_awaited_once_with(PROVIDER_SCOPE, created_by=None)
        assert service.resolve_batch_repo.create.await_args.args[0] == PROVIDER_SCOPE
