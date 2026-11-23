"""Generate a reconciliation register from registrations and a target-model snapshot."""

import argparse
from collections import Counter
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from src.configuration import Config, MockConfigProvider, set_config_provider
from src.strategies.configured_classifier import ConfiguredClassifierStrategy, initialize_classifiers
from src.strategies.strategy import Strategies

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET_MODEL = REPOSITORY_ROOT.parent / "sead_shape_shifter/resources/target_models/sead_standard_model.yml"
DEFAULT_DOCUMENT = REPOSITORY_ROOT / "docs/RECONCILIATION_TYPE_INVENTORY.md"
MANUAL_START = "<!-- reconciliation-inventory:manual\n"
MANUAL_END = "\n-->"
GENERATED_START = "<!-- reconciliation-inventory:generated:start -->"
GENERATED_END = "<!-- reconciliation-inventory:generated:end -->"
ROWS_START = "<!-- reconciliation-inventory:rows:start -->"
ROWS_END = "<!-- reconciliation-inventory:rows:end -->"


class InventoryEntry(NamedTuple):
    entity: str
    service_type: str | None
    target_table: str | None
    role: str
    disposition: str
    marker: str | None
    label_column: str | None
    text_columns: tuple[str, ...]
    scope_columns: tuple[str, ...]
    reason: str | None
    planned: str | None


def registered_types(specs: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, str]:
    """Returns actual registrations using the supplied configuration without retaining changes."""
    original_strategies = dict(Strategies.items)
    original_provider = set_config_provider(
        MockConfigProvider(Config(data={"table_specs": specs, "options": {"reconciliation": thresholds}}))
    )
    try:
        for key, strategy in original_strategies.items():
            if issubclass(strategy, ConfiguredClassifierStrategy):
                del Strategies.items[key]
        initialize_classifiers()
        registrations: dict[str, str] = {}
        for key, strategy in sorted(Strategies.items.items()):
            status = getattr(strategy, "support_status", None)
            if status not in {"supported", "excluded"}:
                raise ValueError(f"Registered type {key!r} has invalid support status {status!r}")
            registrations[key] = status
        return registrations
    finally:
        Strategies.items.clear()
        Strategies.items.update(original_strategies)
        set_config_provider(original_provider)


def _section(document: str, start: str, end: str) -> str:
    if document.count(start) != 1 or document.count(end) != 1:
        raise ValueError(f"Expected exactly one {start!r} and {end!r} marker")
    content = document.split(start, 1)[1]
    if end not in content:
        raise ValueError(f"Marker {end!r} must follow {start!r}")
    return content.split(end, 1)[0]


def _table_spec(entity: str, service_type: str | None, table: str | None, specs: dict[str, Any]) -> dict[str, Any]:
    for key in (service_type, entity):
        spec = specs.get(key) if key else None
        if isinstance(spec, dict) and (not table or spec.get("table_name") == table):
            return spec
    matches = [spec for spec in specs.values() if isinstance(spec, dict) and table and spec.get("table_name") == table]
    return matches[0] if len(matches) == 1 else {}


def _scope_columns(entity: str, spec: dict[str, Any]) -> tuple[str, ...]:
    columns = spec.get("scope_columns") or []
    if not isinstance(columns, list) or not all(isinstance(column, str) and column for column in columns):
        raise ValueError(f"Invalid scope columns for {entity!r}")
    return tuple(columns)


def _service_type(
    entity: str, table: str | None, aliases: dict[str, str], registrations: dict[str, str], specs: dict[str, Any]
) -> str | None:
    if entity in aliases:
        service_type = aliases[entity]
        if service_type not in registrations:
            raise ValueError(f"Alias for {entity!r} refers to unregistered type {service_type!r}")
        return service_type
    if entity in registrations:
        return entity
    matches = [key for key in registrations if table and isinstance(specs.get(key), dict) and specs[key].get("table_name") == table]
    if len(matches) > 1:
        raise ValueError(f"Entity {entity!r} has multiple registered types for table {table!r}: {matches}")
    return matches[0] if matches else None


