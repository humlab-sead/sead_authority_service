from unittest.mock import AsyncMock

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import candidate_verification
from src.api.model import CandidateVerificationItem
from src.api.router import router
from src.record_selection import RecordSelectionConfigurationError
from src.strategies.site import MissingCandidateExistsQueryError, SiteReconciliationStrategy, SiteRepository
from tests.decorators import with_test_config

ID_BASE = "https://w3id.org/sead/id/"

# pylint: disable=protected-access, unused-argument

_ALL_FLAGS = (
    "search_supported",
    "identifier_search_supported",
    "browse_supported",
    "details_supported",
    "export_verification_supported",
)


def _enable_pilot(test_provider, entity_type: str, **flags: bool) -> None:
    """Enable selected capabilities for one pilot type without touching the others."""
    entry = {flag: False for flag in _ALL_FLAGS}
    entry.update(flags)
    block = {
        "version": 1,
        "browse_max_rows": 500,
        "browse_max_bytes": 1_048_576,
        "interactive_search_max_results": 50,
        "types": {entity_type: entry},
    }
    test_provider.get_config().update({"options:record_selection": block})


@pytest.fixture(name="client")
def _client() -> TestClient:
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
    assert (
        candidate_verification._site_id_from_candidate(
            candidate_id,
            "site",
            ID_BASE,
        )
        is None
    )


def test_positive_candidate_uri_returns_integer_id() -> None:
    assert candidate_verification._site_id_from_candidate(f"{ID_BASE}site/123", "site", ID_BASE) == 123
    assert candidate_verification._site_id_from_candidate(f"{ID_BASE}site/123", "site", None) is None


@pytest.mark.asyncio
@with_test_config
async def test_batch_preserves_order_and_classifies_candidates(monkeypatch, test_provider) -> None:
    looked_up: list[int] = []

    class CountingSiteStrategy(SiteReconciliationStrategy):
        instances = 0

        def __init__(self) -> None:
            type(self).instances += 1
            super().__init__()

    async def site_exists(self, site_id: int) -> bool:
        looked_up.append(site_id)
        return site_id == 1

    monkeypatch.setattr(candidate_verification.Strategies, "items", {"site": CountingSiteStrategy})
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
    assert CountingSiteStrategy.instances == 1


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
def test_missing_candidate_query_returns_configuration_error(monkeypatch, client, test_provider) -> None:
    async def site_exists(self, site_id: int) -> bool:
        raise MissingCandidateExistsQueryError("missing candidate_exists_sql")

    monkeypatch.setattr(SiteRepository, "site_exists", site_exists)
    response = client.post("/reconcile/verify-candidates", json={"items": [{"type": "site", "id": f"{ID_BASE}site/123"}]})

    assert response.status_code == 500
    assert response.json() == {"detail": "Candidate verification is misconfigured"}


