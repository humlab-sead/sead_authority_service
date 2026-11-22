"""Bounded, read-only record selection for configured simple classifiers.

Any entity marked `reconciliation: simple` in `table_specs` can be enabled through
`options:record_selection:types`. Discovery, lists, details, and interactive search read the
generated `authority.<key>` objects and derive their columns from the same table spec, so no
per-type code is needed. Nothing in this module writes to the target database or to SIMS state.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from loguru import logger

from src.configuration import ConfigValue
from src.record_identifiers import format_record_uri, parse_record_uri, valid_id_base, within_postgres_integer
from src.strategies.configured_classifier import simple_classifier_keys
from src.strategies.query import BaseRepository
from src.strategies.strategy import Strategies

DEFAULT_BROWSE_MAX_ROWS = 500
DEFAULT_BROWSE_MAX_BYTES = 1_048_576
DEFAULT_INTERACTIVE_SEARCH_MAX_RESULTS = 50
MAX_INTERACTIVE_SEARCH_RESULTS = 500

RECORD_SELECTION_VERSION = 1
RECORD_SELECTION_TYPES_PATH = "/records/types"

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class RecordSelectionConfigurationError(ValueError):
    """Raised when record-selection configuration is missing or invalid."""


class RecordSelectionError(ValueError):
    """A request-time record-selection error that maps to a JSON error envelope."""

    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class CapabilityFlags:
    """Independent capability switches for one selectable type."""

    search: bool = False
    identifier_search: bool = False
    browse: bool = False
    details: bool = False
    export_verification: bool = False

    @property
    def any_enabled(self) -> bool:
        return self.search or self.identifier_search or self.browse or self.details or self.export_verification


@dataclass(frozen=True)
class RecordSelectionPolicy:
    """Limits and per-type capability switches for record selection."""

    browse_max_rows: int
    browse_max_bytes: int
    interactive_search_max_results: int
    types: dict[str, CapabilityFlags]

    def flags_for(self, entity_type: str) -> CapabilityFlags:
        """Return the capability flags for a selectable type, or raise ``unsupported_type``."""
        flags: CapabilityFlags | None = self.types.get(entity_type)
        if flags is None:
            raise RecordSelectionError("unsupported_type", f"Unsupported record type '{entity_type}'.")
        return flags


@dataclass(frozen=True)
class RecordProjection:
    """Read-only SQL projection shared by list and exact-ID lookups for one type."""

    entity_type: str
    table: str
    id_column: str
    label_column: str
    description_column: str | None = None
    membership_clause: str = ""


_FLAG_FIELDS: dict[str, str] = {
    "search": "search_supported",
    "identifier_search": "identifier_search_supported",
    "browse": "browse_supported",
    "details": "details_supported",
    "export_verification": "export_verification_supported",
}


def _positive_int(value: Any, default: int, name: str) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RecordSelectionConfigurationError(f"options:record_selection:{name} must be a positive integer")
    return value


def _flags_from_entry(entry: Any) -> CapabilityFlags:
    if not isinstance(entry, dict):
        return CapabilityFlags()
    return CapabilityFlags(**{attribute: entry.get(field) is True for attribute, field in _FLAG_FIELDS.items()})


def load_record_selection_policy() -> RecordSelectionPolicy:
    """Build the selection policy from ``options:record_selection``.

    Missing settings and missing switches mean disabled. Configured limits are
    validated as positive integers, and the interactive cap is kept inside the
    existing 500-result query-model maximum.

    Only selectable types listed under ``types`` appear in the policy, so an
    unconfigured type is reported as ``unsupported_type`` and stays out of
    discovery, while a configured type whose switches are all off is reported as
    ``unsupported_capability``.
    """
    block: Any = ConfigValue("options:record_selection").resolve()
    block = block if isinstance(block, dict) else {}

    browse_max_rows: int = _positive_int(block.get("browse_max_rows"), DEFAULT_BROWSE_MAX_ROWS, "browse_max_rows")
    browse_max_bytes: int = _positive_int(block.get("browse_max_bytes"), DEFAULT_BROWSE_MAX_BYTES, "browse_max_bytes")
    interactive_max: int = _positive_int(
        block.get("interactive_search_max_results"),
        DEFAULT_INTERACTIVE_SEARCH_MAX_RESULTS,
        "interactive_search_max_results",
    )
    if interactive_max > MAX_INTERACTIVE_SEARCH_RESULTS:
        raise RecordSelectionConfigurationError(
            f"options:record_selection:interactive_search_max_results must be at most {MAX_INTERACTIVE_SEARCH_RESULTS}"
        )

    configured_types: Any = block.get("types")
    configured_types = configured_types if isinstance(configured_types, dict) else {}

    selectable: tuple[str, ...] = selectable_types()
    types: dict[str, CapabilityFlags] = {}
    for entity_type, entry in configured_types.items():
        flags: CapabilityFlags = _flags_from_entry(entry)
        if entity_type not in selectable:
            if flags.any_enabled:
                raise RecordSelectionConfigurationError(f"options:record_selection:types enables unsupported type '{entity_type}'")
            continue
        types[entity_type] = flags

    return RecordSelectionPolicy(
        browse_max_rows=browse_max_rows,
        browse_max_bytes=browse_max_bytes,
        interactive_search_max_results=interactive_max,
        types=types,
    )


def validate_record_selection_configuration() -> None:
    """Validate enabled record-selection types and the identifier base during startup."""
    policy: RecordSelectionPolicy = load_record_selection_policy()
    enabled_types: list[str] = [entity_type for entity_type, flags in policy.types.items() if flags.any_enabled]
    if not enabled_types:
        return

    id_base: Any = ConfigValue("options:id_base").resolve()
    if not valid_id_base(id_base):
        raise RecordSelectionConfigurationError("The options:id_base setting is missing or invalid for an enabled record selection type.")

    for entity_type in enabled_types:
        if Strategies.items.get(entity_type) is None:
            raise RecordSelectionConfigurationError(f"Record selection type '{entity_type}' is not registered.")
        build_projection(entity_type)

    logger.info(f"Validated record selection configuration for: {', '.join(enabled_types)}")


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.match(value):
        raise RecordSelectionConfigurationError(f"Invalid SQL identifier for {label}: {value!r}")
    return value


def selectable_types() -> tuple[str, ...]:
    """Return the marked simple classifier keys that record selection can serve.

    Lookups are registered for reconciliation but are not selectable records.
    """
    return tuple(simple_classifier_keys())


def build_projection(entity_type: str) -> RecordProjection:
    """Return the read-only projection for a selectable simple classifier.

    The projection reads the generated ``authority.<key>`` view, so a spec's
    ``where_clause`` and ``joins`` are already applied there.
    """
    if entity_type not in selectable_types():
        raise RecordSelectionError("unsupported_type", f"Unsupported record type '{entity_type}'.")

    table_spec: Any = ConfigValue(f"table_specs.{entity_type}").resolve()
    if not isinstance(table_spec, dict):
        raise RecordSelectionError("unsupported_type", f"Unsupported record type '{entity_type}'.")

    return RecordProjection(
        entity_type=entity_type,
        table=f"authority.{entity_type}",
        id_column=_identifier(table_spec.get("id_column"), f"{entity_type} id_column"),
        label_column="label",
        description_column="description" if table_spec.get("description_column") else None,
    )


def _select_columns(projection: RecordProjection) -> str:
    columns: list[str] = [f"{projection.id_column} as target_id", f"{projection.label_column} as name"]
    if projection.description_column:
        columns.append(f"{projection.description_column} as description")
    return ", ".join(columns)


def build_list_sql(projection: RecordProjection) -> str:
    """Build the complete-list query for a projection."""
    where: str = f" where {projection.membership_clause}" if projection.membership_clause else ""
    return (
        f"select {_select_columns(projection)} from {projection.table}{where} "
        f"order by {projection.label_column}, {projection.id_column} limit %(limit)s"
    )


def build_lookup_sql(projection: RecordProjection) -> str:
    """Build the exact-ID query for a projection."""
    conditions: list[str] = [f"{projection.id_column} = %(target_id)s"]
    if projection.membership_clause:
        conditions.append(projection.membership_clause)
    return f"select {_select_columns(projection)} from {projection.table} where {' and '.join(conditions)}"


def configured_id_base() -> str:
    """Return a validated ``options:id_base`` or raise a configuration error."""
    id_base: Any = ConfigValue("options:id_base").resolve()
    if not valid_id_base(id_base):
        raise RecordSelectionConfigurationError("The options:id_base setting is missing or invalid.")
    return str(id_base)


def resolve_id_path(entity_type: str) -> str:
    """Return the URI path segment for a record type.

    Constructing a strategy can read a resource specification, so callers that
    format many records for one type should call this once and pass the result to
    ``record_payload``.
    """
    strategy_cls = Strategies.items.get(entity_type)
    if strategy_cls is not None:
        path: str = strategy_cls().get_id_path()
        if isinstance(path, str) and path and path != "unknown":
            return path
    return entity_type


def _repository_for(entity_type: str) -> BaseRepository:
    strategy_cls = Strategies.items.get(entity_type)
    if strategy_cls is None:
        raise RecordSelectionError("unsupported_type", f"Unsupported record type '{entity_type}'.")
    return strategy_cls().get_repository()


async def fetch_browse_rows(entity_type: str, limit: int) -> list[dict[str, Any]]:
    """Read up to ``limit`` projected rows for a type without writing anything."""
    projection: RecordProjection = build_projection(entity_type)
    repository: BaseRepository = _repository_for(entity_type)
    return await repository.fetch_all(build_list_sql(projection), {"limit": limit})


async def fetch_record_row(entity_type: str, target_id: int) -> dict[str, Any] | None:
    """Read one projected row by ID, treating out-of-range IDs as absent."""
    if not within_postgres_integer(target_id):
        return None
    projection: RecordProjection = build_projection(entity_type)
    repository: BaseRepository = _repository_for(entity_type)
    return await repository.fetch_one(build_lookup_sql(projection), {"target_id": target_id})


def encode_json(payload: Any) -> bytes:
    """Serialize a payload to the exact UTF-8 bytes returned to a caller."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def record_payload(entity_type: str, row: Mapping[str, Any], id_base: str, id_path: str) -> dict[str, Any]:
    """Convert one projected row to the record shape shared by list and details.

    ``id_path`` comes from ``resolve_id_path`` so a caller formatting many rows
    resolves it once per request.
    """
    target_id: int = int(row["target_id"])
    record: dict[str, Any] = {
        "id": format_record_uri(id_base, id_path, target_id),
        "target_id": target_id,
        "type": entity_type,
        "name": "" if row.get("name") is None else str(row["name"]),
        "fields": {},
    }
    description: Any = row.get("description")
    if description is not None:
        record["description"] = str(description)
    return record


