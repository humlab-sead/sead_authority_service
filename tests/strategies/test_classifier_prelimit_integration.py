"""Generated-SQL regression for duplicate-label detection before the row limit.

The test installs the tracked `feature_type` (zero description weight) and `rdb_code`
(positive description weight) functions in a disposable PostgreSQL container that this
module starts and stops. It reads the function results as JSON, converts them with the
real configured strategy, and feeds the same rows into both reconciliation response paths.

The test is opt-in because it needs Podman and the PostgreSQL image:

    CLASSIFIER_SQL_INTEGRATION=1 .venv/bin/python -m pytest \\
        tests/strategies/test_classifier_prelimit_integration.py

When the variable is set, a missing image, Podman, container startup, SQL, or cleanup
failure fails the test instead of skipping it.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.router import router
from src.configuration import MockConfigProvider
from src.strategies.configured_classifier import initialize_classifiers
from src.strategies.strategy import Strategies
from tests.decorators import with_test_config

pytestmark = pytest.mark.integration

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_IMAGE = "docker.io/library/postgres:17-alpine"
INTEGRATION_ENV = "CLASSIFIER_SQL_INTEGRATION"
STARTUP_TIMEOUT_SECONDS = 60
ID_BASE = "https://w3id.org/sead/id/"
GENERATED_KEYS = (
    "feature_type",
    "rdb_code",
    "colour",
    "feature",
    "taxa_common_names",
    "rdb_system",
    "taxa_synonym",
    "dating_lab",
    "value_class",
)

BOOTSTRAP_SQL = """
create extension if not exists unaccent;
create extension if not exists pg_trgm;

create schema if not exists authority;

create or replace function authority.immutable_unaccent(p_value text)
returns text language sql immutable parallel safe
as $$
  select public.unaccent('public.unaccent'::regdictionary, p_value)
$$;

create table public.tbl_feature_types (
  feature_type_id integer primary key,
  feature_type_name text,
  feature_type_description text
);

create table public.tbl_methods (
  method_id integer primary key,
  method_name text,
  description text,
  method_abbrev_or_alt_name text
);

create table public.tbl_colours (
  colour_id integer primary key,
  colour_name text,
  method_id integer
);

create table public.tbl_features (
  feature_id integer primary key,
  feature_name text,
  feature_description text,
  feature_type_id integer
);

create table public.tbl_taxa_tree_master (
  taxon_id integer primary key,
  species text
);

create table public.tbl_taxa_common_names (
  taxon_common_name_id integer primary key,
  common_name text,
  taxon_id integer
);

create table public.tbl_taxa_synonyms (
  synonym_id integer primary key,
  synonym text,
  taxon_id integer
);

create table public.tbl_rdb_systems (
  rdb_system_id integer primary key,
  rdb_system text
);

create table public.tbl_rdb_codes (
  rdb_code_id integer primary key,
  rdb_category text,
  rdb_definition text,
  rdb_system_id integer
);

create table public.tbl_dating_labs (
  dating_lab_id integer primary key,
  lab_name text,
  international_lab_id text
);

create table public.tbl_value_types (
  value_type_id integer primary key,
  name text,
  description text
);

create table public.tbl_value_classes (
  value_class_id integer primary key,
  name text,
  description text,
  value_type_id integer,
  method_id integer
);

insert into public.tbl_feature_types (feature_type_id, feature_type_name, feature_type_description) values
  (1, 'Cafe', 'A place to eat'),
  (2, 'Café', 'A place to drink'),
  (3, 'Chert', 'A hard stone');

insert into public.tbl_methods (method_id, method_name, description, method_abbrev_or_alt_name) values
  (1, 'Tempera', 'Egg tempera paint', 'TEM'),
  (2, 'Oil', 'Oil paint', 'OIL');

insert into public.tbl_colours (colour_id, colour_name, method_id) values
  (1, 'Red', 1),
  (2, 'Red', 2),
  (3, 'BLUE', 1),
  (4, 'Red', 1);

