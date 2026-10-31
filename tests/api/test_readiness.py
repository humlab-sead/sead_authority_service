import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.candidate_verification as candidate_verification
from src.api.router import router
from src.candidate_verification import UnsupportedReadinessType
from src.strategies.strategy import Strategies
from tests.decorators import with_test_config


class _ReadyStrategy:
    calls: list[dict] = []
    error: Exception | None = None

    async def find_candidates(self, *, query: str, properties: dict, limit: int) -> list[dict]:
        self.calls.append({"query": query, "properties": properties, "limit": limit})
        if self.error:
            raise self.error
        return []


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.asyncio
@with_test_config
async def test_readiness_runs_minimal_registered_site_query(monkeypatch, test_provider) -> None:
    monkeypatch.setattr(Strategies, "items", {"site": _ReadyStrategy})
    _ReadyStrategy.calls = []
    _ReadyStrategy.error = None

    result = await candidate_verification.get_reconciliation_readiness("site")

    assert result.model_dump() == {"type": "site", "ready": True, "reason": None}
    assert _ReadyStrategy.calls == [{"query": "readiness", "properties": {}, "limit": 1}]


@pytest.mark.asyncio
@with_test_config
async def test_readiness_reports_missing_id_base_without_running_query(monkeypatch, test_provider) -> None:
    monkeypatch.setattr(Strategies, "items", {"site": _ReadyStrategy})
    monkeypatch.setattr(candidate_verification, "_configured_id_base", lambda: None)
    _ReadyStrategy.calls = []

    result = await candidate_verification.get_reconciliation_readiness("site")

    assert result.ready is False
    assert "options:id_base" in result.reason
    assert _ReadyStrategy.calls == []


@pytest.mark.asyncio
@with_test_config
async def test_readiness_reports_database_match_failure(monkeypatch, test_provider) -> None:
    monkeypatch.setattr(Strategies, "items", {"site": _ReadyStrategy})
    _ReadyStrategy.calls = []
    _ReadyStrategy.error = psycopg.OperationalError("connection details must not be returned")

    result = await candidate_verification.get_reconciliation_readiness("site")

    assert result.ready is False
    assert result.reason is not None
    assert "connection details" not in result.reason
    assert _ReadyStrategy.calls == [{"query": "readiness", "properties": {}, "limit": 1}]
    _ReadyStrategy.error = None


@pytest.mark.asyncio
@with_test_config
async def test_readiness_rejects_unknown_type(monkeypatch, test_provider) -> None:
    monkeypatch.setattr(Strategies, "items", {"site": _ReadyStrategy})

    with pytest.raises(UnsupportedReadinessType, match="Unsupported reconciliation type"):
        await candidate_verification.get_reconciliation_readiness("unknown")


@with_test_config
def test_readiness_endpoint_maps_unknown_type_to_422(client, test_provider) -> None:
    response = client.get("/reconcile/readiness", params={"type": "unknown"})

    assert response.status_code == 422
    assert "Unsupported reconciliation type" in response.json()["detail"]


@with_test_config
def test_readiness_endpoint_returns_ready_response(monkeypatch, client, test_provider) -> None:
    monkeypatch.setattr(Strategies, "items", {"site": _ReadyStrategy})
    _ReadyStrategy.calls = []
    _ReadyStrategy.error = None

    response = client.get("/reconcile/readiness", params={"type": "site"})

    assert response.status_code == 200
    assert response.json() == {"type": "site", "ready": True, "reason": None}
    assert _ReadyStrategy.calls == [{"query": "readiness", "properties": {}, "limit": 1}]


@with_test_config
def test_readiness_endpoint_returns_safe_database_failure_reason(monkeypatch, client, test_provider) -> None:
    monkeypatch.setattr(Strategies, "items", {"site": _ReadyStrategy})
    _ReadyStrategy.calls = []
    monkeypatch.setattr(_ReadyStrategy, "error", psycopg.OperationalError("private connection details"))

    response = client.get("/reconcile/readiness", params={"type": "site"})

    assert response.status_code == 200
    assert response.json()["ready"] is False
    assert "private connection details" not in response.json()["reason"]
