"""HTTP tests for record selection discovery, lists, details, and interactive search."""

import json
from typing import Any

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import src.api.router as router_module
import src.record_selection as record_selection_module
from src.api.router import router
from src.configuration import MockConfigProvider
from src.record_identifiers import POSTGRES_INTEGER_MAX, parse_record_uri
from src.strategies.configured_classifier import ConfiguredClassifierStrategy, initialize_classifiers, simple_classifier_keys
from tests.decorators import with_test_config

ID_BASE = "https://w3id.org/sead/id/"
ALL_FLAGS = (
    "search_supported",
    "identifier_search_supported",
    "browse_supported",
    "details_supported",
    "export_verification_supported",
)

# pylint: disable=protected-access, unused-argument, redefined-outer-name


@pytest.fixture(name="client")
def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _set_selection(
    test_provider: MockConfigProvider,
    types: dict[str, dict[str, bool]],
    *,
    browse_max_rows: int = 500,
    browse_max_bytes: int = 1_048_576,
    interactive_search_max_results: int = 50,
) -> None:
    """Replace the record-selection block for one test."""
    initialize_classifiers()
    block: dict[str, Any] = {
        "version": 1,
        "browse_max_rows": browse_max_rows,
        "browse_max_bytes": browse_max_bytes,
        "interactive_search_max_results": interactive_search_max_results,
        "types": {},
    }
    for entity_type, flags in types.items():
        entry = {flag: False for flag in ALL_FLAGS}
        entry.update(flags)
        block["types"][entity_type] = entry
    test_provider.get_config().update({"options:record_selection": block})


def _mock_db(test_provider, *, fetchall: list[dict[str, Any]] | None = None, fetchone: dict[str, Any] | None = None):
    test_provider.create_connection_mock(execute=None, fetchall=fetchall or [], fetchone=fetchone)
    return test_provider.cursor_mock


class TestDiscovery:
    """Discovery reports independent capabilities without querying target data."""

    @with_test_config
    def test_stock_config_lists_every_selectable_type_with_all_capabilities_off(
        self, client: TestClient, test_provider: MockConfigProvider
    ):
        response = client.get("/records/types")

        assert response.status_code == 200
        types = {entry["type"]: entry for entry in response.json()["types"]}
        assert set(types) == set(simple_classifier_keys())
        assert {"feature_type", "country"} <= set(types)
        for entry in types.values():
            assert entry["search_supported"] is False
            assert entry["identifier_search_supported"] is False
            assert entry["browse_supported"] is False
            assert entry["details_supported"] is False
            assert entry["export_verification_supported"] is False
            assert entry["browse_max_rows"] is None
            assert entry["browse_max_bytes"] is None
            assert entry["interactive_search_max_results"] is None

    @with_test_config
    def test_lookups_are_not_selectable_record_types(self, client: TestClient, test_provider: MockConfigProvider):
        """Registered lookups are reconcilable but are not offered as selectable records."""
        types = {entry["type"] for entry in client.get("/records/types").json()["types"]}

        assert {"feature", "project", "taxa_common_names", "rdb_system"}.isdisjoint(types)

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "oak", "type": "taxa_common_names", "limit": 1}}},
        )
        assert response.status_code == 422

    @with_test_config
    def test_feature_type_display_fields_and_filters(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {}})

        entry = next(item for item in client.get("/records/types").json()["types"] if item["type"] == "feature_type")
        assert [field["name"] for field in entry["display_fields"]] == ["name", "target_id", "description"]
        assert all(field["source"] == "record" for field in entry["display_fields"])
        assert entry["text_filter_fields"] == ["name", "description"]
        assert entry["sort_fields"] == ["name", "target_id"]
        assert entry["field_filters"] == [
            {"field": "name", "operator": "contains_ci"},
            {"field": "description", "operator": "contains_ci"},
            {"field": "target_id", "operator": "equals"},
        ]
        assert entry["id_path"] == "feature_type"
        assert entry["id_base"] == ID_BASE

    @with_test_config
    def test_country_has_no_description_field(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"country": {}})

        entry = next(item for item in client.get("/records/types").json()["types"] if item["type"] == "country")

        assert [field["name"] for field in entry["display_fields"]] == ["name", "target_id"]
        assert entry["text_filter_fields"] == ["name"]
        assert entry["field_filters"] == [
            {"field": "name", "operator": "contains_ci"},
            {"field": "target_id", "operator": "equals"},
        ]

    @with_test_config
    def test_one_flag_enables_only_that_capability(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}})

        entry = next(item for item in client.get("/records/types").json()["types"] if item["type"] == "feature_type")

        assert entry["browse_supported"] is True
        assert entry["browse_max_rows"] == 500
        assert entry["browse_max_bytes"] == 1_048_576
        assert entry["search_supported"] is False
        assert entry["interactive_search_max_results"] is None

    @with_test_config
    def test_independent_limits_can_be_overridden(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(
            test_provider,
            {"country": {"browse_supported": True, "search_supported": True}},
            browse_max_rows=7,
            browse_max_bytes=2048,
            interactive_search_max_results=11,
        )

        entry = next(item for item in client.get("/records/types").json()["types"] if item["type"] == "country")

        assert entry["browse_max_rows"] == 7
        assert entry["browse_max_bytes"] == 2048
        assert entry["interactive_search_max_results"] == 11

    @with_test_config
    def test_discovery_lists_only_configured_types(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {}})

        types = {entry["type"] for entry in client.get("/records/types").json()["types"]}

        assert types == {"feature_type"}
        assert "country" not in types

    @with_test_config
    def test_manifest_publishes_record_selection_descriptor(self, client: TestClient, test_provider: MockConfigProvider):
        data = client.get("/reconcile").json()

        assert data["reconciliation"]["record_selection"] == {"version": 1, "types_path": "/records/types"}
        assert "supportedTypes" in data["reconciliation"]


