"""Shared reconciliation strategy for entities marked `reconciliation: simple` or `lookup`.

`initialize_classifiers()` is the only registration entry point. It validates the marked
`table_specs` entries, then registers one strategy per marked key. Specification details come
from that entry, so no per-entity Python class or resource YAML is needed.

Configuration must be loaded before classifiers exist. Application startup and the router's
configuration dependency call the entry point; tooling that builds strategies directly must
call it too, otherwise the registry stays empty for configured reconciliation types.
"""

from collections import Counter
from typing import Any

from loguru import logger

from src.configuration import ConfigValue
from src.record_identifiers import format_record_uri
from src.utility import (
    CONTEXT_DESCRIPTION_PREFIX,
    CONTEXT_PROPERTY_ID,
    build_classifier_specification,
    classifier_view_columns,
    context_matches,
    is_marked_for_reconciliation,
    normalize_text,
    reconciliation_marker,
    resolve_scope_context,
    set_configured_specification_resolver,
    view_column_source,
)

from .query import BaseRepository
from .strategy import ReconciliationStrategy, Strategies

CANDIDATE_DESCRIPTION_LIMIT = 500
CANDIDATE_DESCRIPTION_SEPARATOR = " — "


class ClassifierConfigurationError(ValueError):
    """Raised when marked classifier configuration is missing or invalid."""


class ClassifierSchemaError(ValueError):
    """Raised when a fuzzy row does not carry the generated schema's ambiguity flag."""


