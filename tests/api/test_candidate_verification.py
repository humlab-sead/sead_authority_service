from unittest.mock import AsyncMock

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.candidate_verification as candidate_verification
from src.api.model import CandidateVerificationItem
from src.api.router import router
from src.strategies.site import SiteRepository
from tests.decorators import with_test_config

ID_BASE = "https://w3id.org/sead/id/"


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.parametrize(
    "candidate_id",
    [
        "https://example.org/sead/id/site/123",
        "https://w3id.org/sead/id/taxon/123",
        "https://w3id.org/sead/id/site/123/extra",
        "https://w3id.org/sead/id/site/0",
        "https://w3id.org/sead/id/site/-1",
        "https://w3id.org/sead/id/site/not-a-number",
        "https://w3id.org/sead/id/site/%2F123",
        f"https://w3id.org/sead/id/site/{'9' * 5000}",
        "https://w3id.org/sead/id/site/123?query=1",
        "https://w3id.org/sead/id/site/123#fragment",
        "site/123",
    ],
)
def test_invalid_candidate_uris_are_rejected(candidate_id: str) -> None:
    assert candidate_verification._site_id_from_candidate(candidate_id, "site", ID_BASE) is None


def test_positive_candidate_uri_returns_integer_id() -> None:
    assert candidate_verification._site_id_from_candidate(f"{ID_BASE}site/123", "site", ID_BASE) == 123
    assert candidate_verification._site_id_from_candidate(f"{ID_BASE}site/123", "site", None) is None


@pytest.mark.asyncio
@with_test_config
async def test_batch_preserves_order_and_classifies_candidates(monkeypatch, test_provider) -> None:
    looked_up: list[int] = []

    async def site_exists(self, site_id: int) -> bool:
        looked_up.append(site_id)
        return site_id == 1

    monkeypatch.setattr(SiteRepository, "site_exists", site_exists)
    results = await candidate_verification.verify_candidate_batch(
        [
            CandidateVerificationItem(type="site", id=f"{ID_BASE}site/1"),
            CandidateVerificationItem(type="site", id=f"{ID_BASE}site/2"),
            CandidateVerificationItem(type="site", id="https://invalid.example/site/3"),
            CandidateVerificationItem(type="sample_group", id=f"{ID_BASE}sample_group/4"),
            CandidateVerificationItem(type="site", id=f"{ID_BASE}site/1"),
        ]
    )

    assert [result.outcome for result in results] == [
        "exists",
        "not_found",
        "invalid_candidate",
        "unsupported_type",
        "exists",
    ]
    assert [result.aggregate_id for result in results] == [1, None, None, None, 1]
    assert looked_up == [1, 2, 1]


@pytest.mark.asyncio
@with_test_config
async def test_policy_disables_candidate_type_without_database_lookup(monkeypatch, test_provider) -> None:
    class DisabledPolicy:
        def supports(self, entity_type: str, operation: str) -> bool:
            return False

    monkeypatch.setattr(candidate_verification, "IdentityPolicy", DisabledPolicy)
    site_exists = AsyncMock()
    monkeypatch.setattr(SiteRepository, "site_exists", site_exists)

    results = await candidate_verification.verify_candidate_batch([CandidateVerificationItem(type="site", id=f"{ID_BASE}site/1")])

    assert results[0].outcome == "unsupported_type"
    site_exists.assert_not_awaited()


@pytest.mark.asyncio
@with_test_config
async def test_unregistered_site_strategy_is_unsupported_without_database_lookup(monkeypatch, test_provider) -> None:
    monkeypatch.setattr(candidate_verification.Strategies, "items", {})
    site_exists = AsyncMock()
    monkeypatch.setattr(SiteRepository, "site_exists", site_exists)

    results = await candidate_verification.verify_candidate_batch([CandidateVerificationItem(type="site", id=f"{ID_BASE}site/1")])

    assert results[0].outcome == "unsupported_type"
    site_exists.assert_not_awaited()


@with_test_config
def test_database_failure_returns_503_without_partial_results(monkeypatch, client, test_provider) -> None:
    lookups: list[int] = []

    async def site_exists(self, site_id: int) -> bool:
        lookups.append(site_id)
        if site_id == 1:
            return True
        raise psycopg.OperationalError("database unavailable")

    monkeypatch.setattr(SiteRepository, "site_exists", site_exists)
    response = client.post(
        "/reconcile/verify-candidates",
        json={"items": [{"type": "site", "id": f"{ID_BASE}site/1"}, {"type": "site", "id": f"{ID_BASE}site/2"}]},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "SEAD database is unavailable"}
    assert lookups == [1, 2]


@with_test_config
def test_candidate_endpoint_omits_identity_fields_for_nonexistent_rows(monkeypatch, client, test_provider) -> None:
    async def site_exists(self, site_id: int) -> bool:
        return False

    monkeypatch.setattr(SiteRepository, "site_exists", site_exists)
    response = client.post("/reconcile/verify-candidates", json={"items": [{"type": "site", "id": f"{ID_BASE}site/123"}]})

    assert response.status_code == 200
    assert response.json() == {"results": [{"type": "site", "id": f"{ID_BASE}site/123", "outcome": "not_found"}]}


@with_test_config
def test_candidate_endpoint_rejects_more_than_one_hundred_items_without_database_calls(monkeypatch, client, test_provider) -> None:
    site_exists = AsyncMock()
    monkeypatch.setattr(SiteRepository, "site_exists", site_exists)
    response = client.post(
        "/reconcile/verify-candidates",
        json={"items": [{"type": "site", "id": f"{ID_BASE}site/1"}] * 101},
    )

    assert response.status_code == 422
    site_exists.assert_not_awaited()
