"""Shared reconciliation strategy for classifier entities marked `reconciliation: simple`.

Registration stays static: `CLASSIFIER_KEYS` names every eligible key and a startup check
verifies the loaded configuration matches it in both directions. Specification details come
from the marked `table_specs` entry, so no per-entity Python class or resource YAML is needed.
"""

from collections import Counter
from typing import Any

from loguru import logger

from src.configuration import ConfigValue
from src.utility import (
    build_classifier_specification,
    classifier_view_columns,
    normalize_text,
    set_configured_specification_resolver,
    view_column_source,
)

from .query import BaseRepository
from .strategy import ReconciliationStrategy, Strategies

CLASSIFIER_KEYS: tuple[str, ...] = (
    "abundance_element",
    "activity_type",
    "age_type",
    "alt_ref_type",
    "colour",
    "contact_type",
    "data_type",
    "data_type_group",
    "dataset_submission_type",
    "dating_uncertainty",
    "ecocode_definition",
    "ecocode_group",
    "feature_type",
    "horizon",
    "identification_level",
    "language",
    "location_type",
    "method_group",
    "project_stage",
    "project_type",
    "property_type",
    "property_type_group",
    "rdb_code",
    "record_type",
    "relative_age_type",
    "sample_description_type",
    "sample_group_description_type",
    "sample_location_type",
    "sample_type",
    "season",
    "season_type",
    "site_type",
    "site_type_group",
    "species_association_type",
    "submission_state",
    "submission_task_type",
    "taxa_tree_author",
    "taxa_tree_family",
    "taxa_tree_genus",
    "taxa_tree_order",
    "unit",
    "value_class",
    "value_qualifier",
    "value_type",
    "value_type_item",
)

CANDIDATE_DESCRIPTION_LIMIT = 500


class ClassifierConfigurationError(ValueError):
    """Raised when marked classifier configuration is missing or invalid."""