async def collect_browse_list(entity_type: str, policy: RecordSelectionPolicy) -> bytes:
    """Return a complete list as bytes, or raise ``too_large_to_browse``.

    The query asks for one row beyond the row limit so an oversized list is detected
    before serialization. A returned list is serialized once and measured against the
    byte limit, and those same bytes are returned to the caller.
    """
    rows: list[dict[str, Any]] = await fetch_browse_rows(entity_type, policy.browse_max_rows + 1)
    if len(rows) > policy.browse_max_rows:
        raise RecordSelectionError("too_large_to_browse", "The list exceeds the configured row limit.", 409)

    id_base: str = configured_id_base()
    id_path: str = resolve_id_path(entity_type)
    items: list[dict[str, Any]] = [record_payload(entity_type, row, id_base, id_path) for row in rows]
    body: bytes = encode_json({"items": items, "completeness": "complete"})
    if len(body) > policy.browse_max_bytes:
        raise RecordSelectionError("too_large_to_browse", "The list exceeds the configured byte limit.", 409)
    return body


# ---------- Interactive search ----------


def validate_interactive_query(raw_queries: Any, policy: RecordSelectionPolicy) -> tuple[str, str, int, str]:
    """Validate a marked interactive request and return its query ID, type, limit, and text."""
    if not isinstance(raw_queries, dict) or len(raw_queries) != 1:
        raise RecordSelectionError("invalid_request", "Interactive record selection requires exactly one query.")
    query_id, query_data = next(iter(raw_queries.items()))
    if not isinstance(query_data, dict):
        raise RecordSelectionError("invalid_request", "Invalid query payload.")

    entity_type: Any = query_data.get("type")
    if not isinstance(entity_type, str) or not entity_type.strip():
        raise RecordSelectionError("invalid_request", "Interactive record selection requires an explicit type.")
    flags: CapabilityFlags = policy.flags_for(entity_type)
    if not flags.search:
        raise RecordSelectionError("unsupported_capability", f"Interactive search is not enabled for '{entity_type}'.")

    text: Any = query_data.get("query")
    if not isinstance(text, str) or not text.strip():
        raise RecordSelectionError("invalid_request", "Interactive record selection requires non-blank query text.")

    limit: Any = query_data.get("limit")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise RecordSelectionError("invalid_request", "Interactive record selection requires an explicit positive integer limit.")
    if limit > policy.interactive_search_max_results:
        raise RecordSelectionError(
            "search_limit_exceeded",
            f"The requested limit exceeds the interactive search cap of {policy.interactive_search_max_results}.",
        )

    if query_data.get("properties"):
        raise RecordSelectionError("invalid_request", "Interactive record selection does not support property hints for this type.")

    return str(query_id), entity_type, limit, text


