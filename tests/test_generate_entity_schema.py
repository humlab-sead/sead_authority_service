from pathlib import Path
from typing import Any

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

from src.scripts.generate_entity_schema import generate_trigram_sql
from src.strategies.configured_classifier import CLASSIFIER_KEYS
from src.strategies.strategy import Strategies

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATHS = (
    REPOSITORY_ROOT / "config/config.yml",
    REPOSITORY_ROOT / "tests/config/config.yml",
    REPOSITORY_ROOT / "deployment/container/config/config.yml",
)

ENTITY_CONFIG_PATHS = (
    REPOSITORY_ROOT / "config/entities.yml",
    REPOSITORY_ROOT / "tests/config/entities.yml",
    REPOSITORY_ROOT / "deployment/container/config/entities.yml",
)

APPROVED_INVENTORY = 45

EXCLUDED_CLASSIFIER_KEYS = (
    "abundance_element_group",
    "coordinate_method_dimension",
    "dimension",
    "method",
    "modification_type",
    "sampling_context",
    "taxon",
    "value_qualifier_symbol",
)

UNREGISTERED_CLASSIFIER_KEYS = (
    "abundance_element_group",
    "coordinate_method_dimension",
    "value_qualifier_symbol",
)

SPECIALIZED_CLASSIFIER_KEYS = (
    "dimension",
    "method",
    "modification_type",
    "sampling_context",
    "taxon",
)

TARGET_MODEL_CLASSIFIER_COUNT = 53


def load_table_specs(config_path: Path) -> dict[str, Any]:
    """Loads table specifications from an entity file or an inline configuration block."""
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return config["table_specs"] if config_path.name == "config.yml" else config


def marked_keys(table_specs: dict[str, Any]) -> set[str]:
    """Returns the keys declared with `reconciliation: simple`."""
    return {key for key, table_spec in table_specs.items() if isinstance(table_spec, dict) and table_spec.get("reconciliation") == "simple"}