class TestListRecords:
    """Complete lists return exactly the measured bytes or an explicit too-large error."""

    @with_test_config
    def test_complete_list_returns_projected_records(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}})
        _mock_db(
            test_provider,
            fetchall=[
                {"target_id": 1, "name": "Pit", "description": "A pit"},
                {"target_id": 2, "name": "Hearth", "description": None},
            ],
        )

        response = client.get("/records/feature_type")

        assert response.status_code == 200
        body = response.json()
        assert body["completeness"] == "complete"
        assert [item["target_id"] for item in body["items"]] == [1, 2]
        assert body["items"][0]["id"] == f"{ID_BASE}feature_type/1"
        assert body["items"][0]["type"] == "feature_type"
        assert body["items"][0]["description"] == "A pit"
        assert "description" not in body["items"][1]
        assert body["items"][0]["fields"] == {}
        assert "score" not in body["items"][0]

    @with_test_config
    def test_empty_list_is_a_successful_complete_list(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}})
        _mock_db(test_provider, fetchall=[])

        response = client.get("/records/feature_type")

        assert response.status_code == 200
        assert response.json() == {"items": [], "completeness": "complete"}

    @with_test_config
    def test_list_at_row_limit_is_complete(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}}, browse_max_rows=2)
        _mock_db(
            test_provider,
            fetchall=[
                {"target_id": 1, "name": "A", "description": None},
                {"target_id": 2, "name": "B", "description": None},
            ],
        )

        response = client.get("/records/feature_type")

        assert response.status_code == 200
        assert len(response.json()["items"]) == 2

    @with_test_config
    def test_list_one_row_over_limit_is_too_large(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}}, browse_max_rows=2)
        _mock_db(
            test_provider,
            fetchall=[
                {"target_id": 1, "name": "A", "description": None},
                {"target_id": 2, "name": "B", "description": None},
                {"target_id": 3, "name": "C", "description": None},
            ],
        )

        response = client.get("/records/feature_type")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "too_large_to_browse"
        assert "items" not in response.json()

    @with_test_config
    def test_list_byte_boundary_includes_the_envelope(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}}, browse_max_bytes=10_000_000)
        _mock_db(test_provider, fetchall=[{"target_id": 1, "name": "Ångström", "description": "Smält"}])

        measured = client.get("/records/feature_type")
        assert measured.status_code == 200
        body = measured.content
        assert len(body) > len(body.decode("utf-8"))  # multibyte content

        _set_selection(test_provider, {"feature_type": {"browse_supported": True}}, browse_max_bytes=len(body))
        at_limit = client.get("/records/feature_type")
        assert at_limit.status_code == 200
        assert at_limit.content == body

        _set_selection(test_provider, {"feature_type": {"browse_supported": True}}, browse_max_bytes=len(body) - 1)
        over_limit = client.get("/records/feature_type")
        assert over_limit.status_code == 409
        assert over_limit.json()["error"]["code"] == "too_large_to_browse"

    @with_test_config
    def test_list_rejects_query_parameters(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}})
        _mock_db(test_provider)

        response = client.get("/records/feature_type?limit=5")

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"

    @with_test_config
    def test_country_list_filters_to_country_locations(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"country": {"browse_supported": True}})
        cursor = _mock_db(test_provider, fetchall=[{"target_id": 1, "name": "Sweden", "description": None}])

        response = client.get("/records/country")

        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == f"{ID_BASE}country/1"
        sql = cursor.execute.call_args.args[0]
        assert "authority.country" in sql
        assert "location_type_id" not in sql

    @with_test_config
    def test_unsupported_and_disabled_types_are_distinguishable(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {}})

        unregistered = client.get("/records/site")
        disabled = client.get("/records/feature_type")

        assert unregistered.status_code == 422
        assert unregistered.json()["error"]["code"] == "unsupported_type"
        assert disabled.status_code == 422
        assert disabled.json()["error"]["code"] == "unsupported_capability"

    @with_test_config
    def test_marked_but_unconfigured_type_is_unsupported(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True, "details_supported": True}})

        listing = client.get("/records/country")
        details = client.get("/records/country/details", params={"target_id": 1})
        search = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "sweden", "type": "country", "limit": 5}}},
        )

        assert listing.status_code == 422
        assert listing.json()["error"]["code"] == "unsupported_type"
        assert details.status_code == 422
        assert details.json()["error"]["code"] == "unsupported_type"
        assert search.status_code == 422
        assert search.json()["error"]["code"] == "unsupported_type"

    @with_test_config
    def test_list_resolves_id_path_once_for_all_rows(self, client: TestClient, test_provider: MockConfigProvider, monkeypatch):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}})
        _mock_db(
            test_provider,
            fetchall=[
                {"target_id": 1, "name": "A", "description": None},
                {"target_id": 2, "name": "B", "description": None},
                {"target_id": 3, "name": "C", "description": None},
            ],
        )
        resolved: list[str] = []

        def counting_resolve_id_path(entity_type: str) -> str:
            resolved.append(entity_type)
            return "feature_type"

        monkeypatch.setattr(record_selection_module, "resolve_id_path", counting_resolve_id_path)

        response = client.get("/records/feature_type")

        assert response.status_code == 200
        assert len(response.json()["items"]) == 3
        assert resolved == ["feature_type"]

    @with_test_config
    def test_database_failure_is_not_an_empty_success(self, client: TestClient, test_provider: MockConfigProvider, monkeypatch):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}})

        async def failing_list(entity_type: str, policy: Any) -> bytes:
            raise psycopg.OperationalError("database unavailable")

        monkeypatch.setattr(router_module, "collect_browse_list", failing_list)

        response = client.get("/records/feature_type")

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"


