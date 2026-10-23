"""Capability-contract tests for SIMS identity operations.

Ties the versioned capability contract together: the policy capability
snapshots and the ``GET /identity/capabilities`` response, using the real
``config/identity_policy.yml``.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from main import app
from src.api.identity_router import get_config_dep, get_identity_policy, get_identity_service
from src.identity.policy import CAPABILITY_VERSION, IdentityPolicy


def _make_client() -> TestClient:
    app.dependency_overrides[get_identity_service] = MagicMock
    app.dependency_overrides[get_config_dep] = MagicMock
    # Pass a zero-arg factory, not the class: FastAPI would otherwise analyze
    # IdentityPolicy.__init__ and treat policy_path as a required query param.
    app.dependency_overrides[get_identity_policy] = lambda: IdentityPolicy()  # pylint: disable=unnecessary-lambda
    return TestClient(app)


def test_real_policy_exposes_expected_capabilities() -> None:
    policy = IdentityPolicy()
    caps = {c.entity_type: c for c in policy.get_capabilities()}

    assert caps["site"].bind_existing is True
    assert caps["site"].allocate_new is True

    assert caps["sample"].bind_existing is False
    assert caps["sample"].allocate_new is True

    assert caps["taxa_tree_master"].bind_existing is True
    assert caps["taxa_tree_master"].allocate_new is False

    assert caps["sample_dimension"].bind_existing is False
    assert caps["sample_dimension"].allocate_new is False


def test_capability_endpoint_returns_versioned_list() -> None:
    client = _make_client()
    response = client.get("/identity/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["version"] == CAPABILITY_VERSION

    by_type = {e["entity_type"]: e for e in data["entities"]}
    assert by_type["site"] == {
        "entity_type": "site",
        "entity_subtype": "shared_metadata",
        "bind_existing": True,
        "allocate_new": True,
        "auto_confirm": True,
        "accept_uuid": False,
    }


def test_unconfigured_entity_is_absent_from_capabilities() -> None:
    policy = IdentityPolicy()
    caps = {c.entity_type for c in policy.get_capabilities()}

    assert "not_a_real_entity" not in caps
    assert policy.supports("not_a_real_entity", "bind_existing") is False
    assert policy.supports("not_a_real_entity", "allocate_new") is False