def build_inventory(
    model: dict[str, Any], specs: dict[str, Any], registrations: dict[str, str], notes: dict[str, Any]
) -> list[InventoryEntry]:
    """Combines a model snapshot with declared registrations and maintained explanations."""
    entities: dict[str, Any] = model["entities"]
    aliases: dict[str, str] = notes.get("aliases", {})
    reasons: dict[str, str] = notes.get("reasons", {})
    planned: dict[str, str] = notes.get("planned", {})
    unknown_aliases = set(aliases) - set(entities)
    if unknown_aliases:
        raise ValueError(f"Aliases refer to unknown model entities: {sorted(unknown_aliases)}")

    entries: list[InventoryEntry] = []
    assigned: set[str] = set()
    for entity, definition in sorted(entities.items()):
        table = definition.get("target_table")
        service_type = _service_type(entity, table, aliases, registrations, specs)
        if service_type in assigned:
            raise ValueError(f"Registered type {service_type!r} maps to more than one model entity")
        if service_type:
            assigned.add(service_type)
        role = definition.get("role", "unknown")
        if role not in {"classifier", "lookup", "fact", "bridge"}:
            raise ValueError(f"Unknown target-model role for {entity!r}: {role!r}")
        disposition = registrations[service_type] if service_type else "excluded" if role in {"classifier", "lookup"} else "not-a-target"
        spec = _table_spec(entity, service_type, table, specs)
        columns = definition.get("columns") or {}
        text_columns = tuple(
            sorted(name for name, column in columns.items() if isinstance(column, dict) and column.get("type") == "string")
        )
        reason = reasons.get(entity) if disposition != "supported" else None
        if disposition == "excluded" and not reason:
            raise ValueError(f"Excluded entity {entity!r} requires a reason")
        if disposition == "supported" and planned.get(entity):
            raise ValueError(f"Supported entity {entity!r} must not retain a planned phase")
        entries.append(
            InventoryEntry(
                entity=entity,
                service_type=service_type,
                target_table=table,
                role=role,
                disposition=disposition,
                marker=spec.get("reconciliation"),
                label_column=spec.get("label_column"),
                text_columns=text_columns,
                scope_columns=_scope_columns(entity, spec),
                reason=reason,
                planned=planned.get(entity),
            )
        )

    for service_type in sorted(set(registrations) - assigned):
        spec = specs.get(service_type) or {}
        disposition = registrations[service_type]
        reason = reasons.get(service_type) if disposition == "excluded" else None
        if disposition == "excluded" and not reason:
            raise ValueError(f"Excluded service type {service_type!r} requires a reason")
        entries.append(
            InventoryEntry(
                entity=service_type,
                service_type=service_type,
                target_table=spec.get("table_name"),
                role="service-only",
                disposition=disposition,
                marker=spec.get("reconciliation"),
                label_column=spec.get("label_column"),
                text_columns=(),
                scope_columns=_scope_columns(service_type, spec),
                reason=reason,
                planned=planned.get(service_type),
            )
        )

    unknown_notes = (set(reasons) | set(planned)) - {entry.entity for entry in entries}
    if unknown_notes:
        raise ValueError(f"Notes refer to unknown inventory entities: {sorted(unknown_notes)}")
    return entries


def _cell(value: str | None, *, code: bool = False) -> str:
    if not value:
        return "-"
    escaped = value.replace("|", "\\|").replace("\n", " ")
    return f"`{escaped}`" if code else escaped


def _column_list(columns: tuple[str, ...]) -> str:
    return ", ".join(_cell(column, code=True) for column in columns) or "-"


