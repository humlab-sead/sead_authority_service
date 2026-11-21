"""Shared reconciliation strategy for entities marked `reconciliation: simple`.

`initialize_classifiers()` is the only registration entry point. It validates the marked
`table_specs` entries, then registers one strategy per marked key. Specification details come
from that entry, so no per-entity Python class or resource YAML is needed.

Configuration must be loaded before classifiers exist. Application startup and the router's
configuration dependency call the entry point; tooling that builds strategies directly must
call it too, otherwise the registry stays empty for simple classifiers.
"""

from collections import Counter
from typing import Any

from loguru import logger

from src.configuration import ConfigValue
from src.record_identifiers import format_record_uri
from src.utility import (
    build_classifier_specification,
    classifier_view_columns,
    normalize_text,
    set_configured_specification_resolver,
    view_column_source,
)

from .query import BaseRepository
from .strategy import ReconciliationStrategy, Strategies

CANDIDATE_DESCRIPTION_LIMIT = 500


class ClassifierConfigurationError(ValueError):
    """Raised when marked classifier configuration is missing or invalid."""


class ConfiguredClassifierStrategy(ReconciliationStrategy):
    """Reconciles a classifier using its marked table specification and generated SQL."""

    async def suggest_candidates(self, prefix: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return classifier rows whose normalized labels start with the prefix."""
        return await self.get_repository().find_by_prefix(prefix, limit)

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
            "id": format_record_uri(id_base, self.get_id_path(), entity_id),
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


def marked_classifier_keys(table_specs: dict[str, Any] | None = None) -> list[str]:
    """Returns the sorted keys whose table specification declares `reconciliation: simple`."""
    specs: dict[str, Any] = _get_table_specs() if table_specs is None else table_specs
    return sorted(key for key, table_spec in specs.items() if isinstance(table_spec, dict) and table_spec.get("reconciliation") == "simple")


def validate_classifier_configuration() -> list[str]:
    """Checks every marked simple classifier and the reconciliation thresholds.

    Returns the validated keys. Validation is unconditional: a marked spec that the system
    would serve must satisfy the simple-classifier contract whether or not record selection
    currently enables it.
    """
    table_specs: dict[str, Any] = _get_table_specs()
    if not table_specs:
        raise ClassifierConfigurationError("Missing 'table_specs' configuration for classifier reconciliation")

    keys: list[str] = marked_classifier_keys(table_specs)
    for key in keys:
        table_spec: dict[str, Any] = table_specs[key]
        _validate_text_column(key, table_spec, "label_column")
        _validate_text_column(key, table_spec, "id_column")
        if table_spec.get("description_column") is not None:
            _validate_text_column(key, table_spec, "description_column")
        _reject_openrefine_properties(key, table_spec)
        _reject_weight_without_description(key, table_spec)

        allowed_columns: set[str] = classifier_view_columns(table_spec)
        for details_column in table_spec.get("details_columns") or []:
            source: str | None = view_column_source(details_column)
            if source not in allowed_columns:
                raise ClassifierConfigurationError(
                    f"Classifier '{key}' details column '{details_column}' is not exposed by its generated view"
                )

    _validate_threshold("label_threshold")
    _validate_threshold("description_threshold")

    logger.info(f"Validated configured classifier configuration for: {', '.join(keys)}")
    return keys


def _reject_openrefine_properties(key: str, table_spec: dict[str, Any]) -> None:
    """Rejects OpenRefine property mappings, which the simple contract does not support."""
    if table_spec.get("properties"):
        raise ClassifierConfigurationError(f"Classifier '{key}' must not declare 'properties'; simple types publish no properties")
    if table_spec.get("property_settings"):
        raise ClassifierConfigurationError(
            f"Classifier '{key}' must not declare 'property_settings'; simple types publish no property settings"
        )


def _reject_weight_without_description(key: str, table_spec: dict[str, Any]) -> None:
    """Rejects description scoring without a description column to score."""
    weight: Any = table_spec.get("description_match_weight")
    if weight is None:
        return
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        raise ClassifierConfigurationError(f"Classifier '{key}' must declare a numeric 'description_match_weight'")
    if float(weight) > 0 and table_spec.get("description_column") is None:
        raise ClassifierConfigurationError(f"Classifier '{key}' declares 'description_match_weight' above 0 without a 'description_column'")


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


def initialize_classifiers() -> list[str]:
    """Validates the simple-classifier configuration, then registers one strategy per marked spec.

    Returns the registered keys. Registration is derived entirely from configuration, so
    calling this again simply replaces the same entries.
    """
    keys: list[str] = validate_classifier_configuration()
    for key in keys:
        strategy_cls = type(
            f"{key.title().replace('_', '')}ReconciliationStrategy",
            (ConfiguredClassifierStrategy,),
            {"__module__": __name__},
        )
        Strategies.register(key=key, repository_cls=BaseRepository, support="supported")(strategy_cls)
    return keys
