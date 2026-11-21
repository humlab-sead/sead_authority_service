"""Unit tests for the configured classifier strategy and its candidate behavior."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.strategies.configured_classifier import (
    CANDIDATE_DESCRIPTION_LIMIT,
    CLASSIFIER_KEYS,
    ConfiguredClassifierStrategy,
)
from src.strategies.strategy import Strategies
from tests.conftest import ExtendedMockConfigProvider, MockRow
from tests.decorators import with_test_config

# pylint: disable=unused-argument


def candidate_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"feature_type_id": 1, "label": "Flint", "name_sim": 0.8}
    row.update(overrides)
    return row


def feature_type_strategy() -> ConfiguredClassifierStrategy:
    strategy_cls = Strategies.items["feature_type"]
    assert issubclass(strategy_cls, ConfiguredClassifierStrategy)
    return strategy_cls()


class TestConfiguredClassifierRegistration:
    @with_test_config
    def test_registers_every_classifier_key(self, test_provider: ExtendedMockConfigProvider):
        for key in CLASSIFIER_KEYS:
            strategy_cls = Strategies.items[key]
            assert issubclass(strategy_cls, ConfiguredClassifierStrategy)
            assert strategy_cls.support_status == "supported"
            assert strategy_cls().key == key

    @with_test_config
    def test_feature_type_specification_comes_from_table_specs(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()

        assert strategy.get_entity_id_field() == "feature_type_id"
        assert strategy.get_label_field() == "label"
        assert strategy.get_id_path() == "feature_type"
        assert strategy.get_display_name() == "Feature Type"

        details_sql: str = strategy.specification["sql_queries"]["details_sql"]
        assert 's.feature_type_id as "ID"' in details_sql
        assert 's.label as "Name"' in details_sql
        assert 's.description as "Description"' in details_sql
        assert "from authority.feature_type as s" in details_sql

    @with_test_config
    def test_data_type_alias_uses_definition_description(self, test_provider: ExtendedMockConfigProvider):
        strategy = Strategies.items["data_type"]()

        assert strategy.get_entity_id_field() == "data_type_id"
        assert 's.description as "Description"' in strategy.specification["sql_queries"]["details_sql"]

    @with_test_config
    def test_data_type_details_keep_group_columns(self, test_provider: ExtendedMockConfigProvider):
        strategy = Strategies.items["data_type"]()

        details_sql: str = strategy.specification["sql_queries"]["details_sql"]
        assert 's.data_type_group_name as "Group"' in details_sql
        assert 's.data_type_group_description as "Group Description"' in details_sql

    @with_test_config
    def test_every_approved_classifier_resolves_its_generated_contract(self, test_provider: ExtendedMockConfigProvider):
        for key in CLASSIFIER_KEYS:
            strategy = Strategies.items[key]()

            assert strategy.get_id_path() == key
            assert strategy.get_label_field() == "label"
            assert strategy.specification["reconciliation"] == "simple"
            fuzzy_sql: str = strategy.specification["sql_queries"]["fuzzy_find_sql"]
            prefix_sql: str = strategy.specification["sql_queries"]["prefix_find_sql"]
            details_sql: str = strategy.specification["sql_queries"]["details_sql"]
            assert fuzzy_sql.startswith(f"select * from authority.fuzzy_{key}(")
            assert "%(label_threshold)s" in fuzzy_sql
            assert "%(description_threshold)s" in fuzzy_sql
            assert f"from authority.{key} as s" in prefix_sql
            assert "where left(s.norm_label, char_length(pq.q)) = pq.q" in prefix_sql
            assert f"from authority.{key} as s" in details_sql

    @with_test_config
    def test_rdb_code_uses_the_code_label_and_definition(self, test_provider: ExtendedMockConfigProvider):
        strategy = Strategies.items["rdb_code"]()

        assert strategy.get_entity_id_field() == "rdb_code_id"
        details_sql: str = strategy.specification["sql_queries"]["details_sql"]
        assert 's.rdb_code_id as "ID"' in details_sql
        assert 's.label as "Name"' in details_sql
        assert 's.description as "Description"' in details_sql

    @with_test_config
    def test_fuzzy_query_passes_both_thresholds(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        fuzzy_sql: str = strategy.specification["sql_queries"]["fuzzy_find_sql"]

        assert fuzzy_sql.startswith("select * from authority.fuzzy_feature_type(")
        assert "%(label_threshold)s" in fuzzy_sql
        assert "%(description_threshold)s" in fuzzy_sql


class TestMarkedFind:
    @pytest.mark.asyncio
    @with_test_config
    async def test_find_binds_configured_thresholds(self, monkeypatch: pytest.MonkeyPatch, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        repository = strategy.get_repository()
        fetch_all = AsyncMock(return_value=[])
        monkeypatch.setattr(repository, "fetch_all", fetch_all)

        await repository.find("flint", limit=5)

        assert fetch_all.await_count == 1
        sql, params = fetch_all.await_args.args
        assert sql == repository.get_find_fuzzy_sql()
        assert params == {
            "q": "flint",
            "n": 5,
            "label_threshold": 0.30,
            "description_threshold": 0.50,
        }

    @pytest.mark.asyncio
    @with_test_config
    async def test_classifier_suggestions_use_prefix_query(
        self, monkeypatch: pytest.MonkeyPatch, test_provider: ExtendedMockConfigProvider
    ):
        strategy = Strategies.items["contact_type"]()
        repository = strategy.get_repository()
        rows = [{"contact_type_id": 1, "label": "Samples taken by", "name_sim": 0.2}]
        fetch_all = AsyncMock(return_value=rows)
        monkeypatch.setattr(repository, "fetch_all", fetch_all)

        suggestions = await strategy.suggest_candidates(prefix="Sa", limit=10)

        assert suggestions == rows
        query, params = fetch_all.await_args.args
        assert query == strategy.specification["sql_queries"]["prefix_find_sql"]
        assert "where left(s.norm_label, char_length(pq.q)) = pq.q" in query
        assert params == {"q": "Sa", "n": 10}


class TestCandidateBehavior:
    @with_test_config
    def test_exact_unique_label_auto_matches(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()

        candidates = strategy.as_candidates([candidate_row(label="Flint", name_sim=0.8)], "flint")

        assert len(candidates) == 1
        assert candidates[0]["match"] is True
        assert candidates[0]["score"] == 80.0
        assert candidates[0]["id"].endswith("feature_type/1")

    @with_test_config
    def test_duplicate_normalized_labels_never_match(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        rows = [
            candidate_row(feature_type_id=1, label="Flint", name_sim=1.0),
            candidate_row(feature_type_id=2, label="FLINT", name_sim=1.0),
        ]

        candidates = strategy.as_candidates(rows, "flint")

        assert [candidate["match"] for candidate in candidates] == [False, False]

    @with_test_config
    def test_duplicate_unaccented_labels_never_match(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        rows = [
            candidate_row(feature_type_id=1, label="Café", name_sim=1.0),
            candidate_row(feature_type_id=2, label="Cafe", name_sim=1.0),
        ]

        candidates = strategy.as_candidates(rows, "cafe")

        assert [candidate["match"] for candidate in candidates] == [False, False]

    @with_test_config
    def test_distinct_exact_labels_can_both_match(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()

        candidates = strategy.as_candidates([candidate_row(label="Chert", name_sim=1.0)], "chert")

        assert candidates[0]["match"] is True

    @with_test_config
    def test_description_only_hit_does_not_match(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        row = candidate_row(label="Chert", name_sim=0.95, label_sim=0.2)

        candidate = strategy.as_candidate(row, "flint")

        assert candidate["score"] == 95.0
        assert candidate["match"] is False

    @with_test_config
    def test_label_similarity_above_threshold_matches(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        row = candidate_row(label="Flint stone", name_sim=0.92, label_sim=0.92)

        candidate = strategy.as_candidate(row, "flint ston")

        assert candidate["match"] is True

    @with_test_config
    def test_candidate_description_is_truncated_to_limit(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        row = candidate_row(description="x" * (CANDIDATE_DESCRIPTION_LIMIT + 1))

        candidate = strategy.as_candidate(row, "flint")

        assert len(candidate["description"]) == CANDIDATE_DESCRIPTION_LIMIT

    @with_test_config
    def test_candidate_description_at_limit_is_unchanged(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        description = "y" * CANDIDATE_DESCRIPTION_LIMIT

        candidate = strategy.as_candidate(candidate_row(description=description), "flint")

        assert candidate["description"] == description

    @with_test_config
    def test_missing_or_null_description_is_omitted(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()

        without_field = strategy.as_candidate(candidate_row(), "flint")
        with_null = strategy.as_candidate(candidate_row(description=None), "flint")

        assert "description" not in without_field
        assert "description" not in with_null


class TestConfiguredDetails:
    @pytest.mark.asyncio
    @with_test_config
    async def test_details_keep_the_full_description(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        long_description = "z" * (CANDIDATE_DESCRIPTION_LIMIT + 250)
        test_provider.create_connection_mock(fetchone=MockRow({"ID": 1, "Name": "Flint", "Description": long_description}))

        details = await strategy.get_details("1")

        assert details is not None
        assert details["Description"] == long_description

    @pytest.mark.asyncio
    @with_test_config
    async def test_details_not_found_returns_none(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        test_provider.create_connection_mock(fetchone=None)

        assert await strategy.get_details("999") is None