insert into public.tbl_features (feature_id, feature_name, feature_description, feature_type_id) values
  (1, 'Midden', 'A refuse deposit', 3),
  (2, 'Midden', 'A refuse deposit', 1),
  (3, 'Flint scatter', 'midden deposit', 3);

insert into public.tbl_taxa_tree_master (taxon_id, species) values (1, 'Quercus robur');

insert into public.tbl_taxa_common_names (taxon_common_name_id, common_name, taxon_id) values (1, 'Oak', 1);

insert into public.tbl_taxa_synonyms (synonym_id, synonym, taxon_id) values (1, 'Quercus pedunculata', 1);

insert into public.tbl_rdb_systems (rdb_system_id, rdb_system) values
  (1, 'UK Red Data Book'),
  (2, 'UK Red Data Book');

insert into public.tbl_rdb_codes (rdb_code_id, rdb_category, rdb_definition, rdb_system_id) values
  (1, 'Cafe', 'Coffee house', 1),
  (2, 'Café', 'Coffee shop', 1),
  (3, 'Chert', 'Stone', 1),
  (4, 'Ceramic', 'cafe', 1),
  (5, 'Cobalt', 'Canteen', 1);

insert into public.tbl_dating_labs (dating_lab_id, lab_name, international_lab_id) values
  (1, 'Uppsala', 'Ua'),
  (2, null, 'Lu');

insert into public.tbl_value_types (value_type_id, name, description) values
  (1, 'Length', 'Linear measure'),
  (2, 'Weight', 'Mass measure');

insert into public.tbl_value_classes (value_class_id, name, description, value_type_id, method_id) values
  (1, 'Alpha', 'First class', 1, 1),
  (2, 'Alpha', 'First class', 1, 2),
  (3, 'Beta', 'Second class', 2, 1);
"""


@dataclass(frozen=True)
class DisposablePostgres:
    """A test-owned container that answers psql commands."""

    container_name: str

    def execute(self, sql: str) -> None:
        """Runs SQL and raises when PostgreSQL reports an error."""
        self._psql(sql)

    def rows(self, sql: str) -> list[dict[str, Any]]:
        """Runs a query that returns one JSON array of row objects."""
        output: str = self._psql(sql, json_output=True)
        parsed: Any = json.loads(output) if output else []
        if not isinstance(parsed, list):
            raise AssertionError(f"Expected a JSON array from psql, got: {output!r}")
        return [row if isinstance(row, dict) else {} for row in parsed]

    def _psql(self, sql: str, *, json_output: bool = False) -> str:
        command: list[str] = ["podman", "exec", "-i", self.container_name, "psql", "-X"]
        if json_output:
            command.extend(["-A", "-t"])
        command.extend(["-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "postgres", "-c", sql])
        completed = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        if completed.returncode != 0:
            raise AssertionError(f"psql failed for:\n{sql}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}")
        return completed.stdout.strip()


def _podman(*arguments: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["podman", *arguments], capture_output=True, text=True, timeout=120, check=False)
    if completed.returncode != 0:
        raise AssertionError(f"podman {' '.join(arguments)} failed:\n{completed.stderr}")
    return completed


def _wait_until_ready(container_name: str) -> None:
    deadline: float = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    last_error: str = ""
    while time.monotonic() < deadline:
        process = subprocess.run(
            ["podman", "exec", container_name, "cat", "/proc/1/comm"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if process.returncode == 0 and process.stdout.strip() == "postgres":
            completed = subprocess.run(
                ["podman", "exec", container_name, "pg_isready", "-U", "postgres", "-d", "postgres"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if completed.returncode == 0:
                return
            last_error = f"{completed.stdout}\n{completed.stderr}"
        else:
            last_error = f"Final PostgreSQL process not started: {process.stdout}\n{process.stderr}"
        time.sleep(0.2)
    logs: subprocess.CompletedProcess[str] = subprocess.run(
        ["podman", "logs", container_name], capture_output=True, text=True, timeout=30, check=False
    )
    raise AssertionError(f"PostgreSQL did not become ready within {STARTUP_TIMEOUT_SECONDS}s:\n{last_error}\n{logs.stdout}\n{logs.stderr}")


def _remove_container(container_name: str) -> None:
    completed = subprocess.run(
        ["podman", "rm", "--force", "--time", "5", container_name], capture_output=True, text=True, timeout=60, check=False
    )
    if completed.returncode != 0 and "no such container" not in completed.stderr.lower():
        raise AssertionError(f"Could not remove container {container_name}:\n{completed.stderr}")


@pytest.fixture(name="bootstrapped")
def _bootstrapped() -> Iterator[DisposablePostgres]:
    """Starts a network-isolated container, installs the generated SQL twice, and removes it."""
    if os.environ.get(INTEGRATION_ENV) != "1":
        pytest.skip(f"Set {INTEGRATION_ENV}=1 to run the generated-SQL integration test")

    container_name: str = f"sead-authority-pre-limit-{uuid.uuid4().hex[:12]}"
    _podman(
        "run",
        "--rm",
        "--detach",
        "--name",
        container_name,
        "--network",
        "none",
        "--env",
        "POSTGRES_HOST_AUTH_METHOD=trust",
        CONTAINER_IMAGE,
    )
    database = DisposablePostgres(container_name)
    try:
        _wait_until_ready(container_name)
        database.execute(BOOTSTRAP_SQL)
        for key in GENERATED_KEYS:
            generated_sql: str = (REPOSITORY_ROOT / "schema/generated" / f"{key}.sql").read_text(encoding="utf-8")
            database.execute(generated_sql)
            database.execute(generated_sql)
        yield database
    finally:
        _remove_container(container_name)


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _fuzzy_rows(database: DisposablePostgres, key: str, query: str, limit: int) -> list[dict[str, Any]]:
    """Returns the generated fuzzy function's rows with every returned column."""
    sql: str = "select coalesce(json_agg(row_to_json(f)), '[]'::json) " f"from authority.fuzzy_{key}({_literal(query)}, {limit}) f"
    return database.rows(sql)