class TestDetails:
    """Exact-ID and URI lookups share the list projection and identifier rules."""

    @with_test_config
    def test_exact_lookup_by_target_id(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"identifier_search_supported": True}})
        _mock_db(test_provider, fetchone={"target_id": 424242, "name": "Alpha", "description": "desc"})

        response = client.get("/records/feature_type/details?target_id=424242")

        assert response.status_code == 200
        item = response.json()["item"]
        assert item["target_id"] == 424242
        assert item["id"] == f"{ID_BASE}feature_type/424242"
        assert item["name"] == "Alpha"
        assert item["description"] == "desc"

    @with_test_config
    def test_uri_lookup_accepts_leading_zeros_and_case(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"details_supported": True}})
        _mock_db(test_provider, fetchone={"target_id": 7, "name": "Pit", "description": None})

        response = client.get("/records/feature_type/details", params={"id": "https://W3ID.ORG/sead/id/feature_type/007"})

        assert response.status_code == 200
        assert response.json()["item"]["id"] == f"{ID_BASE}feature_type/7"

    @pytest.mark.parametrize(
        ("params"),
        [
            {},
            {"id": f"{ID_BASE}feature_type/7", "target_id": "7"},
            {"target_id": ["7", "8"]},
        ],
    )
    @with_test_config
    def test_both_neither_and_repeated_identifiers_are_rejected(self, client: TestClient, test_provider: MockConfigProvider, params):
        _set_selection(test_provider, {"feature_type": {"details_supported": True, "identifier_search_supported": True}})
        _mock_db(test_provider)

        response = client.get("/records/feature_type/details", params=params)

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"

    @pytest.mark.parametrize(
        "candidate_id",
        [
            f"{ID_BASE}feature_type/0",
            f"{ID_BASE}feature_type/１２３",
            "not-a-uri",
            f"{ID_BASE}country/7",
            f"{ID_BASE}feature_type/7/extra",
        ],
    )
    @with_test_config
    def test_malformed_uris_are_rejected(self, client: TestClient, test_provider: MockConfigProvider, candidate_id):
        _set_selection(test_provider, {"feature_type": {"details_supported": True}})
        _mock_db(test_provider)

        response = client.get("/records/feature_type/details", params={"id": candidate_id})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"

    @with_test_config
    def test_missing_record_returns_not_found(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"identifier_search_supported": True}})
        _mock_db(test_provider, fetchone=None)

        response = client.get("/records/feature_type/details?target_id=123")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "record_not_found"

    @with_test_config
    def test_id_too_large_for_target_column_is_absent(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"identifier_search_supported": True}})
        _mock_db(test_provider, fetchone={"target_id": 1, "name": "A", "description": None})

        response = client.get(f"/records/feature_type/details?target_id={POSTGRES_INTEGER_MAX + 1}")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "record_not_found"

    @with_test_config
    def test_target_id_over_the_conversion_limit_is_absent(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"identifier_search_supported": True}})
        cursor = _mock_db(test_provider, fetchone=None)

        response = client.get(f"/records/feature_type/details?target_id={'9' * 5000}")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "record_not_found"
        cursor.execute.assert_not_awaited()

    @pytest.mark.parametrize("target_id", ["000", "0", "12.5", "-3", "abc"])
    @with_test_config
    def test_non_positive_and_non_decimal_target_ids_are_rejected(self, client: TestClient, test_provider: MockConfigProvider, target_id):
        _set_selection(test_provider, {"feature_type": {"identifier_search_supported": True}})
        _mock_db(test_provider)

        response = client.get("/records/feature_type/details", params={"target_id": target_id})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"

    @with_test_config
    def test_disabled_capability_is_reported(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"details_supported": True}})

        response = client.get("/records/feature_type/details?target_id=7")

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unsupported_capability"

    @with_test_config
    def test_database_failure_is_not_not_found(self, client: TestClient, test_provider: MockConfigProvider, monkeypatch):
        _set_selection(test_provider, {"feature_type": {"identifier_search_supported": True}})

        async def failing_lookup(entity_type: str, target_id: int) -> Any:
            raise psycopg.OperationalError("database unavailable")

        monkeypatch.setattr(router_module, "fetch_record_row", failing_lookup)

        response = client.get("/records/feature_type/details?target_id=7")

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"