async def search_interactive(entity_type: str, query_text: str, limit: int) -> dict[str, Any]:
    """Run a bounded search through the registered classifier strategy for one type."""
    strategy_cls = Strategies.items.get(entity_type)
    if strategy_cls is None or entity_type not in selectable_types():
        raise RecordSelectionError("unsupported_type", f"Unsupported record type '{entity_type}'.")

    strategy = strategy_cls()
    rows: list[dict[str, Any]] = await strategy.find_candidates(query=query_text, properties={}, limit=limit)
    candidates: list[dict[str, Any]] = strategy.as_candidates(rows, query_text)

    id_base: str = configured_id_base()
    valid: list[dict[str, Any]] = []
    for candidate in candidates[:limit]:
        target_id: int | None = parse_record_uri(str(candidate.get("id", "")), entity_type, id_base)
        if target_id is None or not within_postgres_integer(target_id):
            logger.warning("Dropping interactive candidate with a URI that does not match a record: {}", candidate.get("id"))
            continue
        valid.append(candidate)
    return {"result": valid}


# ---------- Discovery ----------


SORT_FIELDS: tuple[str, ...] = ("name", "target_id")


def _display_fields(projection: RecordProjection) -> list[dict[str, Any]]:
    """Return the ordered display fields a projection exposes."""
    fields: list[dict[str, Any]] = [
        {"name": "name", "source": "record", "label": "Name", "value_type": "string", "display": True},
        {"name": "target_id", "source": "record", "label": "ID", "value_type": "integer", "display": True},
    ]
    if projection.description_column:
        fields.append({"name": "description", "source": "record", "label": "Description", "value_type": "string", "display": True})
    return fields