def _scoped_fuzzy_rows(database: DisposablePostgres, key: str, query: str, limit: int, context: str | None) -> list[dict[str, Any]]:
    """Returns scoped fuzzy rows for an explicit parent context, or for no context."""
    context_literal: str = "null" if context is None else _literal(context)
    sql: str = (
        "select coalesce(json_agg(row_to_json(f)), '[]'::json) "
        f"from authority.fuzzy_{key}({_literal(query)}, {limit}, 0.30, 0.50, {context_literal}) f"
    )
    return database.rows(sql)


def _configured_strategy(key: str) -> Any:
    initialize_classifiers()
    strategy_cls: Any = Strategies.items[key]
    return strategy_cls()


def _matches(candidates: list[dict[str, Any]]) -> list[bool]:
    return [bool(candidate["match"]) for candidate in candidates]


def _enable_feature_type_search(provider: MockConfigProvider) -> None:
    """Enables only interactive feature-type search for one test."""
    entry: dict[str, bool] = {
        "search_supported": True,
        "identifier_search_supported": False,
        "browse_supported": False,
        "details_supported": False,
        "export_verification_supported": False,
    }
    provider.get_config().update(
        {
            "options:record_selection": {
                "version": 1,
                "browse_max_rows": 500,
                "browse_max_bytes": 1_048_576,
                "interactive_search_max_results": 50,
                "types": {"feature_type": entry},
            }
        }
    )


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@with_test_config
def test_zero_weight_branch_flags_duplicates_hidden_by_the_limit(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    """`feature_type` scores labels only, so the flag is the only duplicate signal."""
    hidden: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "feature_type", "cafe", 1)
    assert len(hidden) == 1
    assert hidden[0]["label_ambiguous"] is True

    full: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "feature_type", "cafe", 10)
    assert {row["label"] for row in full} == {"Cafe", "Café"}
    assert all(row["label_ambiguous"] is True for row in full)

    strategy = _configured_strategy("feature_type")
    assert _matches(strategy.as_candidates(hidden, "cafe")) == [False]
    assert _matches(strategy.as_candidates(full, "cafe")) == [False, False]
    assert "label_ambiguous" not in strategy.as_candidates(full, "cafe")[0]


