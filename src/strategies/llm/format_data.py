from __future__ import annotations
import csv, io, json
from dataclasses import dataclass
from typing import Any, List, Mapping, Protocol, Tuple

# ---------- Strategy interface ----------

class RowFormatter(Protocol):
    name: str
    def format(self, rows: List[Mapping[str, Any]], columns: List[str]) -> str: ...


# ---------- Concrete formatters ----------

class MarkdownFormatter:
    name = "markdown"
    def format(self, rows: List[Mapping[str, Any]], columns: List[str]) -> str:
        if not columns:
            return "_(no rows)_"
        def esc(v: Any) -> str:
            s = "" if v is None else str(v)
            return s.replace("|", r"\|").replace("\n", "↩")
        head = "| " + " | ".join(columns) + " |"
        sep  = "| " + " | ".join("---" for _ in columns) + " |"
        body = "\n".join("| " + " | ".join(esc(r.get(c, "")) for c in columns) + " |" for r in rows)
        return "\n".join([head, sep, body]) if body else "\n".join([head, sep])


class CSVFormatter:
    name = "csv"
    def __init__(self, sep: str = "|"):
        self.sep = sep
    def format(self, rows: List[Mapping[str, Any]], columns: List[str]) -> str:
        if not columns:
            return ""
        buf = io.StringIO()
        writer = csv.writer(
            buf, delimiter=self.sep, quotechar='"',
            lineterminator="\n", quoting=csv.QUOTE_MINIMAL, escapechar="\\"
        )
        writer.writerow(columns)
        for r in rows:
            writer.writerow([("" if r.get(c) is None else r.get(c, "")) for c in columns])
        return buf.getvalue()


class JSONFormatter:
    name = "json"
    def format(self, rows: List[Mapping[str, Any]], columns: List[str]) -> str:
        return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


# ---------- Registry ----------

@dataclass
class FormatRegistry:
    markdown: RowFormatter = MarkdownFormatter()
    json: RowFormatter = JSONFormatter()
    def get(self, key: str, *, csv_sep: str = "|") -> RowFormatter:
        k = key.lower()
        if k == "markdown": return self.markdown
        if k == "json": return self.json
        if k == "csv": return CSVFormatter(csv_sep)
        raise ValueError(f"Unknown formatter: {key!r}")


# ---------- Helpers ----------

def _is_scalar(x: Any) -> bool:
    return isinstance(x, (str, int, float, bool)) or x is None

def _has_non_scalar(rows: List[Mapping[str, Any]]) -> bool:
    return any(not _is_scalar(v) for r in rows for v in r.values())

def _total_chars(rows: List[Mapping[str, Any]]) -> int:
    return sum(len(str(v)) if v is not None else 4 for r in rows for v in r.values())


# ---------- Main orchestrator ----------

def format_rows_for_llm(
    rows: List[Mapping[str, Any]],
    *,
    entity_type: str,
    target_format: str = "auto",         # 'markdown' | 'csv' | 'json' | 'auto'
    csv_separator: str = "|",
    column_map: dict[str, str] | None = None,  # e.g. {"id": "biblio_id", "label": "title", "description": "authors"}
    registry: FormatRegistry | None = None,
) -> Tuple[str, str]:
    """
    Format SQL-style rows into markdown/csv/json for LLM use.
    Returns (table_string, descriptive_blurb).

    Parameters:
    - rows: List of dict-like records (from SQL query)
    - entity_type: human-readable entity name ("bibliographic reference", "sample type", ...)
    - target_format: 'markdown', 'csv', 'json', or 'auto'
    - column_map: maps logical keys {'id', 'label', 'description'?} to actual field names in the rows
                  If None → assumes {'id': 'id', 'label': 'label'} (description optional)
    """
    registry = registry or FormatRegistry()

    # Default map, with description optional
    default_map = {"id": "id", "label": "label"}
    if column_map:
        default_map.update(column_map)
    column_map = default_map

    # Normalize rows using the mapping
    normalized: list[dict[str, Any]] = []
    for r in rows:
        new_r = {}
        for alias, real_key in column_map.items():
            if real_key in r:  # Skip missing description cleanly
                new_r[alias] = r.get(real_key)
        normalized.append(new_r)

    columns = [k for k in column_map.keys() if any(k in row for row in normalized)]

    # Auto format selection
    fmt = (target_format or "auto").lower()
    if fmt == "auto":
        if _has_non_scalar(normalized) or len(rows) > 200:
            fmt = "json"
        else:
            payload = _total_chars(normalized)
            fmt = "markdown" if (len(rows) <= 50 and payload <= 20_000) else "csv"

    formatter = registry.get(fmt, csv_sep=csv_separator)
    table = formatter.format(normalized, columns)

    # Build blurb dynamically
    col_str = ", ".join(columns)
    blurb = (
        f"You are given {len(rows)} {entity_type} candidate records in {formatter.name.upper()} format.\n"
        f"Columns: {col_str or '(none)'}.\n"
        f"Task: Given a query string, select the **single best match**.\n"
        f"Return the `{columns[0]}` of the best match and a similarity score between 0 and 1.\n"
    )
    if "label" in columns:
        blurb += f"Use `label` for name matching"
        if "description" in columns:
            blurb += " and `description` for context"
        blurb += ". "
    blurb += "If uncertain, return your best guess with a lower score."

    return table, blurb
