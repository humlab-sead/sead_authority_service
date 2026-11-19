"""Bounded, read-only record selection for the reconciliation pilot types.

Phase 1 covers two pilot types, ``feature_type`` and ``country``. Each type has an
independent set of capability switches and two small read-only projections:
``feature_type`` reads the generated classifier view derived from its marked table
spec, and ``country`` reads the country subset of ``authority.location``. Nothing in
this module writes to the target database or to SIMS state.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from loguru import logger

from src.configuration import ConfigValue
from src.record_identifiers import format_record_uri, parse_record_uri, valid_id_base, within_postgres_integer
from src.strategies.query import BaseRepository
from src.strategies.strategy import Strategies

DEFAULT_BROWSE_MAX_ROWS = 500
DEFAULT_BROWSE_MAX_BYTES = 1_048_576
DEFAULT_INTERACTIVE_SEARCH_MAX_RESULTS = 50
MAX_INTERACTIVE_SEARCH_RESULTS = 500

RECORD_SELECTION_VERSION = 1
RECORD_SELECTION_TYPES_PATH = "/records/types"

PILOT_TYPES: tuple[str, ...] = ("feature_type", "country")
COUNTRY_LOCATION_TYPE_IDS: tuple[int, ...] = (1,)
COUNTRY_FUZZY_SQL = "select * from authority.fuzzy_location(%(q)s::text, %(n)s::int, %(location_type_ids)s::integer[])"

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
    """Independent capability switches for one pilot type."""

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
        """Return the capability flags for a pilot type, or raise ``unsupported_type``."""
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

    types: dict[str, CapabilityFlags] = {entity_type: _flags_from_entry(configured_types.get(entity_type)) for entity_type in PILOT_TYPES}
    for entity_type, entry in configured_types.items():
        if entity_type not in PILOT_TYPES and _flags_from_entry(entry).any_enabled:
            raise RecordSelectionConfigurationError(f"options:record_selection:types enables unsupported type '{entity_type}'")

    return RecordSelectionPolicy(
        browse_max_rows=browse_max_rows,
        browse_max_bytes=browse_max_bytes,
        interactive_search_max_results=interactive_max,
        types=types,
    )


def validate_record_selection_configuration() -> None:
    """Validate enabled pilot types and the identifier base during startup."""
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


def _feature_type_projection() -> RecordProjection:
    table_spec: Any = ConfigValue("table_specs.feature_type").resolve()
    if not isinstance(table_spec, dict):
        raise RecordSelectionConfigurationError("Missing 'table_specs.feature_type' configuration for record selection.")
    return RecordProjection(
        entity_type="feature_type",
        table="authority.feature_type",
        id_column=_identifier(table_spec.get("id_column"), "feature_type id_column"),
        label_column="label",
        description_column="description" if table_spec.get("description_column") else None,
    )


def _country_projection() -> RecordProjection:
    return RecordProjection(
        entity_type="country",
        table="authority.location",
        id_column="location_id",
        label_column="label",
        description_column=None,
        membership_clause="location_type_id = 1",
    )


_PROJECTION_BUILDERS = {
    "feature_type": _feature_type_projection,
    "country": _country_projection,
}


def build_projection(entity_type: str) -> RecordProjection:
    """Return the read-only projection for a pilot type."""
    builder = _PROJECTION_BUILDERS.get(entity_type)
    if builder is None:
        raise RecordSelectionError("unsupported_type", f"Unsupported record type '{entity_type}'.")
    return builder()


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


def _id_path(entity_type: str) -> str:
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


def record_payload(entity_type: str, row: Mapping[str, Any], id_base: str) -> dict[str, Any]:
    """Convert one projected row to the record shape shared by list and details."""
    target_id: int = int(row["target_id"])
    record: dict[str, Any] = {
        "id": format_record_uri(id_base, _id_path(entity_type), target_id),
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
    items: list[dict[str, Any]] = [record_payload(entity_type, row, id_base) for row in rows]
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


async def _feature_type_candidates(query_text: str, limit: int) -> list[dict[str, Any]]:
    strategy_cls = Strategies.items.get("feature_type")
    if strategy_cls is None:
        raise RecordSelectionError("unsupported_type", "Unsupported record type 'feature_type'.")
    strategy = strategy_cls()
    rows: list[dict[str, Any]] = await strategy.find_candidates(query=query_text, properties={}, limit=limit)
    return strategy.as_candidates(rows, query_text)


async def _country_candidates(query_text: str, limit: int) -> list[dict[str, Any]]:
    strategy_cls = Strategies.items.get("country")
    if strategy_cls is None:
        raise RecordSelectionError("unsupported_type", "Unsupported record type 'country'.")
    strategy = strategy_cls()
    rows: list[dict[str, Any]] = await strategy.get_repository().fetch_all(
        COUNTRY_FUZZY_SQL,
        {"q": query_text, "n": limit, "location_type_ids": list(COUNTRY_LOCATION_TYPE_IDS)},
    )
    return strategy.as_candidates(rows, query_text)


async def search_interactive(entity_type: str, query_text: str, limit: int) -> dict[str, Any]:
    """Run a bounded pilot search and return an OpenRefine result keyed by the caller."""
    if entity_type == "country":
        candidates: list[dict[str, Any]] = await _country_candidates(query_text, limit)
    elif entity_type == "feature_type":
        candidates = await _feature_type_candidates(query_text, limit)
    else:
        raise RecordSelectionError("unsupported_type", f"Unsupported record type '{entity_type}'.")

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


@dataclass(frozen=True)
class DisplayField:
    """One ordered display field advertised for a pilot type."""

    name: str
    source: str
    label: str
    value_type: str
    display: bool


_DISPLAY_FIELDS: dict[str, tuple[DisplayField, ...]] = {
    "feature_type": (
        DisplayField("name", "record", "Name", "string", True),
        DisplayField("target_id", "record", "ID", "integer", True),
        DisplayField("description", "record", "Description", "string", True),
    ),
    "country": (
        DisplayField("name", "record", "Name", "string", True),
        DisplayField("target_id", "record", "ID", "integer", True),
    ),
}

SORT_FIELDS: tuple[str, ...] = ("name", "target_id")


def _display_fields(entity_type: str) -> list[dict[str, Any]]:
    return [
        {
            "name": field.name,
            "source": field.source,
            "label": field.label,
            "value_type": field.value_type,
            "display": field.display,
        }
        for field in _DISPLAY_FIELDS[entity_type]
    ]


def _text_filter_fields(entity_type: str) -> list[str]:
    fields = ["name"]
    if entity_type == "feature_type":
        fields.append("description")
    return fields


def _field_filters(entity_type: str) -> list[dict[str, str]]:
    filters: list[dict[str, str]] = [{"field": "name", "operator": "contains_ci"}]
    if entity_type == "feature_type":
        filters.append({"field": "description", "operator": "contains_ci"})
    filters.append({"field": "target_id", "operator": "equals"})
    return filters


def discovery_types() -> list[dict[str, Any]]:
    """Return per-type capability descriptors without querying target data."""
    policy: RecordSelectionPolicy = load_record_selection_policy()
    id_base: Any = ConfigValue("options:id_base").resolve()
    id_base_value: str | None = id_base if isinstance(id_base, str) and id_base else None

    entries: list[dict[str, Any]] = []
    for entity_type in PILOT_TYPES:
        flags: CapabilityFlags = policy.types[entity_type]
        entries.append(
            {
                "type": entity_type,
                "search_supported": flags.search,
                "identifier_search_supported": flags.identifier_search,
                "browse_supported": flags.browse,
                "details_supported": flags.details,
                "export_verification_supported": flags.export_verification,
                "id_base": id_base_value,
                "id_path": _id_path(entity_type),
                "browse_max_rows": policy.browse_max_rows if flags.browse else None,
                "browse_max_bytes": policy.browse_max_bytes if flags.browse else None,
                "interactive_search_max_results": policy.interactive_search_max_results if flags.search else None,
                "display_fields": _display_fields(entity_type),
                "text_filter_fields": _text_filter_fields(entity_type),
                "sort_fields": list(SORT_FIELDS),
                "field_filters": _field_filters(entity_type),
            }
        )
    return entries


def record_selection_manifest() -> dict[str, Any]:
    """Return the manifest descriptor that points a client at the discovery route."""
    return {"version": RECORD_SELECTION_VERSION, "types_path": RECORD_SELECTION_TYPES_PATH}