class TestInteractiveSearch:
    """Marked interactive search is bounded and consistent with lists and details."""

    @with_test_config
    def test_feature_type_search_includes_configured_substring_candidates(
        self, client: TestClient, test_provider: MockConfigProvider, monkeypatch: pytest.MonkeyPatch
    ):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})

        async def find_candidates(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
            assert query == "sampl"
            assert limit == 10
            return [
                {
                    "feature_type_id": 4,
                    "label": "Samples taken by",
                    "name_sim": 0.26,
                    "label_ambiguous": False,
                },
                {
                    "feature_type_id": 3,
                    "label": "Samples processed by",
                    "name_sim": 0.28,
                    "label_ambiguous": False,
                },
            ]

        monkeypatch.setattr(ConfiguredClassifierStrategy, "find_interactive_candidates", find_candidates)
        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "sampl", "type": "feature_type", "limit": 10}}},
        )

        assert response.status_code == 200
        candidates = response.json()["q0"]["result"]
        assert {candidate["name"] for candidate in candidates} == {"Samples processed by", "Samples taken by"}

    @with_test_config
    def test_feature_type_search_round_trips_to_the_same_uri(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(
            test_provider,
            {"feature_type": {"search_supported": True, "browse_supported": True, "identifier_search_supported": True}},
        )
        cursor = _mock_db(test_provider, fetchone={"target_id": 5, "name": "Pit", "description": "A pit"})
        cursor.fetchall.return_value = [
            {"feature_type_id": 5, "label": "Pit", "description": "A pit", "name_sim": 0.95, "label_ambiguous": False}
        ]

        search = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "pit", "type": "feature_type", "limit": 10}}},
        )
        assert search.status_code == 200
        candidate = search.json()["q0"]["result"][0]
        assert candidate["id"] == f"{ID_BASE}feature_type/5"

        cursor.fetchall.return_value = [{"target_id": 5, "name": "Pit", "description": "A pit"}]
        listing = client.get("/records/feature_type")
        assert listing.json()["items"][0]["id"] == candidate["id"]

        details = client.get("/records/feature_type/details?target_id=5")
        assert details.json()["item"]["id"] == candidate["id"]

    @with_test_config
    def test_country_search_uses_country_scoped_fuzzy_function(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"country": {"search_supported": True}})
        cursor = _mock_db(test_provider, fetchall=[{"location_id": 3, "label": "Sweden", "name_sim": 0.9, "label_ambiguous": False}])

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "sweden", "type": "country", "limit": 5}}},
        )

        assert response.status_code == 200
        assert response.json()["q0"]["result"][0]["id"] == f"{ID_BASE}country/3"
        fuzzy_search = next(call for call in cursor.execute.call_args_list if "fuzzy_country" in call.args[0])
        sql, params = fuzzy_search.args
        assert "fuzzy_country" in sql
        assert params["label_threshold"] == 0.30
        assert params["description_threshold"] == 0.50

    @with_test_config
    def test_country_search_suppresses_duplicate_normalized_labels(self, client: TestClient, test_provider: MockConfigProvider):
        """Country adopts simple-classifier search semantics, including duplicate-label suppression."""
        _set_selection(test_provider, {"country": {"search_supported": True}})
        _mock_db(
            test_provider,
            fetchall=[
                {"location_id": 3, "label": "Åland", "name_sim": 0.95, "label_ambiguous": False},
                {"location_id": 4, "label": "Aland", "name_sim": 0.94, "label_ambiguous": False},
            ],
        )

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "aland", "type": "country", "limit": 5}}},
        )

        assert response.status_code == 200
        assert [item["match"] for item in response.json()["q0"]["result"]] == [False, False]

    @with_test_config
    def test_flagged_label_is_not_a_match_at_limit_one(self, client: TestClient, test_provider: MockConfigProvider):
        """The SQL flag covers a duplicate the limit dropped, so the one row is a suggestion only."""
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})
        _mock_db(
            test_provider,
            fetchall=[{"feature_type_id": 5, "label": "Flint", "name_sim": 1.0, "label_ambiguous": True}],
        )

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "flint", "type": "feature_type", "limit": 1}}},
        )

        assert response.status_code == 200
        result = response.json()["q0"]["result"]
        assert len(result) == 1
        assert result[0]["match"] is False
        assert "label_ambiguous" not in result[0]

    @with_test_config
    def test_unflagged_exact_label_still_matches_at_limit_one(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})
        _mock_db(
            test_provider,
            fetchall=[{"feature_type_id": 5, "label": "Flint", "name_sim": 1.0, "label_ambiguous": False}],
        )

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "flint", "type": "feature_type", "limit": 1}}},
        )

        assert response.status_code == 200
        result = response.json()["q0"]["result"]
        assert len(result) == 1
        assert result[0]["match"] is True
        assert set(result[0]) == {"id", "name", "score", "match", "type"}

    @with_test_config
    def test_search_miss_returns_empty_result(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})
        _mock_db(test_provider, fetchall=[])

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "nothing", "type": "feature_type", "limit": 10}}},
        )

        assert response.status_code == 200
        assert response.json()["q0"]["result"] == []

    @with_test_config
    def test_search_limit_above_cap_is_rejected_before_query(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(
            test_provider,
            {"feature_type": {"search_supported": True}},
            interactive_search_max_results=10,
        )
        _mock_db(test_provider)

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "pit", "type": "feature_type", "limit": 11}}},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "search_limit_exceeded"

    @pytest.mark.parametrize("limit", [None, 0, -1, 1.5, "10"])
    @with_test_config
    def test_malformed_requests_are_rejected_before_query(self, client: TestClient, test_provider: MockConfigProvider, limit):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})
        cursor = _mock_db(test_provider)

        query: dict[str, Any] = {"query": "pit", "type": "feature_type"}
        if limit is not None:
            query["limit"] = limit
        response = client.post("/reconcile", headers={"X-Record-Selection": "interactive"}, json={"queries": {"q0": query}})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"
        cursor.execute.assert_not_awaited()

    @with_test_config
    def test_integer_literal_over_the_conversion_limit_is_rejected(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})
        cursor = _mock_db(test_provider)

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive", "Content-Type": "application/json"},
            content=f'{{"queries": {{"q0": {{"query": "pit", "type": "feature_type", "limit": {"9" * 5000}}}}}}}',
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"
        cursor.execute.assert_not_awaited()

    @with_test_config
    def test_multiple_queries_are_rejected(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})
        _mock_db(test_provider)

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={
                "queries": {
                    "q0": {"query": "pit", "type": "feature_type", "limit": 5},
                    "q1": {"query": "hearth", "type": "feature_type", "limit": 5},
                }
            },
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"

    @with_test_config
    def test_missing_type_is_rejected(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})
        _mock_db(test_provider)

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "pit", "limit": 5}}},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_request"

    @with_test_config
    def test_disabled_search_capability_is_reported(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"browse_supported": True}})

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "pit", "type": "feature_type", "limit": 5}}},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unsupported_capability"

    @with_test_config
    def test_unregistered_type_is_reported(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "uppsala", "type": "site", "limit": 5}}},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "unsupported_type"

    @with_test_config
    def test_form_encoded_interactive_search_is_supported(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})
        cursor = _mock_db(test_provider)
        cursor.fetchall.return_value = [
            {"feature_type_id": 9, "label": "Ditch", "description": None, "name_sim": 0.8, "label_ambiguous": False}
        ]

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            data={"queries": json.dumps({"q0": {"query": "ditch", "type": "feature_type", "limit": 5}})},
        )

        assert response.status_code == 200
        assert response.json()["q0"]["result"][0]["id"] == f"{ID_BASE}feature_type/9"

    @with_test_config
    def test_database_failure_returns_503(self, client: TestClient, test_provider: MockConfigProvider, monkeypatch):
        _set_selection(test_provider, {"feature_type": {"search_supported": True}})

        async def failing_search(entity_type: str, query_text: str, limit: int) -> Any:
            raise psycopg.OperationalError("database unavailable")

        monkeypatch.setattr(router_module, "search_interactive", failing_search)

        response = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "pit", "type": "feature_type", "limit": 5}}},
        )

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "database_unavailable"

    @with_test_config
    def test_unmarked_batch_requests_are_unchanged(self, client: TestClient, test_provider: MockConfigProvider, monkeypatch):
        _set_selection(test_provider, {"feature_type": {}})

        captured: dict[str, Any] = {}

        async def fake_reconcile_queries(queries: dict[str, Any]) -> dict[str, Any]:
            captured.update(queries)
            return {"q0": {"result": []}}

        monkeypatch.setattr(router_module, "reconcile_queries", fake_reconcile_queries)

        response = client.post("/reconcile", json={"queries": {"q0": {"query": "test", "type": "site"}}})

        assert response.status_code == 200
        assert captured == {"q0": {"query": "test", "type": "site"}}