@with_test_config
def test_unique_label_is_unambiguous_and_still_matches(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    rows: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "feature_type", "chert", 1)

    assert len(rows) == 1
    assert rows[0]["label"] == "Chert"
    assert rows[0]["label_ambiguous"] is False

    candidates = _configured_strategy("feature_type").as_candidates(rows, "chert")
    assert _matches(candidates) == [True]


@with_test_config
def test_weighted_branch_keeps_scoring_and_marks_only_eligible_duplicates(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    """`rdb_code` adds description scoring; eligibility is decided before counting."""
    bootstrapped.execute("insert into public.tbl_rdb_codes (rdb_code_id, rdb_category, rdb_definition) values (6, 'CÉRAMIC', 'stone')")
    same_label_scores: list[dict[str, Any]] = bootstrapped.rows(
        """
        select coalesce(json_agg(json_build_object(
          'id', s.rdb_code_id,
          'norm_label', s.norm_label,
          'label_sim', similarity(s.norm_label, pq.q),
          'description_sim', strict_word_similarity(pq.q, s.norm_description)
        )), '[]'::json)
        from authority.rdb_code as s
        cross join (select authority.immutable_unaccent(lower('cafe'))::text as q) pq
        where s.rdb_code_id in (4, 6)
        """
    )
    scores_by_id: dict[int, dict[str, Any]] = {row["id"]: row for row in same_label_scores}
    assert set(scores_by_id) == {4, 6}
    assert scores_by_id[4]["norm_label"] == scores_by_id[6]["norm_label"] == "ceramic"
    assert scores_by_id[4]["label_sim"] == pytest.approx(scores_by_id[6]["label_sim"])
    assert scores_by_id[4]["label_sim"] < 0.30
    assert scores_by_id[4]["description_sim"] >= 0.50
    assert scores_by_id[6]["description_sim"] < 0.50

    limited: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "rdb_code", "cafe", 1)
    assert len(limited) == 1
    assert limited[0]["label_ambiguous"] is True

    rows: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "rdb_code", "cafe", 10)
    by_label: dict[str, dict[str, Any]] = {row["label"]: row for row in rows}

    # `Cobalt` is below both thresholds, so it is absent and cannot affect the count.
    assert set(by_label) == {"Cafe", "Café", "Ceramic"}
    assert by_label["Cafe"]["label_ambiguous"] is True
    assert by_label["Café"]["label_ambiguous"] is True
    assert by_label["Ceramic"]["label_ambiguous"] is False

    description_only: dict[str, Any] = by_label["Ceramic"]
    assert description_only["label_sim"] < 0.30
    assert description_only["label_sim"] < description_only["name_sim"] < 0.30

    candidates = _configured_strategy("rdb_code").as_candidates(rows, "cafe")
    assert _matches(candidates) == [False, False, False]

    expected: list[dict[str, Any]] = bootstrapped.rows(
        """
        select coalesce(json_agg(json_build_object(
          'label_sim', case when s.norm_label = pq.q then 1.0 else similarity(s.norm_label, pq.q) end,
          'name_sim', least(
            1.0,
            (case when s.norm_label = pq.q then 1.0 else similarity(s.norm_label, pq.q) end)
              + 0.15 * coalesce(strict_word_similarity(pq.q, s.norm_description), 0)
          )
        )), '[]'::json)
        from authority.rdb_code as s
        cross join (select authority.immutable_unaccent(lower('cafe'))::text as q) pq
        where s.label = 'Café'
        """
    )
    expected_values: dict[str, Any] = expected[0]
    assert by_label["Café"]["label_sim"] == pytest.approx(expected_values["label_sim"])
    assert by_label["Café"]["name_sim"] == pytest.approx(expected_values["name_sim"])

    both_eligible: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "rdb_code", "ceramic", 1)
    assert len(both_eligible) == 1
    assert both_eligible[0]["label_ambiguous"] is True
    assert _matches(_configured_strategy("rdb_code").as_candidates(both_eligible, "ceramic")) == [False]

    bootstrapped.execute("update public.tbl_rdb_codes set rdb_definition = 'xylophone' where rdb_code_id = 4")
    one_eligible: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "rdb_code", "xylophone", 1)
    assert len(one_eligible) == 1
    assert one_eligible[0]["rdb_code_id"] == 4
    assert one_eligible[0]["label_ambiguous"] is False
    assert _matches(_configured_strategy("rdb_code").as_candidates(one_eligible, "xylophone")) == [False]