def render_sql(tmp_path: Path, entity_key: str, entity: dict[str, Any]) -> str:
    output_dir = tmp_path / entity_key
    output_dir.mkdir()
    environment = Environment(
        loader=FileSystemLoader(str(REPOSITORY_ROOT / "schema/templates")),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    generate_trigram_sql(entity_key, entity, environment, output_dir, force=True)
    return (output_dir / f"{entity_key}.sql").read_text(encoding="utf-8")


def test_reconciliation_thresholds_match_across_configurations() -> None:
    threshold_settings = []

    for config_path in CONFIG_PATHS:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        threshold_settings.append(config["options"]["reconciliation"])

    assert threshold_settings == [
        {"label_threshold": 0.30, "description_threshold": 0.50},
    ] * len(CONFIG_PATHS)


@pytest.mark.parametrize("description_weight", [None, 0])
def test_marked_description_without_scoring_returns_description_without_index(tmp_path: Path, description_weight: int | None) -> None:
    entity: dict[str, Any] = {
        "name": "Test Classifier",
        "table_name": "tbl_test_classifier",
        "id_column": "test_classifier_id",
        "label_column": "test_classifier_name",
        "description_column": "test_classifier_description",
        "reconciliation": "simple",
    }
    if description_weight is not None:
        entity["description_match_weight"] = description_weight

    sql = render_sql(tmp_path, "test_classifier", entity)

    assert "t.test_classifier_description as description" in sql
    assert "as norm_description" in sql
    assert "description text" in sql
    assert "strict_word_similarity" not in sql
    assert "_norm_desc_trgm" not in sql
    assert "p_label_threshold double precision default 0.30" in sql
    assert "p_description_threshold double precision default 0.50" in sql
    assert "where case when s.norm_label = pq.q then 1.0" in sql
    assert "s.norm_label % pq.q" not in sql


def test_marked_positive_weight_scores_and_indexes_description(tmp_path: Path) -> None:
    entity = {
        "name": "Test Classifier",
        "table_name": "tbl_test_classifier",
        "id_column": "test_classifier_id",
        "label_column": "test_classifier_name",
        "description_column": "test_classifier_description",
        "description_match_weight": 0.15,
        "reconciliation": "simple",
    }

    sql = render_sql(tmp_path, "test_classifier", entity)

    assert "t.test_classifier_description as description" in sql
    assert "as norm_description" in sql
    assert "tbl_test_classifier_norm_desc_trgm" in sql
    assert "strict_word_similarity(pq.q, s.norm_description)" in sql
    assert "scored.label_sim >= p_label_threshold" in sql
    assert "scored.description_sim >= p_description_threshold" in sql
    assert "filtered.label_sim + 0.15 * filtered.description_sim" in sql
    assert "label_sim double precision" in sql
    assert "case when s.norm_label = pq.q then 1.0" in sql
    assert "s.norm_label % pq.q" not in sql
    assert "<<%" not in sql


def test_marked_entity_without_description_keeps_three_return_columns(tmp_path: Path) -> None:
    entity = {
        "name": "Test Classifier",
        "table_name": "tbl_test_classifier",
        "id_column": "test_classifier_id",
        "label_column": "test_classifier_name",
        "description_column": None,
        "reconciliation": "simple",
    }

    sql = render_sql(tmp_path, "test_classifier", entity)

    assert "description text" not in sql
    assert "norm_description" not in sql
    assert "returns table (\n  test_classifier_id integer,\n  label text,\n  name_sim double precision" in sql
    assert "p_label_threshold double precision default 0.30" in sql
    assert "p_description_threshold double precision default 0.50" in sql


@pytest.mark.parametrize("entity_key", ["site", "method", "location"])
def test_unmarked_entities_render_tracked_sql_unchanged(tmp_path: Path, entity_key: str) -> None:
    entities = yaml.safe_load((REPOSITORY_ROOT / "config/entities.yml").read_text(encoding="utf-8"))
    generated = render_sql(tmp_path, entity_key, entities[entity_key])
    tracked = (REPOSITORY_ROOT / "schema/generated" / f"{entity_key}.sql").read_text(encoding="utf-8")

    assert generated == tracked


def test_unmarked_filter_parameters_keep_legacy_function_shape(tmp_path: Path) -> None:
    entity = {
        "name": "Filtered Classifier",
        "table_name": "tbl_filtered_classifier",
        "id_column": "filtered_classifier_id",
        "label_column": "filtered_classifier_name",
        "description_column": None,
        "filter_params": [
            {
                "name": "filter_ids",
                "type": "integer[]",
                "default": "null",
                "cte_definition": "select unnest(filter_ids) as filter_id",
                "join_clause": "join filter_params using (filter_id)",
                "where_clause": "and filter_id is not null",
            }
        ],
    }

    sql = render_sql(tmp_path, "filtered_classifier", entity)

    assert "p_limit integer default 10,\n  filter_ids integer[] default null" in sql
    assert "where s.norm_label % pq.q" in sql
    assert "join filter_params using (filter_id)" in sql
    assert "and filter_id is not null" in sql


def test_marked_filter_parameters_are_preserved_with_description_scoring(tmp_path: Path) -> None:
    entity = {
        "name": "Filtered Classifier",
        "table_name": "tbl_filtered_classifier",
        "id_column": "filtered_classifier_id",
        "label_column": "filtered_classifier_name",
        "description_column": "filtered_classifier_description",
        "description_match_weight": 0.15,
        "reconciliation": "simple",
        "filter_params": [
            {
                "name": "filter_ids",
                "type": "integer[]",
                "default": "null",
                "cte_definition": "select unnest(filter_ids) as filter_id",
                "join_clause": "join filter_params using (filter_id)",
                "where_clause": "and filter_id is not null",
            }
        ],
    }

    sql = render_sql(tmp_path, "filtered_classifier", entity)

    assert "p_description_threshold double precision default 0.50,\n  filter_ids integer[] default null" in sql
    assert "select unnest(filter_ids) as filter_id" in sql
    assert "join filter_params using (filter_id)" in sql
    assert "and filter_id is not null" in sql


REFERENCE_ENTITY_CONFIG_PATHS = (
    REPOSITORY_ROOT / "config/entities.yml",
    REPOSITORY_ROOT / "tests/config/entities.yml",
    REPOSITORY_ROOT / "deployment/container/config/entities.yml",
)


def test_approved_classifier_inventory_matches_marked_entries() -> None:
    expected_keys = set(CLASSIFIER_KEYS)

    assert len(CLASSIFIER_KEYS) == len(expected_keys) == APPROVED_INVENTORY
    for config_path in ENTITY_CONFIG_PATHS:
        assert marked_keys(load_table_specs(config_path)) == expected_keys, config_path

    inline_test_specs = load_table_specs(REPOSITORY_ROOT / "tests/config/config.yml")
    assert marked_keys(inline_test_specs) == expected_keys


def test_excluded_classifiers_are_not_generically_registered() -> None:
    assert len(CLASSIFIER_KEYS) + len(EXCLUDED_CLASSIFIER_KEYS) == TARGET_MODEL_CLASSIFIER_COUNT

    for key in EXCLUDED_CLASSIFIER_KEYS:
        assert key not in CLASSIFIER_KEYS

    for key in UNREGISTERED_CLASSIFIER_KEYS:
        assert key not in Strategies.items

    for specialized_key in SPECIALIZED_CLASSIFIER_KEYS:
        assert specialized_key in Strategies.items


def test_only_rdb_code_enables_description_scoring() -> None:
    for config_path in (*ENTITY_CONFIG_PATHS, REPOSITORY_ROOT / "tests/config/config.yml"):
        table_specs = load_table_specs(config_path)
        weights = {key: float(table_specs[key].get("description_match_weight") or 0) for key in CLASSIFIER_KEYS}

        assert {key for key, weight in weights.items() if weight > 0} == {"rdb_code"}, config_path
        assert 0.10 <= weights["rdb_code"] <= 0.20


@pytest.mark.parametrize("entity_key", ["rdb_code", "age_type", "colour"])
def test_generated_classifier_sql_matches_tracked_output(tmp_path: Path, entity_key: str) -> None:
    entities = yaml.safe_load((REPOSITORY_ROOT / "config/entities.yml").read_text(encoding="utf-8"))
    generated = render_sql(tmp_path, entity_key, entities[entity_key])
    tracked = (REPOSITORY_ROOT / "schema/generated" / f"{entity_key}.sql").read_text(encoding="utf-8")

    assert generated == tracked


def test_weighted_and_zero_weight_classifier_contracts_differ() -> None:
    entities = yaml.safe_load((REPOSITORY_ROOT / "config/entities.yml").read_text(encoding="utf-8"))
    weighted = (REPOSITORY_ROOT / "schema/generated/rdb_code.sql").read_text(encoding="utf-8")
    plain = (REPOSITORY_ROOT / "schema/generated/age_type.sql").read_text(encoding="utf-8")

    assert "strict_word_similarity(pq.q, s.norm_description)" in weighted
    assert "tbl_rdb_codes_norm_desc_trgm" in weighted
    assert "scored.description_sim >= p_description_threshold" in weighted
    assert "filtered.label_sim + 0.15 * filtered.description_sim" in weighted
    assert "s.norm_label % pq.q" not in weighted

    assert entities["age_type"].get("description_match_weight") is None
    assert "description text" in plain
    assert "strict_word_similarity" not in plain
    assert "_norm_desc_trgm" not in plain
    assert "label_sim double precision" not in plain
    assert "p_label_threshold double precision default 0.30" in plain


def test_reference_entities_are_marked_simple_in_entity_configurations() -> None:
    for config_path in REFERENCE_ENTITY_CONFIG_PATHS:
        entities = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        for entity_key in ("feature_type", "data_type"):
            assert entities[entity_key].get("reconciliation") == "simple", (config_path, entity_key)


def test_reference_entities_are_marked_in_inline_test_table_specs() -> None:
    config = yaml.safe_load((REPOSITORY_ROOT / "tests/config/config.yml").read_text(encoding="utf-8"))
    for entity_key in ("feature_type", "data_type"):
        assert config["table_specs"][entity_key].get("reconciliation") == "simple"


@pytest.mark.parametrize("entity_key", ["feature_type", "data_type"])
def test_marked_reference_entities_render_tracked_sql(tmp_path: Path, entity_key: str) -> None:
    entities = yaml.safe_load((REPOSITORY_ROOT / "config/entities.yml").read_text(encoding="utf-8"))
    generated = render_sql(tmp_path, entity_key, entities[entity_key])
    tracked = (REPOSITORY_ROOT / "schema/generated" / f"{entity_key}.sql").read_text(encoding="utf-8")

    assert generated == tracked
    assert "as description" in generated
    assert "as norm_description" in generated
    assert "description text" in generated
    assert "label_sim" not in generated
    assert "strict_word_similarity" not in generated
    assert "_norm_desc_trgm" not in generated
