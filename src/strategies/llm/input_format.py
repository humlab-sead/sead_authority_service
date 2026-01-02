from __future__ import annotations

import csv
import io
import json
from typing import Any, Literal, Protocol

from src.utility import Registry

# pylint: disable=unused-argument, pointless-string-statement


class FormatterRegistry(Registry):
    items: dict[str, RowFormatter] = {}


Formatters: FormatterRegistry = FormatterRegistry()


class RowFormatter(Protocol):
    def format(self, rows: list[dict[str, Any]], *, columns: list[str], **kwargs) -> str: ...


@Formatters.register(key="markdown")
class MarkdownFormatter:

    def format(self, rows: list[dict[str, Any]], *, columns: list[str], **kwargs) -> str:
        if not columns:
            return "_(no rows)_"

        def esc(v: Any) -> str:
            s = "" if v is None else str(v)
            return s.replace("|", r"\|").replace("\n", "↩")

        head = "| " + " | ".join(columns) + " |"
        sep = "| " + " | ".join("---" for _ in columns) + " |"
        body = "\n".join("| " + " | ".join(esc(r.get(c, "")) for c in columns) + " |" for r in rows)
        return "\n".join([head, sep, body]) if body else "\n".join([head, sep])


@Formatters.register(key="csv")
class CSVFormatter:

    def format(self, rows: list[dict[str, Any]], *, columns: list[str], **kwargs) -> str:
        if not columns:
            return ""
        sep: str = kwargs.get("sep", "|")
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=sep, quotechar='"', lineterminator="\n", quoting=csv.QUOTE_MINIMAL, escapechar="\\")
        writer.writerow(columns)
        for r in rows:
            writer.writerow([("" if r.get(c) is None else r.get(c, "")) for c in columns])
        return buf.getvalue()


@Formatters.register(key="json")
class JSONFormatter:

    # def format(self, rows: list[dict[str, Any]], columns: list[str], **kwargs) -> str:  # pylint: disable=unused-argument
    #     return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))

    # def _project_row(self, row: dict[str, Any], columns: list[str] | None) -> dict[str, Any]:
    #     if not columns:
    #         return dict(row)
    #     return {k: row.get(k) for k in columns}

    # def _order_keys(self, d: dict[str, Any]) -> dict[str, Any]:
    #     # Put id / *_id first, then label, description, then the rest (alphabetical)
    #     keys = list(d.keys())
    #     id_keys = [k for k in keys if k == "id" or k.endswith("_id")]
    #     label_keys = [k for k in keys if k == "label"]
    #     desc_keys = [k for k in keys if k == "description"]
    #     rest = sorted([k for k in keys if k not in set(id_keys + label_keys + desc_keys)])
    #     ordered = id_keys + label_keys + desc_keys + rest
    #     return {k: d.get(k) for k in ordered}

    # def _coerce_ids_to_str(self, d: dict[str, Any]) -> dict[str, Any]:
    #     out = dict(d)
    #     for k, v in list(out.items()):
    #         if k == "id" or k.endswith("_id"):
    #             if v is not None and not isinstance(v, str):
    #                 out[k] = str(v)
    #     return out

    def format(
        self,
        rows: list[dict[str, Any]],
        *,
        columns: list[str] | None = None,
        **kwargs,
    ) -> str:

        # sort_by: str | None = kwargs.get("sort_by", None)
        # reverse: bool = kwargs.get("reverse", False)
        pretty: bool = kwargs.get("pretty", False)
        # stringify_ids: bool = kwargs.get("stringify_ids", True)

        # # 1) project
        # projected: list[dict[str, Any]] = [_project_row(r, columns) for r in rows]

        # # 2) coerce ids
        # if stringify_ids:
        #     projected = [_coerce_ids_to_str(r) for r in projected]

        # # 3) stable key order
        # ordered: list[dict[str, Any]] = [_order_keys(r) for r in projected]

        # # 4) optional sort (after coercion)
        # if sort_by:
        #     ordered.sort(key=lambda r: (r.get(sort_by) is None, r.get(sort_by)), reverse=reverse)
        ordered: list[dict[str, Any]] = list(rows)
        # 5) dump strict JSON
        if pretty:
            return json.dumps(ordered, ensure_ascii=False, allow_nan=False, indent=2)
        return json.dumps(ordered, ensure_ascii=False, allow_nan=False, separators=(",", ":"))