class ConfiguredClassifierStrategy(ReconciliationStrategy):
    """Reconciles a classifier or lookup using its marked table specification and generated SQL."""

    async def suggest_candidates(self, prefix: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return classifier rows whose normalized labels start with the prefix."""
        return await self.get_repository().find_by_prefix(prefix, limit)

    async def find_interactive_candidates(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Include literal label-substring hits with the strategy's ranked fuzzy results."""
        fuzzy_rows = await self.find_candidates(query=query, properties={}, limit=limit)
        substring_rows = await self.get_repository().find_by_label_substring(query, limit)

        rows_by_id: dict[Any, dict[str, Any]] = {}
        for row in [*fuzzy_rows, *substring_rows]:
            entity_id: Any = row[self.get_entity_id_field()]
            previous: dict[str, Any] | None = rows_by_id.get(entity_id)
            if previous is None or self._interactive_rank(row) > self._interactive_rank(previous):
                rows_by_id[entity_id] = row

        return sorted(rows_by_id.values(), key=self._interactive_rank, reverse=True)[:limit]

    @staticmethod
    def _interactive_rank(row: dict[str, Any]) -> float:
        """Return the candidate score used to combine ranked and substring results."""
        return float(row.get("name_sim", row.get("score", 0)) or 0)

    async def _find_candidates(self, query, properties, limit, proxy) -> list[dict[str, Any]]:
        """Searches the generated fuzzy function, passing optional parent context as a bound value."""
        supplied: dict[str, Any] = properties or {}
        context: str | None = self._supplied_context(supplied)
        rows: list[dict[str, Any]] = []

        alternate_identity_field: str | None = self.specification.get("alternate_identity_field")
        if alternate_identity_field and supplied.get(alternate_identity_field):
            rows.extend(await proxy.fetch_by_alternate_identity(supplied[alternate_identity_field], context=context))

        rows.extend(await proxy.find(query, limit, context=context))
        return rows

    def as_candidate(self, entity_data: dict[str, Any], query: str) -> dict[str, Any]:
        """Converts one row to a candidate using label evidence for the match flag."""
        return self._as_label_evidence_candidate(entity_data, normalize_text(query))

    def as_candidates(
        self, entity_data: list[dict[str, Any]], query: str, properties: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Converts fuzzy rows, suppressing matches whose label is duplicated in the eligible set.

        Each row must carry the generated schema's `label_ambiguous` flag, which covers rows
        the SQL limit omitted. The returned-row label count stays as a second check, because
        Python normalization and PostgreSQL `unaccent` are separate implementations.

        When the request supplies a `context` property, `context_match` is copied from the
        row. Rows found outside the supplied context cannot auto-match, and alternate-identity
        rows outside the supplied context are dropped.
        """
        normalized_query: str = normalize_text(query)
        label_field: str = self.get_label_field()
        normalized_labels: list[str] = [normalize_text(str(row.get(label_field, ""))) for row in entity_data]
        label_counts: Counter[str] = Counter(normalized_labels)
        scoped: bool = bool(self.get_properties_meta())
        supplied_context: str | None = self._supplied_context(properties) if scoped else None

        candidates: list[dict[str, Any]] = []
        for row, normalized_label in zip(entity_data, normalized_labels):
            context_match: bool | None = None
            if supplied_context is not None:
                context_match = self._row_context_match(row, supplied_context)
            label_ambiguous: bool = self._label_ambiguous(row)
            candidate: dict[str, Any] = self._as_label_evidence_candidate(row, normalized_query)
            if context_match is not None:
                candidate["context_match"] = context_match
            if label_ambiguous or label_counts[normalized_label] > 1 or context_match is False:
                candidate["match"] = False
            candidates.append(candidate)
        return candidates

    @staticmethod
    def _supplied_context(properties: dict[str, Any] | None) -> str | None:
        """Returns the normalized context value supplied by the request, or None."""
        value: Any = (properties or {}).get(CONTEXT_PROPERTY_ID)
        if isinstance(value, str) and value.strip():
            return normalize_text(value.strip())
        return None

    @staticmethod
    def _row_context_match(row: dict[str, Any], supplied_context: str) -> bool:
        """Returns whether the row belongs to the supplied context.

        Generated fuzzy rows report `context_match` themselves. Rows that omit the flag
        are compared with the same whole-parent-label rule the generated SQL uses, so a
        row found outside the supplied context is returned as a suggestion that cannot
        auto-match.
        """
        row_context_match: Any = row.get("context_match")
        if isinstance(row_context_match, bool):
            return row_context_match
        row_norm_context: str = str(row.get("norm_context") or normalize_text(str(row.get("context") or "")))
        return context_matches(supplied_context, row_norm_context)

    def _label_ambiguous(self, row: dict[str, Any]) -> bool:
        """Returns the generated schema's ambiguity flag for one fuzzy row.

        The flag is required. A row from a function that still returns the tier-1 columns
        cannot be treated as unambiguous, because the SQL limit may have dropped a row with
        the same normalized label.
        """
        value: Any = row.get("label_ambiguous")
        if not isinstance(value, bool):
            raise ClassifierSchemaError(
                f"Fuzzy row for classifier '{self.key}' is missing the boolean 'label_ambiguous' column "
                f"(got {value!r}); deploy the generated classifier schema before this application version"
            )
        return value

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

        description: str | None = self._compose_description(entity_data)
        if description is not None:
            candidate["description"] = description

        logger.debug(
            f"Candidate: query='{normalized_query}' -> name='{label}' | "
            f"score={score_percent}% | label_sim={label_sim:.3f} | match={is_match} | id={entity_id}"
        )
        return candidate

    @staticmethod
    def _compose_description(entity_data: dict[str, Any]) -> str | None:
        """Builds the candidate description, placing parent context before the entity description."""
        parts: list[str] = []
        context_value: Any = entity_data.get("context")
        if isinstance(context_value, str) and context_value.strip():
            parts.append(f"{CONTEXT_DESCRIPTION_PREFIX}{context_value.strip()}")
        description_value: Any = entity_data.get("description")
        if description_value is not None and str(description_value).strip():
            parts.append(str(description_value))
        if not parts:
            return None
        return CANDIDATE_DESCRIPTION_SEPARATOR.join(parts)[:CANDIDATE_DESCRIPTION_LIMIT]


def _get_table_specs() -> dict[str, Any]:
    resolved: Any = ConfigValue("table_specs").resolve()
    return resolved if isinstance(resolved, dict) else {}


def marked_classifier_keys(table_specs: dict[str, Any] | None = None) -> list[str]:
    """Returns the sorted keys marked with `reconciliation: simple` or `reconciliation: lookup`."""
    specs: dict[str, Any] = _get_table_specs() if table_specs is None else table_specs
    return sorted(key for key, table_spec in specs.items() if is_marked_for_reconciliation(table_spec))


def simple_classifier_keys(table_specs: dict[str, Any] | None = None) -> list[str]:
    """Returns the sorted keys marked with `reconciliation: simple` only."""
    specs: dict[str, Any] = _get_table_specs() if table_specs is None else table_specs
    return sorted(key for key, table_spec in specs.items() if isinstance(table_spec, dict) and table_spec.get("reconciliation") == "simple")


def validate_classifier_configuration() -> list[str]:
    """Checks every marked reconciliation entry and the reconciliation thresholds.

    Returns the validated keys. Validation is unconditional: a marked spec that the system
    would serve must satisfy its marker's contract whether or not record selection
    currently enables it. `simple` entities may opt into description scoring; `lookup`
    entities must not score descriptions. Scoped entries must resolve every declared
    scope column to a configured parent label.
    """
    table_specs: dict[str, Any] = _get_table_specs()
    if not table_specs:
        raise ClassifierConfigurationError("Missing 'table_specs' configuration for classifier reconciliation")

    keys: list[str] = marked_classifier_keys(table_specs)
    for key in keys:
        table_spec: dict[str, Any] = table_specs[key]
        marker: str | None = reconciliation_marker(table_spec)
        _validate_text_column(key, table_spec, "label_column", marker)
        _validate_text_column(key, table_spec, "id_column", marker)
        if table_spec.get("description_column") is not None:
            _validate_text_column(key, table_spec, "description_column", marker)
        _reject_openrefine_properties(key, table_spec)
        _reject_weight_without_description(key, table_spec)
        _reject_lookup_description_weight(key, table_spec)
        _validate_scope_columns(key, table_specs)

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


def _validate_scope_columns(key: str, table_specs: dict[str, Any]) -> None:
    """Rejects scope columns that do not resolve to exactly one configured parent label."""
    try:
        resolve_scope_context(table_specs, key)
    except ValueError as exc:
        raise ClassifierConfigurationError(str(exc)) from exc


def _reject_lookup_description_weight(key: str, table_spec: dict[str, Any]) -> None:
    """Rejects description scoring on lookups, which match on labels only."""
    if table_spec.get("reconciliation") != "lookup":
        return
    weight: Any = table_spec.get("description_match_weight")
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        return
    if float(weight) > 0:
        raise ClassifierConfigurationError(
            f"Lookup '{key}' must not score descriptions; declare 'description_match_weight' as 0 or omit it"
        )


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


def _validate_text_column(key: str, table_spec: dict[str, Any], field: str, marker: str | None = None) -> None:
    value: Any = table_spec.get(field)
    if not isinstance(value, str) or not value.strip():
        role: str = "Lookup" if marker == "lookup" else "Classifier"
        raise ClassifierConfigurationError(f"{role} '{key}' must declare a non-empty text '{field}'")


def _validate_threshold(name: str) -> None:
    value: Any = ConfigValue(f"options:reconciliation:{name}").resolve()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClassifierConfigurationError(f"Reconciliation option 'options:reconciliation:{name}' must be a number")
    if not 0 < float(value) <= 1:
        raise ClassifierConfigurationError(f"Reconciliation option 'options:reconciliation:{name}' must be greater than 0 and at most 1")


def _resolve_configured_specification(key: str) -> dict[str, Any] | None:
    """Builds a specification from the marked table spec, or None when unusable."""
    try:
        resolved_spec = ConfigValue(f"table_specs.{key}").resolve()
    except ValueError:
        return None
    table_spec = resolved_spec if isinstance(resolved_spec, dict) else None
    if table_spec is None:
        return None
    if not is_marked_for_reconciliation(table_spec):
        return None
    if not table_spec.get("id_column") or not table_spec.get("label_column"):
        return None
    return build_classifier_specification(key, table_spec)


set_configured_specification_resolver(_resolve_configured_specification)


def initialize_classifiers() -> list[str]:
    """Validates the marked reconciliation configuration, then registers one strategy per entry.

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
