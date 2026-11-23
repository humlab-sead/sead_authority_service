"""Unit tests for the configured classifier strategy and its candidate behavior."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.strategies.configured_classifier import (
    CANDIDATE_DESCRIPTION_LIMIT,
    ClassifierSchemaError,
    ConfiguredClassifierStrategy,
    initialize_classifiers,
    marked_classifier_keys,
)
from src.strategies.strategy import Strategies
from tests.conftest import ExtendedMockConfigProvider, MockRow
from tests.decorators import with_test_config

# pylint: disable=unused-argument


def candidate_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {"feature_type_id": 1, "label": "Flint", "name_sim": 0.8, "label_ambiguous": False}
    row.update(overrides)
    return row


def feature_type_strategy() -> ConfiguredClassifierStrategy:
    initialize_classifiers()
    strategy_cls = Strategies.items["feature_type"]
    assert issubclass(strategy_cls, ConfiguredClassifierStrategy)
    return strategy_cls()


def colour_row(**overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "colour_id": 1,
        "label": "Red",
        "name_sim": 1.0,
        "label_ambiguous": False,
        "context": "Tempera",
        "norm_context": "tempera",
        "context_match": True,
    }
    row.update(overrides)
    return row


def colour_strategy() -> ConfiguredClassifierStrategy:
    initialize_classifiers()
    strategy_cls = Strategies.items["colour"]
    assert issubclass(strategy_cls, ConfiguredClassifierStrategy)
    return strategy_cls()


def value_class_strategy() -> ConfiguredClassifierStrategy:
    initialize_classifiers()
    strategy_cls = Strategies.items["value_class"]
    assert issubclass(strategy_cls, ConfiguredClassifierStrategy)
    return strategy_cls()


class TestConfiguredClassifierRegistration:
    @with_test_config
    def test_registers_every_classifier_key(self, test_provider: ExtendedMockConfigProvider):
        classifier_keys: list[str] = initialize_classifiers()

        assert classifier_keys
        for key in classifier_keys:
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
        initialize_classifiers()
        table_specs = test_provider.get_config().get("table_specs") or {}

        for key in marked_classifier_keys():
            strategy = Strategies.items[key]()
            table_spec: dict[str, Any] = table_specs[key]

            assert strategy.get_id_path() == key
            assert strategy.get_label_field() == "label"
            assert strategy.specification["reconciliation"] == table_spec.get("reconciliation")
            fuzzy_sql: str = strategy.specification["sql_queries"]["fuzzy_find_sql"]
            prefix_sql: str = strategy.specification["sql_queries"]["prefix_find_sql"]
            details_sql: str = strategy.specification["sql_queries"]["details_sql"]
            substring_sql: str = strategy.get_repository().get_find_label_substring_sql()
            assert fuzzy_sql.startswith(f"select * from authority.fuzzy_{key}(")
            assert "%(label_threshold)s" in fuzzy_sql
            assert "%(description_threshold)s" in fuzzy_sql
            if table_spec.get("scope_columns"):
                assert "%(context)s" in fuzzy_sql
                assert [prop["id"] for prop in strategy.get_properties_meta()] == ["context"]
            else:
                assert "%(context)s" not in fuzzy_sql
                assert strategy.get_properties_meta() == []
            assert f"from authority.{key} as s" in prefix_sql
            assert "where left(s.norm_label, char_length(pq.q)) = pq.q" in prefix_sql
            assert f"from authority.{key} as s" in substring_sql
            assert "where s.norm_label like (" in substring_sql
            assert ") escape chr(92)" in substring_sql
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

    @pytest.mark.asyncio
    @with_test_config
    async def test_interactive_search_merges_substring_hits_with_fuzzy_results(
        self, monkeypatch: pytest.MonkeyPatch, test_provider: ExtendedMockConfigProvider
    ):
        strategy = feature_type_strategy()
        fuzzy_rows = [
            candidate_row(feature_type_id=9, label="Sampel", name_sim=0.8),
            candidate_row(feature_type_id=4, label="Samples taken by", name_sim=0.35),
        ]
        substring_rows = [
            candidate_row(feature_type_id=4, label="Samples taken by", name_sim=0.26),
            candidate_row(feature_type_id=3, label="Samples processed by", name_sim=0.28),
        ]
        fuzzy_search = AsyncMock(return_value=fuzzy_rows)
        substring_search = AsyncMock(return_value=substring_rows)
        monkeypatch.setattr(strategy, "find_candidates", fuzzy_search)
        monkeypatch.setattr(strategy.get_repository(), "find_by_label_substring", substring_search)

        candidates = await strategy.find_interactive_candidates("sampl", limit=3)

        assert [row["feature_type_id"] for row in candidates] == [9, 4, 3]
        assert candidates[1]["name_sim"] == 0.35
        fuzzy_search.assert_awaited_once_with(query="sampl", properties={}, limit=3)
        substring_search.assert_awaited_once_with("sampl", 3)


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
    def test_flagged_single_row_never_matches(self, test_provider: ExtendedMockConfigProvider):
        """A duplicate hidden by the SQL limit still blocks the automatic match."""
        strategy = feature_type_strategy()

        candidates = strategy.as_candidates([candidate_row(label="Flint", name_sim=1.0, label_ambiguous=True)], "flint")

        assert len(candidates) == 1
        assert candidates[0]["match"] is False
        assert candidates[0]["score"] == 100.0
        assert candidates[0]["name"] == "Flint"

    @with_test_config
    def test_flagged_similarity_hit_never_matches(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        row = candidate_row(label="Flint stone", name_sim=0.92, label_sim=0.92, label_ambiguous=True)

        candidates = strategy.as_candidates([row], "flint ston")

        assert candidates[0]["match"] is False

    @with_test_config
    def test_unflagged_similarity_hit_still_matches(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        row = candidate_row(label="Flint stone", name_sim=0.92, label_sim=0.92)

        candidates = strategy.as_candidates([row], "flint ston")

        assert candidates[0]["match"] is True

    @with_test_config
    def test_unflagged_description_only_score_never_matches(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        row = candidate_row(label="Chert", name_sim=0.95, label_sim=0.2)

        candidates = strategy.as_candidates([row], "flint")

        assert candidates[0]["score"] == 95.0
        assert candidates[0]["match"] is False

    @with_test_config
    def test_candidates_do_not_expose_the_ambiguity_flag(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()

        without_description = strategy.as_candidates([candidate_row(label_ambiguous=True)], "flint")[0]
        with_description = strategy.as_candidates([candidate_row(description="A stone", label_ambiguous=False)], "flint")[0]

        assert set(without_description) == {"id", "name", "score", "match", "type"}
        assert set(with_description) == {"id", "name", "score", "match", "type", "description"}

    @with_test_config
    def test_missing_ambiguity_flag_raises(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        row = {"feature_type_id": 1, "label": "Flint", "name_sim": 1.0}

        with pytest.raises(ClassifierSchemaError, match="label_ambiguous"):
            strategy.as_candidates([row], "flint")

    @pytest.mark.parametrize("flag", [None, 1, 0, "true"])
    @with_test_config
    def test_non_boolean_ambiguity_flag_raises(self, test_provider: ExtendedMockConfigProvider, flag: Any):
        strategy = feature_type_strategy()
        row = candidate_row(label_ambiguous=flag)

        with pytest.raises(ClassifierSchemaError, match="label_ambiguous"):
            strategy.as_candidates([row], "flint")

    @with_test_config
    def test_empty_result_needs_no_flag(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()

        assert strategy.as_candidates([], "flint") == []

    @with_test_config
    def test_duplicate_normalized_labels_never_match(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        rows = [
            candidate_row(feature_type_id=1, label="Flint", name_sim=1.0, label_ambiguous=False),
            candidate_row(feature_type_id=2, label="FLINT", name_sim=1.0, label_ambiguous=False),
        ]

        candidates = strategy.as_candidates(rows, "flint")

        assert [candidate["match"] for candidate in candidates] == [False, False]

    @with_test_config
    def test_duplicate_unaccented_labels_never_match(self, test_provider: ExtendedMockConfigProvider):
        strategy = feature_type_strategy()
        rows = [
            candidate_row(feature_type_id=1, label="Café", name_sim=1.0, label_ambiguous=False),
            candidate_row(feature_type_id=2, label="Cafe", name_sim=1.0, label_ambiguous=False),
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


class TestContextBehaviour:
    @with_test_config
    def test_context_hit_sets_context_match_and_prefixes_description(self, test_provider: ExtendedMockConfigProvider):
        strategy = colour_strategy()
        row = colour_row(description="A red pigment")

        candidate = strategy.as_candidates([row], "red", {"context": " Tempera "})[0]

        assert candidate["context_match"] is True
        assert candidate["description"] == "Context: Tempera — A red pigment"
        assert candidate["match"] is True

    @with_test_config
    def test_context_fallback_cannot_auto_match(self, test_provider: ExtendedMockConfigProvider):
        strategy = colour_strategy()
        row = colour_row(context_match=False)

        candidate = strategy.as_candidates([row], "red", {"context": "Oil"})[0]

        assert candidate["context_match"] is False
        assert candidate["match"] is False

    @with_test_config
    def test_context_match_is_omitted_without_a_supplied_property(self, test_provider: ExtendedMockConfigProvider):
        candidate = colour_strategy().as_candidates([colour_row()], "red")[0]

        assert "context_match" not in candidate
        assert candidate["description"] == "Context: Tempera"

    @with_test_config
    def test_unscoped_entity_ignores_a_supplied_context(self, test_provider: ExtendedMockConfigProvider):
        candidate = feature_type_strategy().as_candidates([candidate_row(label="Flint", name_sim=1.0)], "flint", {"context": "anything"})[0]

        assert "context_match" not in candidate
        assert candidate["match"] is True

    @with_test_config
    def test_duplicate_labels_in_the_selected_context_never_match(self, test_provider: ExtendedMockConfigProvider):
        rows = [colour_row(colour_id=1), colour_row(colour_id=2)]

        candidates = colour_strategy().as_candidates(rows, "red", {"context": "Tempera"})

        assert [candidate["match"] for candidate in candidates] == [False, False]
        assert all(candidate["context_match"] is True for candidate in candidates)

    @with_test_config
    def test_row_outside_context_is_returned_as_a_non_matching_suggestion(self, test_provider: ExtendedMockConfigProvider):
        outside = {"colour_id": 3, "label": "Red", "name_sim": 1.0, "label_ambiguous": False, "norm_context": "oil"}

        candidates = colour_strategy().as_candidates([outside], "red", {"context": "Tempera"})

        assert len(candidates) == 1
        assert candidates[0]["context_match"] is False
        assert candidates[0]["match"] is False

    @with_test_config
    def test_partial_parent_word_does_not_select_a_row(self, test_provider: ExtendedMockConfigProvider):
        """`age` is a substring of `Storage` but must not select that parent."""
        row = {"value_class_id": 1, "label": "Alpha", "name_sim": 1.0, "label_ambiguous": False, "norm_context": "length / storage"}

        candidates = value_class_strategy().as_candidates([row], "alpha", {"context": "age"})

        assert candidates[0]["context_match"] is False
        assert candidates[0]["match"] is False

    @with_test_config
    def test_single_component_of_a_composite_context_still_selects_the_row(self, test_provider: ExtendedMockConfigProvider):
        row = {"value_class_id": 1, "label": "Alpha", "name_sim": 1.0, "label_ambiguous": False, "norm_context": "length / tempera"}

        candidates = value_class_strategy().as_candidates([row], "alpha", {"context": "Tempera"})

        assert candidates[0]["context_match"] is True
        assert candidates[0]["match"] is True

    @with_test_config
    def test_context_description_is_truncated_to_the_limit(self, test_provider: ExtendedMockConfigProvider):
        row = colour_row(description="x" * (CANDIDATE_DESCRIPTION_LIMIT + 1))

        candidate = colour_strategy().as_candidates([row], "red")[0]

        assert len(candidate["description"]) == CANDIDATE_DESCRIPTION_LIMIT
        assert candidate["description"].startswith("Context: Tempera — ")


class TestConfiguredFindCandidates:
    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_passes_normalized_context_to_the_repository(
        self, monkeypatch: pytest.MonkeyPatch, test_provider: ExtendedMockConfigProvider
    ):
        strategy = colour_strategy()
        proxy = strategy.get_repository()
        find = AsyncMock(return_value=[colour_row()])
        alternate = AsyncMock(return_value=[])
        monkeypatch.setattr(proxy, "find", find)
        monkeypatch.setattr(proxy, "fetch_by_alternate_identity", alternate)

        rows = await strategy.find_candidates("red", {"context": " Tempera "}, limit=5)

        find.assert_awaited_once_with("red", 5, context="tempera")
        alternate.assert_not_awaited()
        assert rows[0]["colour_id"] == 1

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_without_context_passes_none(
        self, monkeypatch: pytest.MonkeyPatch, test_provider: ExtendedMockConfigProvider
    ):
        strategy = feature_type_strategy()
        proxy = strategy.get_repository()
        find = AsyncMock(return_value=[candidate_row()])
        monkeypatch.setattr(proxy, "find", find)

        await strategy.find_candidates("flint", {}, limit=3)

        find.assert_awaited_once_with("flint", 3, context=None)