class TestBatchCandidateConversion:
    """Batch reconciliation carries the same ambiguity rule as interactive search."""

    @with_test_config
    def test_batch_flagged_label_is_not_a_match_and_hides_the_flag(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {})
        _mock_db(
            test_provider,
            fetchall=[{"feature_type_id": 5, "label": "Flint", "name_sim": 1.0, "label_ambiguous": True}],
        )

        response = client.post(
            "/reconcile",
            json={"queries": {"q0": {"query": "flint", "type": "feature_type", "limit": 1}}},
        )

        assert response.status_code == 200
        result = response.json()["q0"]["result"]
        assert len(result) == 1
        assert result[0]["match"] is False
        assert result[0]["score"] == 100.0
        assert "label_ambiguous" not in result[0]

    @with_test_config
    def test_batch_unflagged_exact_label_matches(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(test_provider, {})
        _mock_db(
            test_provider,
            fetchall=[{"feature_type_id": 5, "label": "Flint", "name_sim": 1.0, "label_ambiguous": False}],
        )

        response = client.post(
            "/reconcile",
            json={"queries": {"q0": {"query": "flint", "type": "feature_type", "limit": 1}}},
        )

        assert response.status_code == 200
        result = response.json()["q0"]["result"]
        assert result[0]["match"] is True
        assert "label_ambiguous" not in result[0]


class TestThirdSimpleClassifier:
    """A simple classifier enabled only through configuration serves every surface.

    This is the acceptance proof for a third type: the entity is already a marked
    table spec, and the only change needed to serve it is its record-selection entry.
    No Python module names it.
    """

    ENTITY_TYPE = "data_type_group"

    @with_test_config
    def test_data_type_group_serves_discovery_list_details_and_search(self, client: TestClient, test_provider: MockConfigProvider):
        _set_selection(
            test_provider,
            {
                self.ENTITY_TYPE: {
                    "search_supported": True,
                    "identifier_search_supported": True,
                    "browse_supported": True,
                    "details_supported": True,
                }
            },
        )
        cursor = _mock_db(
            test_provider,
            fetchall=[{"target_id": 7, "name": "Group", "description": None}],
            fetchone={"target_id": 7, "name": "Group", "description": None},
        )

        entry = next(item for item in client.get("/records/types").json()["types"] if item["type"] == self.ENTITY_TYPE)
        assert entry["browse_supported"] is True
        assert entry["search_supported"] is True
        assert entry["id_path"] == self.ENTITY_TYPE
        assert [field["name"] for field in entry["display_fields"]] == ["name", "target_id", "description"]

        listing = client.get(f"/records/{self.ENTITY_TYPE}")
        assert listing.status_code == 200
        assert listing.json()["items"][0]["id"] == f"{ID_BASE}{self.ENTITY_TYPE}/7"
        assert f"from authority.{self.ENTITY_TYPE}" in cursor.execute.call_args.args[0]

        details = client.get(f"/records/{self.ENTITY_TYPE}/details?target_id=7")
        assert details.status_code == 200
        assert details.json()["item"]["id"] == f"{ID_BASE}{self.ENTITY_TYPE}/7"

        cursor.fetchall.return_value = [{"data_type_group_id": 7, "label": "Group", "name_sim": 0.9, "label_ambiguous": False}]
        search = client.post(
            "/reconcile",
            headers={"X-Record-Selection": "interactive"},
            json={"queries": {"q0": {"query": "group", "type": self.ENTITY_TYPE, "limit": 5}}},
        )

        assert search.status_code == 200
        assert search.json()["q0"]["result"][0]["id"] == f"{ID_BASE}{self.ENTITY_TYPE}/7"
        fuzzy_search = next(call for call in cursor.execute.call_args_list if f"fuzzy_{self.ENTITY_TYPE}" in call.args[0])
        sql, params = fuzzy_search.args
        assert f"fuzzy_{self.ENTITY_TYPE}" in sql
        assert params["label_threshold"] == 0.30


class TestRecordIdentifierParsing:
    """The shared parser keeps the legacy site semantics for every type."""

    @pytest.mark.parametrize(
        "candidate_id",
        [
            f"{ID_BASE}feature_type/1",
            f"{ID_BASE}feature_type/01",
            "https://W3ID.ORG/sead/id/feature_type/1",
        ],
    )
    def test_valid_uris_parse(self, candidate_id: str) -> None:
        assert parse_record_uri(candidate_id, "feature_type", ID_BASE) == 1

    @pytest.mark.parametrize(
        "candidate_id",
        [
            f"{ID_BASE}country/1",
            f"{ID_BASE}feature_type/0",
            f"{ID_BASE}feature_type/-2",
            f"{ID_BASE}feature_type/1/extra",
            f"{ID_BASE}feature_type/1?x=1",
            f"{ID_BASE}feature_type/1#frag",
            "feature_type/1",
        ],
    )
    def test_invalid_uris_do_not_parse(self, candidate_id: str) -> None:
        assert parse_record_uri(candidate_id, "feature_type", ID_BASE) is None