@with_test_config
def test_weighted_branch_unique_label_still_matches(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    unique: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "rdb_code", "chert", 10)

    assert len(unique) == 1
    assert unique[0]["label"] == "Chert"
    assert unique[0]["label_ambiguous"] is False
    assert _matches(_configured_strategy("rdb_code").as_candidates(unique, "chert")) == [True]


@with_test_config
def test_both_response_paths_hide_the_flag_and_suppress_the_match(
    test_provider: MockConfigProvider,
    bootstrapped: DisposablePostgres,
) -> None:
    """The SQL rows feed the existing repository mock for interactive and batch requests."""
    rows: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "feature_type", "cafe", 1)
    _enable_feature_type_search(test_provider)
    test_provider.create_connection_mock(execute=None, fetchall=rows, fetchone=None)
    client: TestClient = _client()

    interactive = client.post(
        "/reconcile",
        headers={"X-Record-Selection": "interactive"},
        json={"queries": {"q0": {"query": "cafe", "type": "feature_type", "limit": 1}}},
    )
    assert interactive.status_code == 200
    interactive_result: list[dict[str, Any]] = interactive.json()["q0"]["result"]
    assert len(interactive_result) == 1
    assert interactive_result[0]["match"] is False
    assert "label_ambiguous" not in interactive_result[0]

    batch = client.post(
        "/reconcile",
        json={"queries": {"q0": {"query": "cafe", "type": "feature_type", "limit": 1}}},
    )
    assert batch.status_code == 200
    batch_result: list[dict[str, Any]] = batch.json()["q0"]["result"]
    assert len(batch_result) == 1
    assert batch_result[0]["id"].startswith(f"{ID_BASE}feature_type/")
    assert batch_result[0]["match"] is False
    assert "label_ambiguous" not in batch_result[0]


@with_test_config
def test_scoped_classifier_filters_context_before_ambiguity_and_limit(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    """A selected context removes other parents before duplicates are counted."""
    oil_rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "colour", "red", 10, "Oil")
    assert [row["colour_id"] for row in oil_rows] == [2]
    assert oil_rows[0]["context"] == "Oil"
    assert oil_rows[0]["context_match"] is True
    assert oil_rows[0]["label_ambiguous"] is False
    assert _matches(_configured_strategy("colour").as_candidates(oil_rows, "red", {"context": "Oil"})) == [True]

    tempera_rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "colour", "red", 1, "Tempera")
    assert len(tempera_rows) == 1
    assert tempera_rows[0]["label_ambiguous"] is True
    assert _matches(_configured_strategy("colour").as_candidates(tempera_rows, "red", {"context": "Tempera"})) == [False]

    unscoped_rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "colour", "red", 10, None)
    assert {row["colour_id"] for row in unscoped_rows} == {1, 2, 4}
    assert all(row["label_ambiguous"] is True for row in unscoped_rows)
    assert all(row["context_match"] is False for row in unscoped_rows)


@with_test_config
def test_unmatched_context_returns_non_matching_unfiltered_suggestions(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "colour", "red", 2, "Missing")

    assert len(rows) == 2
    assert all(row["context_match"] is False for row in rows)

    candidates: list[dict[str, Any]] = _configured_strategy("colour").as_candidates(rows, "red", {"context": "Missing"})
    assert [candidate["match"] for candidate in candidates] == [False, False]
    assert [candidate["context_match"] for candidate in candidates] == [False, False]