def _text_filter_fields(projection: RecordProjection) -> list[str]:
    fields: list[str] = ["name"]
    if projection.description_column:
        fields.append("description")
    return fields


def _field_filters(projection: RecordProjection) -> list[dict[str, str]]:
    filters: list[dict[str, str]] = [{"field": "name", "operator": "contains_ci"}]
    if projection.description_column:
        filters.append({"field": "description", "operator": "contains_ci"})
    filters.append({"field": "target_id", "operator": "equals"})
    return filters


def discovery_types() -> list[dict[str, Any]]:
    """Return per-type capability descriptors for the configured types without querying target data."""
    policy: RecordSelectionPolicy = load_record_selection_policy()
    id_base: Any = ConfigValue("options:id_base").resolve()
    id_base_value: str | None = id_base if isinstance(id_base, str) and id_base else None

    entries: list[dict[str, Any]] = []
    for entity_type, flags in policy.types.items():
        projection: RecordProjection = build_projection(entity_type)
        entries.append(
            {
                "type": entity_type,
                "search_supported": flags.search,
                "identifier_search_supported": flags.identifier_search,
                "browse_supported": flags.browse,
                "details_supported": flags.details,
                "export_verification_supported": flags.export_verification,
                "id_base": id_base_value,
                "id_path": resolve_id_path(entity_type),
                "browse_max_rows": policy.browse_max_rows if flags.browse else None,
                "browse_max_bytes": policy.browse_max_bytes if flags.browse else None,
                "interactive_search_max_results": policy.interactive_search_max_results if flags.search else None,
                "display_fields": _display_fields(projection),
                "text_filter_fields": _text_filter_fields(projection),
                "sort_fields": list(SORT_FIELDS),
                "field_filters": _field_filters(projection),
            }
        )
    return entries


def record_selection_manifest() -> dict[str, Any]:
    """Return the manifest descriptor that points a client at the discovery route."""
    return {"version": RECORD_SELECTION_VERSION, "types_path": RECORD_SELECTION_TYPES_PATH}
