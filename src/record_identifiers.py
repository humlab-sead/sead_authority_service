"""Shared parsing and formatting for reconciliation record URIs.

The reconciliation service exposes records as absolute URIs of the form
``<id_base><type>/<integer id>``. Matching, record lists, details lookups, and
candidate verification all use the helpers here so one record keeps the same
URI and positive integer ID in every response.
"""

from urllib.parse import urlsplit

# PostgreSQL stores target primary keys in ``integer`` columns.
POSTGRES_INTEGER_MAX = 2_147_483_647


def valid_id_base(id_base: str | None) -> bool:
    """Return whether ``id_base`` is an absolute URI ending in ``/`` with no query or fragment."""
    if not isinstance(id_base, str) or not id_base or "?" in id_base or "#" in id_base:
        return False
    try:
        parsed = urlsplit(id_base)
    except ValueError:
        return False
    return bool(parsed.scheme and parsed.netloc and parsed.path.endswith("/") and not parsed.query and not parsed.fragment)


def parse_record_uri(candidate_id: str, entity_type: str, id_base: str | None) -> int | None:
    """Return the positive integer ID encoded in a record URI, or ``None`` when it does not match.

    Scheme and host are compared without case sensitivity. A different base path, a
    different type segment, an extra path segment, a query string, or a fragment is
    rejected. Leading zeros are accepted and resolved to the integer value.
    """
    if not valid_id_base(id_base) or not isinstance(candidate_id, str) or "?" in candidate_id or "#" in candidate_id:
        return None
    try:
        base = urlsplit(id_base)  # type: ignore[arg-type]
        candidate = urlsplit(candidate_id)
    except ValueError:
        return None
    if (
        not candidate.scheme  # pylint: disable=too-many-boolean-expressions
        or not candidate.netloc
        or candidate.scheme.casefold() != base.scheme.casefold()
        or candidate.netloc.casefold() != base.netloc.casefold()
        or candidate.query
        or candidate.fragment
        or not candidate.path.startswith(base.path)
    ):
        return None

    relative_path: str = candidate.path[len(base.path) :]
    type_segment, separator, id_segment = relative_path.partition("/")
    if not separator or type_segment != entity_type or "/" in id_segment or not id_segment.isascii() or not id_segment.isdecimal():
        return None
    try:
        record_id = int(id_segment)
    except ValueError:
        return None
    return record_id if record_id > 0 else None


def within_postgres_integer(record_id: int) -> bool:
    """Return whether ``record_id`` fits a PostgreSQL ``integer`` column."""
    return 0 < record_id <= POSTGRES_INTEGER_MAX


def format_record_uri(id_base: str, id_path: str, target_id: int | str) -> str:
    """Return the canonical record URI for a projected record."""
    return f"{id_base}{id_path}/{target_id}"