def _is_scalar(x: Any) -> bool:
    return isinstance(x, (str, int, float, bool)) or x is None


def _has_non_scalar(rows: list[dict[str, Any]]) -> bool:
    return any(not _is_scalar(v) for r in rows for v in r.values())


def _total_chars(rows: list[dict[str, Any]]) -> int:
    return sum(len(str(v)) if v is not None else 4 for r in rows for v in r.values())


def format_rows_for_llm(  # pylint: disable=too-many-arguments, too-many-locals
    rows: list[dict[str, Any]],
    *,
    target_format: Literal["auto", "markdown", "csv", "json"] = "auto",
    sep: str = "|",
    column_map: dict[str, str] | None = None,  # e.g. {"id": "biblio_id", "label": "title", "description": "authors"},
    logical_keys: list[str] | None = None,
) -> tuple[str, str]:
    """
    Format SQL-style rows into markdown/csv/json for LLM use.
    Returns (table_string, descriptive_blurb).

    Parameters:
    - rows: list of dict-like records (from SQL query)
    - entity_type: human-readable entity name ("bibliographic reference", "sample type", ...)
    - target_format: 'markdown', 'csv', 'json', or 'auto'
    - column_map: maps logical keys {'id', 'label', 'description'?} to actual field names in the rows
                  If None → assumes {'id': 'id', 'label': 'label'} (description optional)
    """

    if len(rows or []) == 0:
        return "_(no rows)_", "No records available."

    keys: list[str] = logical_keys or ["id", "label", "description"]
    data_keys: set[str] = set(rows[0].keys())

    """ Build default mapping from logical keys that exist in the data """
    default_map: dict[str, str] = {k: k for k in keys if k in data_keys}
    if not default_map:
        default_map = {"id": list(data_keys)[0]}  # Fallback to first column as 'id'
    """ Merge with user-provided mapping, prioritizing user map """
    column_map = default_map | (column_map or {})

    """ Validate that all map keys are from the logical keys """
    if not all(k in keys for k in (column_map or {}).keys()):
        raise KeyError(f"Map keys must all be from ({', '.join(keys)})")

    """ Ensure correct  column order """
    normalized_column_keys: list[str] = [k for k in keys if k in column_map]

    # if "id" not in normalized_column_keys or "label" not in normalized_column_keys:
    #     raise ValueError("column_map must at least map 'id' and 'label' keys")

    """ Normalize rows to only include mapped keys """
    normalized_rows: list[dict[str, Any]] = [{alias: r[real_key] for alias, real_key in column_map.items() if real_key in r} for r in rows]

    fmt = _resolve_format(
        target_format,
        n_rows=len(normalized_rows),
        has_non_scalar=_has_non_scalar(normalized_rows),
        total_chars=_total_chars(normalized_rows),
    )

    # Here we could decide to pass data keys instead of normalized keys (if that would help LLM)
    formatter: RowFormatter = FormatterRegistry.get(fmt)()  # type: ignore
    table: str = formatter.format(rows=normalized_rows, columns=normalized_column_keys, sep=sep)

    return fmt, table


def _resolve_format(target_format: str, n_rows: int, has_non_scalar: bool, total_chars: int) -> str:
    fmt: str = (target_format or "auto").lower()
    if fmt != "auto":
        return fmt
    if has_non_scalar or n_rows > 200:
        return "json"
    if n_rows <= 50 and total_chars <= 20_000:
        return "markdown"
    return "csv"


# def create_blurb_for_records(rows: list[dict[str, Any]], entity_type: str, columns: list[str], output_format: str) -> str:
#     """Create a descriptive blurb for the LLM prompt based on the records and format"""
#     if not columns:
#         raise ValueError("No columns provided for blurb generation")
#     col_str = ", ".join(columns)
#     blurb = (
#         f"You are given {entity_type} candidates in {output_format.upper()} format.\n"
#     )
#     if "label" in columns:
#         blurb += "Use `label` for name matching"
#         if "description" in columns:
#             blurb += " and `description` for context"
#         blurb += ". "
#     blurb += "If uncertain, return your best guess with a lower score."
#     return blurb