def render_document(document: str, model: dict[str, Any], specs: dict[str, Any], registrations: dict[str, str]) -> str:
    """Replaces generated content while preserving the document's maintained sections."""
    notes = yaml.safe_load(_section(document, MANUAL_START, MANUAL_END)) or {}
    entries = build_inventory(model, specs, registrations, notes)
    roles = Counter(entry.role for entry in entries)
    dispositions = Counter(entry.disposition for entry in entries)
    include_planned = bool(notes.get("planned"))
    headings = [
        "Entity",
        "Service type",
        "Target table",
        "Role",
        "Disposition",
        "Marker",
        "Configured label",
        "Model text columns",
        "Scope columns",
        "Reason",
    ]
    if include_planned:
        headings.append("Planned phase")

    lines = [
        "",
        "## Snapshot Counts",
        "",
        f"Target-model version: `{model['model']['version']}`.",
        f"Model entities: {len(entries) - roles['service-only']}. Registered service types: {len(registrations)}.",
        "",
        "| Role | Count |",
        "| --- | ---: |",
    ]
    for role, count in sorted(roles.items()):
        lines.append(f"| {role} | {count} |")
    lines.extend(["", "| Disposition | Count |", "| --- | ---: |"])
    for disposition, count in sorted(dispositions.items()):
        lines.append(f"| {disposition} | {count} |")
    lines.extend(
        [
            "",
            "## Entity Register",
            "",
            ROWS_START,
            "| " + " | ".join(headings) + " |",
            "| " + " | ".join("---" for _ in headings) + " |",
        ]
    )
    for entry in entries:
        cells = [
            _cell(entry.entity, code=True),
            _cell(entry.service_type, code=True),
            _cell(entry.target_table, code=True),
            _cell(entry.role),
            _cell(entry.disposition),
            _cell(entry.marker, code=True),
            _cell(entry.label_column, code=True),
            _column_list(entry.text_columns),
            _column_list(entry.scope_columns),
            _cell(entry.reason),
        ]
        if include_planned:
            cells.append(_cell(entry.planned))
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend([ROWS_END, ""])
    generated = _section(document, GENERATED_START, GENERATED_END)
    return document.replace(GENERATED_START + generated + GENERATED_END, GENERATED_START + "\n".join(lines) + GENERATED_END)


def documented_registrations(document: str) -> dict[str, str]:
    """Reads service types and dispositions from the generated Markdown table."""
    rows = _section(document, ROWS_START, ROWS_END).strip().splitlines()
    registrations: dict[str, str] = {}
    for row in rows[2:]:
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if len(cells) < 5:
            raise ValueError(f"Invalid inventory row: {row!r}")
        service_type = cells[1].strip("`")
        if service_type == "-":
            continue
        if service_type in registrations:
            raise ValueError(f"Registered type {service_type!r} appears more than once")
        status = cells[4]
        if status not in {"supported", "excluded"}:
            raise ValueError(f"Registered type {service_type!r} has invalid disposition {status!r}")
        registrations[service_type] = status
    return registrations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-model", type=Path, default=DEFAULT_TARGET_MODEL)
    parser.add_argument("--document", type=Path, default=DEFAULT_DOCUMENT)
    parser.add_argument("--check", action="store_true", help="Fail if the generated content is out of date")
    args = parser.parse_args()
    if not args.target_model.is_file():
        parser.error(f"Target model not found: {args.target_model}; pass --target-model with a local model file")
    model = yaml.safe_load(args.target_model.read_text(encoding="utf-8"))
    specs = yaml.safe_load((REPOSITORY_ROOT / "config/entities.yml").read_text(encoding="utf-8"))
    config = yaml.safe_load((REPOSITORY_ROOT / "config/config.yml").read_text(encoding="utf-8"))
    document = args.document.read_text(encoding="utf-8")
    rendered = render_document(document, model, specs, registered_types(specs, config["options"]["reconciliation"]))
    if args.check:
        if rendered != document:
            parser.exit(1, f"Inventory is out of date: {args.document}\n")
        print(f"Inventory is current: {args.document}")
    else:
        args.document.write_text(rendered, encoding="utf-8")
        print(f"Generated inventory: {args.document}")


if __name__ == "__main__":
    main()