@with_test_config
def test_context_appears_first_in_the_candidate_description(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "colour", "blue", 10, "Tempera")
    assert len(rows) == 1

    candidate: dict[str, Any] = _configured_strategy("colour").as_candidates(rows, "blue", {"context": "Tempera"})[0]

    assert candidate["description"] == "Context: Tempera"
    assert candidate["context_match"] is True
    assert candidate["match"] is True


@with_test_config
def test_lookup_scores_labels_only_and_uses_parent_context(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "feature", "midden", 10, "Chert")

    assert [row["feature_id"] for row in rows] == [1]
    assert rows[0]["context"] == "Chert"
    assert rows[0]["context_match"] is True
    assert rows[0]["name_sim"] == pytest.approx(rows[0]["label_sim"])
    assert _matches(_configured_strategy("feature").as_candidates(rows, "midden", {"context": "Chert"})) == [True]

    unfiltered: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "feature", "midden", 10, None)
    assert {row["feature_id"] for row in unfiltered} == {1, 2}
    assert all(row["name_sim"] == pytest.approx(row["label_sim"]) for row in unfiltered)

    description_only: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "feature", "midden deposit", 10, None)
    assert 3 not in {row["feature_id"] for row in description_only}


@with_test_config
def test_two_parent_scope_joins_labels_in_declaration_order(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "value_class", "alpha", 10, "Tempera")

    assert [row["value_class_id"] for row in rows] == [1]
    assert rows[0]["context"] == "Length / Tempera"
    assert _matches(_configured_strategy("value_class").as_candidates(rows, "alpha", {"context": "Tempera"})) == [True]


@with_test_config
def test_unscoped_lookups_keep_duplicate_ambiguity_and_null_labels(
    test_provider: MockConfigProvider,  # pylint: disable=unused-argument
    bootstrapped: DisposablePostgres,
) -> None:
    systems: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "rdb_system", "uk red", 10)
    assert {row["rdb_system_id"] for row in systems} == {1, 2}
    assert all(row["label_ambiguous"] is True for row in systems)
    assert _matches(_configured_strategy("rdb_system").as_candidates(systems, "uk red")) == [False, False]

    named: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "dating_lab", "uppsala", 10)
    assert [row["dating_lab_id"] for row in named] == [1]
    assert _fuzzy_rows(bootstrapped, "dating_lab", "lu", 10) == []

    synonyms: list[dict[str, Any]] = _fuzzy_rows(bootstrapped, "taxa_synonym", "quercus", 10)
    assert [row["synonym_id"] for row in synonyms] == [1]


@with_test_config
def test_context_http_response_exposes_context_match_and_description(
    test_provider: MockConfigProvider,
    bootstrapped: DisposablePostgres,
) -> None:
    context_rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "feature", "midden", 10, "Chert")
    test_provider.create_connection_mock(execute=None, fetchall=context_rows, fetchone=None)
    client: TestClient = _client()

    matched = client.post(
        "/reconcile",
        json={"queries": {"q0": {"query": "midden", "type": "feature", "properties": [{"pid": "context", "v": "Chert"}]}}},
    )
    assert matched.status_code == 200
    matched_result: list[dict[str, Any]] = matched.json()["q0"]["result"]
    assert len(matched_result) == 1
    assert matched_result[0]["context_match"] is True
    assert matched_result[0]["match"] is True
    assert matched_result[0]["description"].startswith("Context: Chert")

    unscoped_rows: list[dict[str, Any]] = _scoped_fuzzy_rows(bootstrapped, "feature", "midden", 10, None)
    test_provider.create_connection_mock(execute=None, fetchall=unscoped_rows, fetchone=None)

    without_context = client.post("/reconcile", json={"queries": {"q0": {"query": "midden", "type": "feature"}}})
    assert without_context.status_code == 200
    without_context_result: list[dict[str, Any]] = without_context.json()["q0"]["result"]
    assert len(without_context_result) == 2
    assert all("context_match" not in candidate for candidate in without_context_result)