class ConfiguredClassifierStrategy(ReconciliationStrategy):
    """Reconciles a classifier using its marked table specification and generated SQL."""

    def as_candidate(self, entity_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Converts one row to a candidate using label evidence for the match flag."""
        return self._as_label_evidence_candidate(entity_data, normalize_text(query))

    def as_candidates(self, entity_data: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        """Converts one query result, suppressing matches shared by duplicate normalized labels."""
        normalized_query: str = normalize_text(query)
        label_field: str = self.get_label_field()
        normalized_labels: list[str] = [normalize_text(str(row.get(label_field, ""))) for row in entity_data]
        label_counts: Counter[str] = Counter(normalized_labels)

        candidates: list[dict[str, Any]] = []
        for row, normalized_label in zip(entity_data, normalized_labels):
            candidate: dict[str, Any] = self._as_label_evidence_candidate(row, normalized_query)
            if label_counts[normalized_label] > 1:
                candidate["match"] = False
            candidates.append(candidate)
        return candidates

    def _as_label_evidence_candidate(self, entity_data: dict[str, Any], normalized_query: str) -> dict[str, Any]:
        id_base: str = ConfigValue("options:id_base").resolve() or ""
        auto_accept_threshold: float = ConfigValue("options:auto_accept_threshold").resolve() or 0.85

        entity_id: str = entity_data[self.get_entity_id_field()]
        label: str = entity_data[self.get_label_field()]
        name_sim: float = float(entity_data.get("name_sim", 0))
        label_sim_value: Any = entity_data.get("label_sim")
        label_sim: float = float(label_sim_value) if label_sim_value is not None else name_sim
        score_percent: float = min(100.0, round(name_sim * 100, 2))
        is_exact_label: bool = normalize_text(str(label)) == normalized_query
        is_match: bool = bool(is_exact_label or label_sim >= auto_accept_threshold)

        candidate: dict[str, Any] = {
            "id": f"{id_base}{self.get_id_path()}/{entity_id}",
            "name": label,
            "score": score_percent,
            "match": is_match,
            "type": [{"id": self.get_id_path(), "name": label}],
        }

        description: Any = entity_data.get("description")
        if description is not None:
            candidate["description"] = str(description)[:CANDIDATE_DESCRIPTION_LIMIT]

        logger.debug(
            f"Candidate: query='{normalized_query}' -> name='{label}' | "
            f"score={score_percent}% | label_sim={label_sim:.3f} | match={is_match} | id={entity_id}"
        )
        return candidate


def _get_table_specs() -> dict[str, Any]:
    resolved: Any = ConfigValue("table_specs").resolve()
    return resolved if isinstance(resolved, dict) else {}


def validate_classifier_configuration() -> None:
    """Checks marked classifier entries and reconciliation thresholds after configuration loads."""
    table_specs: dict[str, Any] = _get_table_specs()
    if not table_specs:
        raise ClassifierConfigurationError("Missing 'table_specs' configuration for classifier reconciliation")

    for key in CLASSIFIER_KEYS:
        table_spec: Any = table_specs.get(key)
        if not isinstance(table_spec, dict):
            raise ClassifierConfigurationError(f"Classifier '{key}' is not configured in 'table_specs'")
        if table_spec.get("reconciliation") != "simple":
            raise ClassifierConfigurationError(f"Classifier '{key}' must declare 'reconciliation: simple'")
        _validate_text_column(key, table_spec, "label_column")
        _validate_text_column(key, table_spec, "id_column")
        if table_spec.get("description_column") is not None:
            _validate_text_column(key, table_spec, "description_column")

        allowed_columns: set[str] = classifier_view_columns(table_spec)
        for details_column in table_spec.get("details_columns") or []:
            source: str | None = view_column_source(details_column)
            if source not in allowed_columns:
                raise ClassifierConfigurationError(
                    f"Classifier '{key}' details column '{details_column}' is not exposed by its generated view"
                )

    marked_keys: set[str] = {
        key for key, table_spec in table_specs.items() if isinstance(table_spec, dict) and table_spec.get("reconciliation") == "simple"
    }
    unexpected_keys: list[str] = sorted(marked_keys.difference(CLASSIFIER_KEYS))
    if unexpected_keys:
        raise ClassifierConfigurationError("Marked classifiers are not declared in CLASSIFIER_KEYS: " + ", ".join(unexpected_keys))

    _validate_threshold("label_threshold")
    _validate_threshold("description_threshold")

    logger.info(f"Validated configured classifier configuration for: {', '.join(CLASSIFIER_KEYS)}")


def _validate_text_column(key: str, table_spec: dict[str, Any], field: str) -> None:
    value: Any = table_spec.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ClassifierConfigurationError(f"Classifier '{key}' must declare a non-empty text '{field}'")


def _validate_threshold(name: str) -> None:
    value: Any = ConfigValue(f"options:reconciliation:{name}").resolve()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClassifierConfigurationError(f"Reconciliation option 'options:reconciliation:{name}' must be a number")
    if not 0 < float(value) <= 1:
        raise ClassifierConfigurationError(f"Reconciliation option 'options:reconciliation:{name}' must be greater than 0 and at most 1")


def _resolve_configured_specification(key: str) -> dict[str, Any] | None:
    """Builds a classifier specification from the marked table spec, or None when unusable."""
    try:
        resolved_spec = ConfigValue(f"table_specs.{key}").resolve()
    except ValueError:
        return None
    table_spec = resolved_spec if isinstance(resolved_spec, dict) else None
    if table_spec is None:
        return None
    if table_spec.get("reconciliation") != "simple":
        return None
    if not table_spec.get("id_column") or not table_spec.get("label_column"):
        return None
    return build_classifier_specification(key, table_spec)


set_configured_specification_resolver(_resolve_configured_specification)


def _register_configured_classifiers() -> None:
    for key in CLASSIFIER_KEYS:
        strategy_cls = type(
            f"{key.title().replace('_', '')}ReconciliationStrategy",
            (ConfiguredClassifierStrategy,),
            {"__module__": __name__},
        )
        Strategies.register(key=key, repository_cls=BaseRepository, support="supported")(strategy_cls)


_register_configured_classifiers()
