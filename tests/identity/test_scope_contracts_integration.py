"""Integration tests for provider-scope business-key contracts.

These tests exercise the full stack: service → repository → PostgreSQL. They
are skipped unless the helper-owned disposable database is configured
(``SIMS_INTEGRATION_DB=1``).

Run with:
    SIMS_INTEGRATION_DB=1 uv run pytest tests/identity/test_scope_contracts_integration.py

Requirements:
    - PostgreSQL with the sead_identity schema applied, including
      ``schema/sql/identity/012_scope_entity_contracts.sql``
"""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from src.identity.contracts import IdentityContractConflict, IdentityContractRequired
from src.identity.models import EntityContractDeclaration, IdentitySignal, ResolutionRequest
from src.identity.service import IdentityService
from src.identity.types import IdentityType

_SKIP_REASON = (
    "Integration test requires a live PostgreSQL database with the sead_identity schema. "
    "Set SIMS_INTEGRATION_DB=1 and configure tests/config/config.yml to enable."
)
_RUN_INTEGRATION = os.environ.get("SIMS_INTEGRATION_DB", "0") == "1"
pytestmark = pytest.mark.integration


def skip_without_db(fn):
    """Decorator: skip the test unless SIMS_INTEGRATION_DB=1."""
    return pytest.mark.skipif(not _RUN_INTEGRATION, reason=_SKIP_REASON)(fn)


@pytest.fixture(name="service")
def _service() -> IdentityService:
    """Live IdentityService pointed at the session-configured disposable DB."""
    return IdentityService()


@pytest.fixture(name="provider_scope")
def _provider_scope() -> str:
    """Unique provider scope per test run to avoid cross-test pollution."""
    return f"provider://test-provider/{uuid4().hex[:8]}"


def _declaration(entity_type: str = "site") -> EntityContractDeclaration:
    return EntityContractDeclaration(entity_type=entity_type, business_keys=["site_name", "country"])


def _site_request(label: str) -> ResolutionRequest:
    return ResolutionRequest(
        entity_type="site",
        primary_signal=IdentitySignal(identity_type=IdentityType.BUSINESS_KEY, identity_value=label),
    )


class TestContractRegistration:
    @skip_without_db
    @pytest.mark.asyncio
    async def test_first_registration_creates_scope_and_contract(self, service, provider_scope):
        result = await service.register_scope_contracts(provider_scope, [_declaration()], created_by="test")

        assert result.scope_name == provider_scope
        assert [(state.entity_type, state.state) for state in result.entities] == [("site", "created")]

        stored = await service.list_scope_contracts(provider_scope)
        assert len(stored) == 1
        assert stored[0].scope_uuid == result.scope_uuid
        assert stored[0].business_keys == ["site_name", "country"]

    @skip_without_db
    @pytest.mark.asyncio
    async def test_identical_registration_is_idempotent(self, service, provider_scope):
        first = await service.register_scope_contracts(provider_scope, [_declaration()], created_by="test")
        second = await service.register_scope_contracts(provider_scope, [_declaration()], created_by="test")

        assert first.scope_uuid == second.scope_uuid
        assert [state.state for state in second.entities] == ["existing"]
        assert len(await service.list_scope_contracts(provider_scope)) == 1

    @skip_without_db
    @pytest.mark.asyncio
    async def test_reordered_keys_are_rejected_without_partial_writes(self, service, provider_scope):
        await service.register_scope_contracts(provider_scope, [_declaration("site")], created_by="test")

        with pytest.raises(IdentityContractConflict) as excinfo:
            await service.register_scope_contracts(
                provider_scope,
                [
                    EntityContractDeclaration(entity_type="site", business_keys=["country", "site_name"]),
                    EntityContractDeclaration(entity_type="sample_group", business_keys=["sample_group_name"]),
                ],
                created_by="test",
            )

        assert excinfo.value.conflicts[0].registered == ["site_name", "country"]
        stored = await service.list_scope_contracts(provider_scope)
        assert [contract.entity_type for contract in stored] == ["site"]

    @skip_without_db
    @pytest.mark.asyncio
    async def test_internal_scope_registration_is_rejected(self, service):
        with pytest.raises(ValueError, match="provider scopes only"):
            await service.register_scope_contracts("sead://admin", [_declaration()], created_by="test")


class TestResolveContractEnforcement:
    @skip_without_db
    @pytest.mark.asyncio
    async def test_resolve_without_contract_is_rejected(self, service, provider_scope):
        with pytest.raises(IdentityContractRequired) as excinfo:
            await service.resolve_batch(provider_scope, "batch", str(uuid4()), [_site_request(f"Site {uuid4().hex}")])

        assert excinfo.value.missing_entity_types == ["site"]

    @skip_without_db
    @pytest.mark.asyncio
    async def test_resolve_after_registration_succeeds(self, service, provider_scope):
        await service.register_scope_contracts(provider_scope, [_declaration()], created_by="test")

        result = await service.resolve_batch(provider_scope, "batch", str(uuid4()), [_site_request(f"Site {uuid4().hex}")])

        assert result.submission_uuid is not None
        assert result.binding_set.binding_count == 1
        assert result.outcomes[0].outcome in {"new", "matched"}