@with_test_config
def test_record_selection_config_error_returns_500_without_partial_results(monkeypatch, client, test_provider) -> None:
    """A record-selection config error raised while loading the policy mid-batch returns 500, not an unhandled error."""

    def fail_policy_load():
        raise RecordSelectionConfigurationError("options:record_selection:browse_max_rows must be a positive integer")

    monkeypatch.setattr(candidate_verification, "load_record_selection_policy", fail_policy_load)
    response = client.post(
        "/reconcile/verify-candidates",
        json={"items": [{"type": "feature_type", "id": f"{ID_BASE}feature_type/1"}]},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Candidate verification is misconfigured"}


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


@pytest.mark.asyncio
@with_test_config
async def test_pilot_batch_preserves_order_echoes_and_ids(monkeypatch, test_provider) -> None:
    _enable_pilot(test_provider, "feature_type", export_verification_supported=True)
    looked_up: list[tuple[str, int]] = []

    async def fetch_record_row(entity_type: str, target_id: int):
        looked_up.append((entity_type, target_id))
        return {"target_id": target_id, "name": "row"} if target_id in {1, 2} else None

    monkeypatch.setattr(candidate_verification, "fetch_record_row", fetch_record_row)

    items = [
        CandidateVerificationItem(type="feature_type", id=f"{ID_BASE}feature_type/1"),
        CandidateVerificationItem(type="feature_type", id=f"{ID_BASE}feature_type/002"),
        CandidateVerificationItem(type="feature_type", id=f"{ID_BASE}feature_type/3"),
        CandidateVerificationItem(type="feature_type", id="https://invalid.example/site/1"),
        CandidateVerificationItem(type="feature_type", id=f"{ID_BASE}country/1"),
        CandidateVerificationItem(type="feature_type", id=f"{ID_BASE}feature_type/1"),
    ]
    results = await candidate_verification.verify_candidate_batch(items)

    assert [result.outcome for result in results] == [
        "exists",
        "exists",
        "not_found",
        "invalid_candidate",
        "invalid_candidate",
        "exists",
    ]
    assert [result.aggregate_id for result in results] == [1, 2, None, None, None, 1]
    assert [result.type for result in results] == ["feature_type"] * len(items)
    assert [result.id for result in results] == [item.id for item in items]
    assert looked_up == [("feature_type", 1), ("feature_type", 2), ("feature_type", 3), ("feature_type", 1)]


@pytest.mark.asyncio
@with_test_config
async def test_pilot_verification_does_not_use_sims_policy(monkeypatch, test_provider) -> None:
    _enable_pilot(test_provider, "country", export_verification_supported=True)

    class FailingPolicy:
        def __init__(self) -> None:
            pass

        def supports(self, entity_type: str, operation: str) -> bool:
            raise AssertionError("SIMS policy must not be consulted for pilot verification")

    async def fetch_record_row(entity_type: str, target_id: int):
        return {"target_id": target_id, "name": "Sweden"}

    monkeypatch.setattr(candidate_verification, "IdentityPolicy", FailingPolicy)
    monkeypatch.setattr(candidate_verification, "fetch_record_row", fetch_record_row)

    results = await candidate_verification.verify_candidate_batch([CandidateVerificationItem(type="country", id=f"{ID_BASE}country/1")])

    assert results[0].outcome == "exists"
    assert results[0].entity_type == "country"
    assert results[0].aggregate_id == 1


@pytest.mark.asyncio
@with_test_config
async def test_disabled_pilot_verification_does_not_hit_database(monkeypatch, test_provider) -> None:
    _enable_pilot(test_provider, "feature_type", details_supported=True, identifier_search_supported=True)
    fetch_record_row = AsyncMock()
    monkeypatch.setattr(candidate_verification, "fetch_record_row", fetch_record_row)

    results = await candidate_verification.verify_candidate_batch(
        [CandidateVerificationItem(type="feature_type", id=f"{ID_BASE}feature_type/1")]
    )

    assert results[0].outcome == "unsupported_type"
    fetch_record_row.assert_not_awaited()


@pytest.mark.asyncio
@with_test_config
async def test_pilot_verification_works_with_details_capabilities_off(monkeypatch, test_provider) -> None:
    _enable_pilot(test_provider, "feature_type", export_verification_supported=True)

    async def fetch_record_row(entity_type: str, target_id: int):
        return {"target_id": target_id, "name": "row"}

    monkeypatch.setattr(candidate_verification, "fetch_record_row", fetch_record_row)

    results = await candidate_verification.verify_candidate_batch(
        [CandidateVerificationItem(type="feature_type", id=f"{ID_BASE}feature_type/12")]
    )

    assert results[0].outcome == "exists"
    assert results[0].aggregate_id == 12


@pytest.mark.asyncio
@with_test_config
async def test_non_country_location_is_not_found(monkeypatch, test_provider) -> None:
    _enable_pilot(test_provider, "country", export_verification_supported=True)

    async def fetch_record_row(entity_type: str, target_id: int):
        return {"target_id": target_id, "name": "Sweden"} if target_id == 1 else None

    monkeypatch.setattr(candidate_verification, "fetch_record_row", fetch_record_row)

    results = await candidate_verification.verify_candidate_batch(
        [
            CandidateVerificationItem(type="country", id=f"{ID_BASE}country/1"),
            CandidateVerificationItem(type="country", id=f"{ID_BASE}country/2"),
        ]
    )

    assert [result.outcome for result in results] == ["exists", "not_found"]


@pytest.mark.asyncio
@with_test_config
async def test_mixed_site_and_pilot_batch_keeps_site_behavior(monkeypatch, test_provider) -> None:
    _enable_pilot(test_provider, "feature_type", export_verification_supported=True)

    async def fetch_record_row(entity_type: str, target_id: int):
        return {"target_id": target_id, "name": "row"}

    async def site_exists(self, site_id: int) -> bool:
        return site_id == 7

    monkeypatch.setattr(candidate_verification, "fetch_record_row", fetch_record_row)
    monkeypatch.setattr(SiteRepository, "site_exists", site_exists)

    results = await candidate_verification.verify_candidate_batch(
        [
            CandidateVerificationItem(type="feature_type", id=f"{ID_BASE}feature_type/4"),
            CandidateVerificationItem(type="site", id=f"{ID_BASE}site/7"),
            CandidateVerificationItem(type="site", id=f"{ID_BASE}site/8"),
        ]
    )

    assert [result.outcome for result in results] == ["exists", "exists", "not_found"]
    assert results[0].entity_type == "feature_type"
    assert results[0].aggregate_id == 4
    assert results[1].entity_type == "site"
    assert results[1].aggregate_id == 7


@with_test_config
def test_pilot_database_failure_after_success_returns_only_503(monkeypatch, client, test_provider) -> None:
    _enable_pilot(test_provider, "feature_type", export_verification_supported=True)
    lookups: list[int] = []

    async def fetch_record_row(entity_type: str, target_id: int):
        lookups.append(target_id)
        if target_id == 1:
            return {"target_id": 1, "name": "row"}
        raise psycopg.OperationalError("database unavailable")

    monkeypatch.setattr(candidate_verification, "fetch_record_row", fetch_record_row)

    response = client.post(
        "/reconcile/verify-candidates",
        json={
            "items": [
                {"type": "feature_type", "id": f"{ID_BASE}feature_type/1"},
                {"type": "feature_type", "id": f"{ID_BASE}feature_type/2"},
            ]
        },
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "SEAD database is unavailable"}
    assert lookups == [1, 2]
