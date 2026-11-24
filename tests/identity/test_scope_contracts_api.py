"""Unit tests for the provider-scope contract API endpoints.

The service and the registration policy are dependency-overridden, so no
database, config store, or real credentials are needed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from main import app
from src.api.identity_router import (
    get_config_dep,
    get_contract_registration_policy,
    get_identity_policy,
    get_identity_service,
)
from src.identity.contracts import (
    ContractAuthorizationError,
    ContractRegistrationPolicy,
    IdentityContractConflict,
    IdentityContractRequired,
)
from src.identity.models import EntityContractConflict, EntityContractState, EntityKeyContract, ScopeContractRegistration

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
SCOPE_UUID = uuid4()
SCOPE_NAME = "provider://gbif/occurrence"


def _make_registration(state: str = "created") -> ScopeContractRegistration:
    return ScopeContractRegistration(
        scope_name=SCOPE_NAME,
        scope_uuid=SCOPE_UUID,
        entities=[
            EntityContractState(entity_type="site", business_keys=["site_name", "country"], state=state),  # type: ignore[arg-type]
        ],
    )


def _make_contract() -> EntityKeyContract:
    return EntityKeyContract(
        contract_uuid=uuid4(),
        scope_uuid=SCOPE_UUID,
        entity_type="site",
        business_keys=["site_name", "country"],
        created_at=NOW,
    )


def _make_service_mock(**overrides) -> MagicMock:
    service = MagicMock()
    service.register_scope_contracts = AsyncMock(return_value=_make_registration())
    service.list_scope_contracts = AsyncMock(return_value=[_make_contract()])
    service.resolve_batch = AsyncMock()
    for name, value in overrides.items():
        setattr(service, name, value)
    return service


def _make_policy_mock(caller: str = "shape-shifter") -> MagicMock:
    policy = MagicMock(spec=ContractRegistrationPolicy)
    policy.authorize = MagicMock(return_value=caller)
    return policy


def _make_client(service: MagicMock, policy: MagicMock | None = None) -> TestClient:
    identity_policy = MagicMock()
    identity_policy.known_entity_types.return_value = ["site"]
    identity_policy.supports.return_value = True

    app.dependency_overrides[get_identity_service] = lambda: service
    app.dependency_overrides[get_config_dep] = lambda: MagicMock()  # pylint: disable=unnecessary-lambda
    app.dependency_overrides[get_identity_policy] = lambda: identity_policy  # pylint: disable=unnecessary-lambda
    app.dependency_overrides[get_contract_registration_policy] = lambda: policy or _make_policy_mock()  # pylint: disable=unnecessary-lambda
    return TestClient(app)


VALID_BODY = {
    "scope_name": SCOPE_NAME,
    "entities": [{"entity_type": "site", "business_keys": ["site_name", "country"]}],
}

HEADERS = {"X-SIMS-Caller": "shape-shifter", "X-SIMS-Caller-Token": "s3cret"}


class TestRegisterScopeContractsEndpoint:
    def test_returns_200_with_entity_states(self) -> None:
        service = _make_service_mock()
        client = _make_client(service)

        response = client.post("/identity/scope-contracts", json=VALID_BODY, headers=HEADERS)

        assert response.status_code == 200
        data = response.json()
        assert data["scope_name"] == SCOPE_NAME
        assert data["entities"][0]["state"] == "created"
        assert data["entities"][0]["business_keys"] == ["site_name", "country"]

    def test_authorizes_caller_for_requested_scope(self) -> None:
        service = _make_service_mock()
        policy = _make_policy_mock()
        client = _make_client(service, policy)

        client.post("/identity/scope-contracts", json=VALID_BODY, headers=HEADERS)

        policy.authorize.assert_called_once_with("shape-shifter", "s3cret", SCOPE_NAME)

    def test_uses_caller_name_as_default_creator(self) -> None:
        service = _make_service_mock()
        client = _make_client(service)

        client.post("/identity/scope-contracts", json=VALID_BODY, headers=HEADERS)

        assert service.register_scope_contracts.await_args.kwargs["created_by"] == "shape-shifter"

    def test_keeps_explicit_creator(self) -> None:
        service = _make_service_mock()
        client = _make_client(service)

        client.post("/identity/scope-contracts", json={**VALID_BODY, "created_by": "roger"}, headers=HEADERS)

        assert service.register_scope_contracts.await_args.kwargs["created_by"] == "roger"

    def test_returns_403_for_unauthorized_caller(self) -> None:
        policy = MagicMock(spec=ContractRegistrationPolicy)
        policy.authorize = MagicMock(side_effect=ContractAuthorizationError("Caller 'other' is not authorized for scope"))
        client = _make_client(_make_service_mock(), policy)

        response = client.post("/identity/scope-contracts", json=VALID_BODY, headers=HEADERS)

        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"]

    def test_returns_409_with_registered_and_submitted_keys(self) -> None:
        conflict = EntityContractConflict(entity_type="site", registered=["site_name"], submitted=["country"])
        service = _make_service_mock(register_scope_contracts=AsyncMock(side_effect=IdentityContractConflict(SCOPE_NAME, [conflict])))
        client = _make_client(service)

        response = client.post("/identity/scope-contracts", json=VALID_BODY, headers=HEADERS)

        assert response.status_code == 409
        detail = response.json()["detail"]
        assert detail["conflicts"] == [{"entity_type": "site", "registered": ["site_name"], "submitted": ["country"]}]

    def test_returns_422_for_non_provider_scope(self) -> None:
        service = _make_service_mock(
            register_scope_contracts=AsyncMock(side_effect=ValueError("Business-key contracts apply to provider scopes only"))
        )
        client = _make_client(service)

        response = client.post("/identity/scope-contracts", json={**VALID_BODY, "scope_name": "sead://admin"}, headers=HEADERS)

        assert response.status_code == 422

    def test_rejects_duplicate_key_names_in_request(self) -> None:
        client = _make_client(_make_service_mock())

        response = client.post(
            "/identity/scope-contracts",
            json={"scope_name": SCOPE_NAME, "entities": [{"entity_type": "site", "business_keys": ["site_name", "site_name"]}]},
            headers=HEADERS,
        )

        assert response.status_code == 422


class TestListScopeContractsEndpoint:
    def test_returns_registered_contracts(self) -> None:
        service = _make_service_mock()
        client = _make_client(service)

        response = client.get("/identity/scope-contracts", params={"scope_name": SCOPE_NAME})

        assert response.status_code == 200
        data = response.json()
        assert data[0]["entity_type"] == "site"
        assert data[0]["business_keys"] == ["site_name", "country"]
        service.list_scope_contracts.assert_awaited_once_with(SCOPE_NAME)

    def test_requires_scope_name(self) -> None:
        client = _make_client(_make_service_mock())

        response = client.get("/identity/scope-contracts")

        assert response.status_code == 422


class TestResolveContractEnforcement:
    def test_returns_409_when_provider_scope_has_no_contract(self) -> None:
        service = _make_service_mock(
            resolve_batch=AsyncMock(side_effect=IdentityContractRequired(SCOPE_NAME, ["site"])),
        )
        client = _make_client(service)

        response = client.post(
            "/identity/resolve",
            json={
                "scope_name": SCOPE_NAME,
                "run_id": "run-1",
                "submission_name": "batch",
                "requests": [
                    {
                        "entity_type": "site",
                        "primary_signal": {"identity_type": "business_key", "identity_value": "label"},
                    }
                ],
            },
        )

        assert response.status_code == 409
        assert "no registered business-key contract" in response.json()["detail"]
