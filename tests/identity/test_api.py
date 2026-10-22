"""Unit tests for the SIMS Identity API router.

Uses FastAPI's dependency override mechanism to inject a fully-mocked
IdentityService so no database or config store is required.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from main import app
from src.api.identity_router import get_config_dep, get_identity_policy, get_identity_service
from src.identity.models import (
    BindingSet,
    BindingSetResponse,
    ChangeDetectionResult,
    ResolutionOutcome,
    ResolveBatchResult,
    SourceScope,
)
from src.identity.service import IdentityBatchConflict, IdentityBindingConflict
from src.identity.types import BindingSetState, ChangeOutcome

NOW = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Fixed UUIDs for predictable assertions
# ---------------------------------------------------------------------------

SCOPE_UUID = uuid4()
SUBMISSION_UUID = uuid4()
TRACKED_UUID = uuid4()
BINDING_SET_UUID = uuid4()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_source_scope() -> SourceScope:
    return SourceScope(
        scope_uuid=SCOPE_UUID,
        scope_name="sead://reconciliation",
        created_at=NOW,
    )


def _make_binding_set_response(state: str = "confirmed") -> BindingSetResponse:
    return BindingSetResponse(
        binding_set_uuid=BINDING_SET_UUID,
        submission_uuid=SUBMISSION_UUID,
        lifecycle_state=BindingSetState(state),
        change_request_name=None,
        binding_count=1,
        created_at=NOW,
    )


def _make_binding_set(state: str = "confirmed") -> BindingSet:
    return BindingSet(
        binding_set_uuid=BINDING_SET_UUID,
        submission_uuid=SUBMISSION_UUID,
        lifecycle_state=BindingSetState(state),
        created_at=NOW,
    )


def _make_submission() -> MagicMock:
    sub = MagicMock()
    sub.submission_uuid = SUBMISSION_UUID
    return sub


def _make_outcome(outcome: str = "new", *, aggregate_id: int | None = None) -> ResolutionOutcome:
    return ResolutionOutcome(
        source_identity_uuid=uuid4(),
        entity_type="site",
        outcome=outcome,
        tracked_identity_uuid=TRACKED_UUID if outcome == "matched" else None,
        aggregate_id=aggregate_id,
    )


def _make_batch_result(*, aggregate_id: int | None = None, outcome: str = "new") -> ResolveBatchResult:
    return ResolveBatchResult(
        submission_uuid=SUBMISSION_UUID,
        scope_uuid=SCOPE_UUID,
        binding_set=_make_binding_set_response(),
        outcomes=[_make_outcome(outcome, aggregate_id=aggregate_id)],
    )


def _make_service_mock(**overrides) -> MagicMock:
    """Return a MagicMock IdentityService with sensible async return values."""
    svc = MagicMock()
    svc.resolve_batch = AsyncMock(return_value=_make_batch_result())
    svc.get_binding_set = AsyncMock(return_value=_make_binding_set_response())
    svc.confirm_binding_set = AsyncMock(return_value=_make_binding_set("confirmed"))
    svc.associate_change_request = AsyncMock(return_value=_make_binding_set("confirmed"))
    svc.detect_change = AsyncMock(
        return_value=ChangeDetectionResult(
            tracked_identity_uuid=TRACKED_UUID,
            outcome=ChangeOutcome.INSERT,
            previous_hash=None,
        )
    )
    svc.list_scopes = AsyncMock(return_value=[_make_source_scope()])
    for attr, val in overrides.items():
        setattr(svc, attr, val)
    return svc


def _make_policy_mock(*, configured: tuple[str, ...] = ("site",), supports: bool = True) -> MagicMock:
    """Return a permissive IdentityPolicy mock for capability checks."""
    policy = MagicMock()
    policy.known_entity_types.return_value = list(configured)
    policy.supports.return_value = supports
    policy.get_capabilities.return_value = []
    return policy


def _make_client(svc: MagicMock) -> TestClient:
    """Build a TestClient with the given service mock injected."""
    app.dependency_overrides[get_identity_service] = lambda: svc
    app.dependency_overrides[get_config_dep] = MagicMock
    app.dependency_overrides[get_identity_policy] = _make_policy_mock
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /identity/resolve
# ---------------------------------------------------------------------------


class TestResolveEndpoint:
    VALID_BODY = {
        "scope_name": "sead://reconciliation",
        "run_id": "run-001",
        "submission_name": "test-batch-001",
        "requests": [
            {
                "entity_type": "site",
                "primary_signal": {
                    "identity_type": "business_key",
                    "identity_value": "ABC-001",
                },
            }
        ],
    }

    def test_resolve_returns_200(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.post("/identity/resolve", json=self.VALID_BODY)
        assert response.status_code == 200

    def test_resolve_response_shape(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.post("/identity/resolve", json=self.VALID_BODY)
        data = response.json()
        assert "submission_uuid" in data
        assert "scope_uuid" in data
        assert "binding_set" in data
        assert "outcomes" in data

    def test_resolve_response_includes_target_id_when_present(self):
        svc = _make_service_mock(resolve_batch=AsyncMock(return_value=_make_batch_result(aggregate_id=4321, outcome="matched")))
        client = _make_client(svc)

        response = client.post("/identity/resolve", json=self.VALID_BODY)

        data = response.json()
        assert data["outcomes"][0]["target_id"] == 4321
        assert "aggregate_id" not in data["outcomes"][0]

    def test_resolve_passes_run_id_and_approved_aggregate_id(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        body = {
            **self.VALID_BODY,
            "requests": [{**self.VALID_BODY["requests"][0], "approved_aggregate_id": 4321}],
        }

        response = client.post("/identity/resolve", json=body)

        assert response.status_code == 200
        kwargs = svc.resolve_batch.await_args.kwargs
        assert kwargs["run_id"] == "run-001"
        assert kwargs["scope_name"] == "sead://reconciliation"
        assert kwargs["requests"][0].approved_aggregate_id == 4321

    def test_resolve_returns_409_for_approved_aggregate_conflict(self):
        svc = _make_service_mock(resolve_batch=AsyncMock(side_effect=IdentityBindingConflict("approved aggregate ID conflicts")))
        client = _make_client(svc)
        body = {
            **self.VALID_BODY,
            "requests": [{**self.VALID_BODY["requests"][0], "approved_aggregate_id": 9876}],
        }

        response = client.post("/identity/resolve", json=body)

        assert response.status_code == 409
        assert response.json()["detail"] == "approved aggregate ID conflicts"

    def test_resolve_returns_409_for_binding_phase_conflict(self):
        svc = _make_service_mock(resolve_batch=AsyncMock(side_effect=IdentityBindingConflict("unresolved proposed binding")))
        client = _make_client(svc)

        response = client.post("/identity/resolve", json=self.VALID_BODY)

        assert response.status_code == 409
        assert response.json()["detail"] == "unresolved proposed binding"

    def test_resolve_returns_409_for_reused_run_with_changed_payload(self):
        svc = _make_service_mock(resolve_batch=AsyncMock(side_effect=IdentityBatchConflict("different payload")))
        client = _make_client(svc)

        response = client.post("/identity/resolve", json=self.VALID_BODY)

        assert response.status_code == 409
        assert "different payload" in response.json()["detail"]

    def test_resolve_rejects_nonpositive_approved_aggregate_id(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        body = {
            **self.VALID_BODY,
            "requests": [{**self.VALID_BODY["requests"][0], "approved_aggregate_id": 0}],
        }

        response = client.post("/identity/resolve", json=body)

        assert response.status_code == 422
        svc.resolve_batch.assert_not_called()

    def test_resolve_rejects_legacy_approved_target_id(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        body = {
            **self.VALID_BODY,
            "requests": [{**self.VALID_BODY["requests"][0], "approved_target_id": 77}],
        }

        response = client.post("/identity/resolve", json=body)

        assert response.status_code == 422
        svc.resolve_batch.assert_not_called()

    def test_resolve_missing_run_id_returns_422(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        body = dict(self.VALID_BODY)
        del body["run_id"]
        response = client.post("/identity/resolve", json=body)
        assert response.status_code == 422
        svc.resolve_batch.assert_not_called()

    def test_resolve_empty_requests_returns_422(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        body = dict(self.VALID_BODY)
        body["requests"] = []
        response = client.post("/identity/resolve", json=body)
        assert response.status_code == 422

    def test_resolve_passes_created_by(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        body = dict(self.VALID_BODY)
        body["created_by"] = "test-agent"
        client.post("/identity/resolve", json=body)
        assert svc.resolve_batch.await_args.kwargs["created_by"] == "test-agent"


# ---------------------------------------------------------------------------
# Resolve operation checks (capability enforcement)
# ---------------------------------------------------------------------------


class TestResolveOperationChecks:
    def _body(self, **request_overrides) -> dict:
        request = {
            "entity_type": "site",
            "primary_signal": {"identity_type": "business_key", "identity_value": "ABC-001"},
        }
        request.update(request_overrides)
        return {"scope_name": "sead://reconciliation", "run_id": "run-001", "submission_name": "test-batch-001", "requests": [request]}

    def test_unconfigured_entity_rejected_before_write(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        app.dependency_overrides[get_identity_policy] = lambda: _make_policy_mock(configured=())
        response = client.post("/identity/resolve", json=self._body(entity_type="not_configured"))
        assert response.status_code == 422
        assert "not configured" in response.json()["detail"]
        svc.resolve_batch.assert_not_called()

    def test_unsupported_operation_rejected_before_write(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        app.dependency_overrides[get_identity_policy] = lambda: _make_policy_mock(configured=("site",), supports=False)
        response = client.post("/identity/resolve", json=self._body())
        assert response.status_code == 422
        assert "allocate_new" in response.json()["detail"]
        svc.resolve_batch.assert_not_called()

    def test_unsupported_bind_existing_rejected(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        app.dependency_overrides[get_identity_policy] = lambda: _make_policy_mock(configured=("sample",), supports=False)
        response = client.post("/identity/resolve", json=self._body(entity_type="sample", approved_aggregate_id=123))
        assert response.status_code == 422
        assert "bind_existing" in response.json()["detail"]
        svc.resolve_batch.assert_not_called()


# ---------------------------------------------------------------------------
# GET /identity/binding-sets/{binding_set_uuid}
# ---------------------------------------------------------------------------


class TestGetBindingSet:
    def test_returns_200_when_found(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.get(f"/identity/binding-sets/{BINDING_SET_UUID}")
        assert response.status_code == 200

    def test_returns_binding_set_uuid_in_body(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.get(f"/identity/binding-sets/{BINDING_SET_UUID}")
        data = response.json()
        assert data["binding_set_uuid"] == str(BINDING_SET_UUID)

    def test_returns_404_when_not_found(self):
        svc = _make_service_mock(get_binding_set=AsyncMock(return_value=None))
        client = _make_client(svc)
        response = client.get(f"/identity/binding-sets/{BINDING_SET_UUID}")
        assert response.status_code == 404

    def test_calls_service_with_correct_uuid(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        client.get(f"/identity/binding-sets/{BINDING_SET_UUID}")
        svc.get_binding_set.assert_called_once_with(UUID(str(BINDING_SET_UUID)))


# ---------------------------------------------------------------------------
# POST /identity/binding-sets/{binding_set_uuid}/confirm
# ---------------------------------------------------------------------------


class TestConfirmBindingSet:
    def test_returns_200_when_found(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.post(f"/identity/binding-sets/{BINDING_SET_UUID}/confirm")
        assert response.status_code == 200

    def test_calls_confirm_then_get(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        client.post(f"/identity/binding-sets/{BINDING_SET_UUID}/confirm")
        svc.confirm_binding_set.assert_called_once_with(UUID(str(BINDING_SET_UUID)))
        svc.get_binding_set.assert_called_once_with(UUID(str(BINDING_SET_UUID)))

    def test_returns_404_when_not_found(self):
        svc = _make_service_mock(confirm_binding_set=AsyncMock(return_value=None))
        client = _make_client(svc)
        response = client.post(f"/identity/binding-sets/{BINDING_SET_UUID}/confirm")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /identity/binding-sets/{binding_set_uuid}/change-request
# ---------------------------------------------------------------------------


class TestAssociateChangeRequest:
    BODY = {"change_request_name": "cr/2026-01-site-data"}

    def test_returns_200_when_found(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.post(
            f"/identity/binding-sets/{BINDING_SET_UUID}/change-request",
            json=self.BODY,
        )
        assert response.status_code == 200

    def test_calls_associate_then_get(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        client.post(
            f"/identity/binding-sets/{BINDING_SET_UUID}/change-request",
            json=self.BODY,
        )
        svc.associate_change_request.assert_called_once_with(UUID(str(BINDING_SET_UUID)), "cr/2026-01-site-data")
        svc.get_binding_set.assert_called_once()

    def test_returns_404_when_not_found(self):
        svc = _make_service_mock(associate_change_request=AsyncMock(return_value=None))
        client = _make_client(svc)
        response = client.post(
            f"/identity/binding-sets/{BINDING_SET_UUID}/change-request",
            json=self.BODY,
        )
        assert response.status_code == 404

    def test_missing_body_returns_422(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.post(
            f"/identity/binding-sets/{BINDING_SET_UUID}/change-request",
            json={},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /identity/detect-change
# ---------------------------------------------------------------------------


class TestDetectChange:
    BODY = {
        "tracked_identity_uuid": str(TRACKED_UUID),
        "content_hash": "abc123",
    }

    def test_returns_200_on_insert(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.post("/identity/detect-change", json=self.BODY)
        assert response.status_code == 200

    def test_outcome_field_present(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.post("/identity/detect-change", json=self.BODY)
        data = response.json()
        assert data["outcome"] == "insert"
        assert data["previous_hash"] is None

    def test_calls_service_detect_change(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        client.post("/identity/detect-change", json=self.BODY)
        svc.detect_change.assert_called_once()

    def test_raises_404_on_lookup_error(self):
        svc = _make_service_mock(detect_change=AsyncMock(side_effect=LookupError("not found")))
        client = _make_client(svc)
        response = client.post("/identity/detect-change", json=self.BODY)
        assert response.status_code == 404

    def test_returns_skip_when_hash_unchanged(self):
        svc = _make_service_mock(
            detect_change=AsyncMock(
                return_value=ChangeDetectionResult(
                    tracked_identity_uuid=TRACKED_UUID,
                    outcome=ChangeOutcome.SKIP,
                    previous_hash="abc123",
                )
            )
        )
        client = _make_client(svc)
        response = client.post("/identity/detect-change", json=self.BODY)
        assert response.json()["outcome"] == "skip"


# ---------------------------------------------------------------------------
# GET /identity/scopes
# ---------------------------------------------------------------------------


class TestListScopes:
    def test_returns_200(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.get("/identity/scopes")
        assert response.status_code == 200

    def test_returns_list(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.get("/identity/scopes")
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1

    def test_scope_name_in_response(self):
        svc = _make_service_mock()
        client = _make_client(svc)
        response = client.get("/identity/scopes")
        data = response.json()
        assert data[0]["scope_name"] == "sead://reconciliation"

    def test_empty_list_when_no_scopes(self):
        svc = _make_service_mock(list_scopes=AsyncMock(return_value=[]))
        client = _make_client(svc)
        response = client.get("/identity/scopes")
        assert response.json() == []
