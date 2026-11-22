import importlib
import os
import re
import sys
import unicodedata
from typing import Any, Callable, Generic, Literal, TypeVar
from urllib.parse import quote

import yaml
from loguru import logger


def normalize_text(text: str) -> str:
    """
    Normalize text to match PostgreSQL's authority.immutable_unaccent(lower(text)).

    Steps:
    1. Convert to lowercase
    2. Remove accents/diacritics using Unicode NFD normalization

    This ensures consistency with PostgreSQL trigram matching and embeddings.
    """
    if not text:
        return ""

    # Step 1: Lowercase
    text = text.lower()

    # Step 2: Remove accents (unaccent equivalent)
    # NFD = Canonical Decomposition (separates base chars from combining diacritics)
    # Filter out combining characters (category 'Mn' = Mark, nonspacing)
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")

    return text


def recursive_update(d1: dict, d2: dict) -> dict:
    """
    Recursively updates d1 with values from d2. If a value in d1 is a dictionary,
    and the corresponding value in d2 is also a dictionary, it recursively updates that dictionary.
    """
    for key, value in d2.items():
        if isinstance(value, dict) and key in d1 and isinstance(d1[key], dict):
            recursive_update(d1[key], value)
        else:
            d1[key] = value
    return d1


def recursive_filter_dict(
    data: dict[str, Any], filter_keys: set[str], filter_mode: Literal["keep", "exclude"] = "exclude"
) -> dict[str, Any]:
    """
    Recursively filters a dictionary to include only keys in the given set.

    Args:
        D (dict): The dictionary to filter.
        filter_keys (set): The set of keys to keep or exclude.
        filter_mode (str): mode of operation, either 'keep' or 'exclude'.

    Returns:
        dict: A new dictionary containing only the keys in K, with nested dictionaries also filtered.
    """
    if not isinstance(data, dict):
        return data

    return {
        key: (recursive_filter_dict(value, filter_keys=filter_keys, filter_mode=filter_mode) if isinstance(value, dict) else value)
        for key, value in data.items()
        if (key in filter_keys if filter_mode == "keep" else key not in filter_keys)
    }


def dget(data: dict, *path: str, default: Any = None) -> Any:
    if path is None or not data:
        return default

    ps: list[str] = list(path)

    d = None

    for p in ps:
        d = dotget(data, p)

        if d is not None:
            return d

    return d or default


def dotexists(data: dict, *paths: str) -> bool:
    for path in paths:
        if dotget(data, path, default="@@") != "@@":
            return True
    return False


def dotexpand(paths: str | list[str]) -> list[str]:
    """Expands paths with ',' and ':'."""
    if not paths:
        return []
    if not isinstance(paths, (str, list)):
        raise ValueError("dot path must be a string or list of strings")
    paths = paths if isinstance(paths, list) else [paths]
    expanded_paths: list[str] = []
    for p in paths:
        for q in p.replace(" ", "").split(","):
            if not q:
                continue
            if ":" in q:
                expanded_paths.extend([q.replace(":", "."), q.replace(":", "_")])
            else:
                expanded_paths.append(q)
    return expanded_paths


def dotget(data: dict, path: str, default: Any = None) -> Any:
    """Gets element from dict. Path can be x.y.y or x_y_y or x:y:y.
    if path is x:y:y then element is search using borh x.y.y or x_y_y."""

    for key in dotexpand(path):
        d: dict | None = data
        for attr in key.split("."):
            d = d.get(attr) if isinstance(d, dict) else None
            if d is None:
                break
        if d is not None:
            return d
    return default


def dotset(data: dict, path: str, value: Any) -> dict:
    """Sets element in dict using dot notation x.y.z or x:y:z"""

    d: dict = data
    attrs: list[str] = path.replace(":", ".").split(".")
    for attr in attrs[:-1]:
        if not attr:
            continue
        d: dict = d.setdefault(attr, {})
    d[attrs[-1]] = value

    return data


def env2dict(prefix: str, data: dict[str, str] | None = None, lower_key: bool = True) -> dict[str, str]:
    """Loads environment variables starting with prefix into."""
    if data is None:
        data = {}
    if not prefix:
        return data
    if lower_key:
        prefix = prefix.lower()
    for key, value in os.environ.items():
        if lower_key:
            key = key.lower()
        if key.startswith(prefix):
            dotset(data, key[len(prefix) + 1 :].replace("_", ":"), value)
    return data


def configure_logging(opts: dict[str, Any] | None = None, default_level: str = "INFO") -> None:
    """Configure logging with file and console handlers.

    Args:
        opts: Logging options from config (folder, handlers)
        default_level: Default log level if not specified in handlers
    """
    logger.remove()

    # Get log folder path, ensure it exists
    log_folder = opts.get("folder", "./logs") if opts else "./logs"
    os.makedirs(log_folder, exist_ok=True)

    # Add default console handler if no handlers specified
    if not opts or not opts.get("handlers"):
        logger.add(
            sys.stdout,
            level=default_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
            backtrace=True,
            diagnose=True,
        )
        # Add default file handler
        logger.add(
            os.path.join(log_folder, "sead_authority.log"),
            rotation="10 MB",
            retention="30 days",
            level=default_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            backtrace=True,
            diagnose=True,
        )
        return

    # Process custom handlers
    if opts.get("handlers"):
        for handler in opts["handlers"]:
            if not handler.get("sink"):
                continue

            # Replace sys.stdout string with actual sys.stdout
            if handler["sink"] == "sys.stdout":
                handler["sink"] = sys.stdout
            # Handle file sinks
            elif isinstance(handler["sink"], str) and handler["sink"].endswith(".log"):
                # Create log file path
                log_filename = handler["sink"]
                handler["sink"] = os.path.join(log_folder, log_filename)

                # Add rotation and retention if not specified
                if "rotation" not in handler:
                    handler["rotation"] = "10 MB"
                if "retention" not in handler:
                    handler["retention"] = "30 days"

            # Add backtrace and diagnose for better exception tracking
            if "backtrace" not in handler:
                handler["backtrace"] = True
            if "diagnose" not in handler:
                handler["diagnose"] = True

        logger.configure(handlers=opts["handlers"])


def import_sub_modules(module_folder: str) -> Any:
    __all__ = []
    # current_dir: str = os.path.dirname(__file__)
    for filename in os.listdir(module_folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name: str = filename[:-3]
            __all__.append(module_name)
            importlib.import_module(f".{module_name}", package=__name__)


def _ensure_key_property(cls):
    if not hasattr(cls, "key"):

        def key(self) -> str:
            return getattr(self, "_registry_key", "unknown")

        cls.key = property(key)
    return cls


def replace_env_vars(data: dict[str, Any] | list[Any] | str) -> dict[str, Any] | list[Any] | str:
    """Replaces recursively values in `data` that matches `${ENV_VAR}` with os.getenv("ENV_VAR", "")"""
    if isinstance(data, dict):
        return {k: replace_env_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [replace_env_vars(i) for i in data]
    if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        env_var: str = data[2:-1]
        return os.getenv(env_var, "")
    return data


T = TypeVar("T")


class Registry(Generic[T]):
    items: dict[str, T] = {}

    @classmethod
    def get(cls, key: str) -> T:
        if key not in cls.items:
            raise KeyError(f"preprocessor {key} is not registered")
        return cls.items[key]

    @classmethod
    def register(cls, **args) -> Callable[..., Any]:
        def decorator(fn_or_class):
            key: str = args.get("key") or fn_or_class.__name__
            if args.get("type") == "function":
                fn_or_class = fn_or_class()
            else:
                setattr(fn_or_class, "_registry_key", key)
                fn_or_class = _ensure_key_property(fn_or_class)

            cls.items[key] = fn_or_class

            fn_or_class = cls.registered_class_hook(fn_or_class, **args)
            return fn_or_class

        return decorator

    @classmethod
    def is_registered(cls, key: str) -> bool:
        return key in cls.items

    @classmethod
    def registered_class_hook(cls, fn_or_class: Any, **args) -> Any:  # pylint: disable=unused-argument
        return fn_or_class


def create_db_uri(
    *,
    host: str,
    port: int | str,
    user: str,
    dbname: str,
    password: str | None = None,
    driver: str = "postgresql",
    **kwargs,  # pylint: disable=unused-argument
) -> str:
    """
    Builds database URI from the individual config elements.
    """
    if password:
        quoted_password: str = quote(password, safe="")
        return f"{driver}://{user}:{quoted_password}@{host}:{port}/{dbname}"
    return f"{driver}://{user}@{host}:{port}/{dbname}"


def load_resource_yaml(key: str) -> dict[str, Any] | None:
    """Loads a resource YAML file from the resources folder."""

    resource_path: str = os.path.join(os.path.dirname(__file__), "resources", f"{key}.yml")
    if not os.path.exists(resource_path):
        return None

    with open(resource_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


RECONCILIATION_MARKERS: tuple[str, ...] = ("simple", "lookup")
CONTEXT_PROPERTY_ID: str = "context"
CONTEXT_DESCRIPTION_PREFIX: str = "Context: "


def reconciliation_marker(table_spec: Any) -> str | None:
    """Returns the reconciliation marker of a table specification, or None when unmarked."""
    if not isinstance(table_spec, dict):
        return None
    marker: Any = table_spec.get("reconciliation")
    return marker if marker in RECONCILIATION_MARKERS else None


def is_marked_for_reconciliation(table_spec: Any) -> bool:
    """Returns True when the table specification declares a supported reconciliation marker."""
    return reconciliation_marker(table_spec) is not None


def scope_columns(table_spec: Any) -> tuple[str, ...]:
    """Returns the declared scope columns, in declaration order.

    Raises ValueError when the value is not a list of non-empty names.
    """
    if not isinstance(table_spec, dict):
        return ()
    columns: Any = table_spec.get("scope_columns") or []
    if not isinstance(columns, list):
        raise ValueError(f"scope_columns must be a list, got {columns!r}")
    resolved: list[str] = []
    for column in columns:
        if not isinstance(column, str) or not column.strip():
            raise ValueError(f"scope_columns entries must be non-empty text, got {column!r}")
        resolved.append(column.strip())
    return tuple(resolved)


def resolve_scope_context(table_specs: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Resolves declared scope columns to the parent entity's label source.

    Each scope column must match the `id_column` of exactly one configured parent
    entity that also declares a `label_column`. The returned dictionaries keep the
    declaration order and carry the parent table, its ID and label columns, and the
    join alias used by the generated view.
    """
    table_spec: Any = table_specs.get(key)
    if not isinstance(table_spec, dict):
        raise ValueError(f"Unknown table specification '{key}'")
    resolved: list[dict[str, Any]] = []
    for index, column in enumerate(scope_columns(table_spec), start=1):
        parents: list[str] = sorted(
            parent_key
            for parent_key, parent in table_specs.items()
            if isinstance(parent, dict) and parent.get("id_column") == column and parent.get("label_column")
        )
        if len(parents) != 1:
            detail: str = "no configured parent entity" if not parents else f"more than one configured parent entity ({', '.join(parents)})"
            raise ValueError(
                f"Scope column '{column}' for '{key}' resolves to {detail}; "
                "declare the parent entity with matching id_column and label_column first"
            )
        parent_spec: dict[str, Any] = table_specs[parents[0]]
        resolved.append(
            {
                "column": column,
                "parent_key": parents[0],
                "table_name": parent_spec["table_name"],
                "id_column": parent_spec["id_column"],
                "label_column": parent_spec["label_column"],
                "alias": f"scope_{index}",
            }
        )
    return resolved


def build_context_property(table_spec: dict[str, Any]) -> list[dict[str, str]]:
    """Returns the OpenRefine property metadata published for a scoped reconciliation entry."""
    if not scope_columns(table_spec):
        return []
    return [
        {
            "id": CONTEXT_PROPERTY_ID,
            "name": "Context",
            "type": "string",
            "description": "Parent label that identifies this entry; supplied context filters candidates before ranking",
        }
    ]


def build_classifier_fuzzy_sql(key: str, table_spec: dict[str, Any]) -> str:
    """Builds the marked-classifier fuzzy query with explicit threshold parameters.

    Scoped entities also receive the normalized request context as a bound value.
    """
    if scope_columns(table_spec):
        return (
            f"select * from authority.fuzzy_{key}("
            "%(q)s::text, %(n)s::int, "
            "%(label_threshold)s::double precision, "
            "%(description_threshold)s::double precision, "
            "%(context)s::text);"
        )
    return (
        f"select * from authority.fuzzy_{key}("
        "%(q)s::text, %(n)s::int, "
        "%(label_threshold)s::double precision, "
        "%(description_threshold)s::double precision);"
    )


def build_classifier_alternate_identity_sql(key: str, table_spec: dict[str, Any]) -> str:
    """Builds an exact alternate-identity query that keeps the configured ID field."""
    id_column: str = table_spec["id_column"]
    alternate_column: str = table_spec["alternate_identity_column"]
    scoped: bool = bool(scope_columns(table_spec))
    context_filter: str = ""
    extra_columns: str = ""
    if scoped:
        context_filter = (
            "  and (nullif(%(context)s::text, '') is null\n"
            "       or position(authority.immutable_unaccent(lower(%(context)s::text)) in coalesce(t.norm_context, '')) > 0)\n"
        )
        extra_columns = ", t.context, true as context_match"
    return (
        "with target as (\n"
        "  select *\n"
        f"  from authority.{key}\n"
        f"  where {alternate_column} = %(alternate_identity)s\n"
        ")\n"
        "select\n"
        f"  t.{id_column},\n"
        "  t.label,\n"
        "  1.0 as name_sim,\n"
        "  exists (\n"
        f"    select 1 from authority.{key} as other\n"
        f"    where other.norm_label = t.norm_label and other.{id_column} <> t.{id_column}\n"
        "  ) as label_ambiguous"
        f"{extra_columns}\n"
        "from target as t\n"
        "where true\n"
        f"{context_filter}".rstrip()
    )


def build_classifier_prefix_sql(key: str, table_spec: dict[str, Any]) -> str:
    """Builds a normalized label-prefix query for a marked classifier."""
    id_column: str = table_spec["id_column"]
    return f"""
with params as (
  select authority.immutable_unaccent(lower(%(q)s))::text as q
)
select
  s.{id_column},
  s.label,
  s.description,
  greatest(similarity(s.norm_label, pq.q), 0.0001) as name_sim
from authority.{key} as s
cross join params pq
where left(s.norm_label, char_length(pq.q)) = pq.q
order by name_sim desc, s.label
limit %(n)s::int;
""".strip()


_ALIAS_RE = re.compile(r"^(?P<source>.+?)\s+as\s+(?P<alias>\"[^\"]+\"|[A-Za-z_][\w.]*)\s*$", re.IGNORECASE | re.DOTALL)


def view_column_source(column: Any) -> str | None:
    """Returns the view column expression from a plain or 'as alias' column entry."""
    if not isinstance(column, str):
        return None
    expression: str = column.strip()
    if not expression:
        return None
    match: re.Match | None = _ALIAS_RE.match(expression)
    if match:
        return match.group("source").strip()
    return expression


def view_column_alias(column: Any) -> str:
    """Returns the column name a view expression is exposed under, honoring 'as alias'."""
    if not isinstance(column, str) or not column.strip():
        raise ValueError(f"Invalid view column entry: {column!r}")
    match: re.Match | None = _ALIAS_RE.match(column.strip())
    if match:
        return match.group("alias").strip('"')
    return column.strip().split()[-1].split(".")[-1]


def build_classifier_details_sql(key: str, table_spec: dict[str, Any]) -> str:
    """Builds the details query for a marked classifier from its table specification.

    Each details column is a name in the generated view, optionally with a display
    header ('data_type_group_name as "Group"'). Qualified or aliased view columns
    (from extra_columns and joins) are allowed here too.
    """
    id_column: str = table_spec["id_column"]
    columns: list[str] = [f's.{id_column} as "ID"', 's.label as "Name"', 's.description as "Description"']
    for details_column in table_spec.get("details_columns") or []:
        expression: str | None = view_column_source(details_column)
        if expression is None:
            raise ValueError(f"Classifier '{key}' has an invalid details column: {details_column!r}")
        header: str = view_column_alias(details_column).strip('"')
        if "." in expression:
            columns.append(f'{expression} as "{header}"')
        else:
            columns.append(f's.{expression} as "{header}"')
    projected: str = ",\n       ".join(columns)
    return f"select {projected}\nfrom authority.{key} as s\nwhere s.{id_column} = %(id)s::int"


def build_classifier_specification(key: str, table_spec: dict[str, Any]) -> dict[str, Any]:
    """Builds a strategy specification from a marked reconciliation table specification.

    Scoped entries publish a `context` property, and entries with an
    `alternate_identity_column` receive an exact alternate-identity query that
    returns the configured ID column under its configured name.
    """
    marker: str | None = reconciliation_marker(table_spec)
    sql_queries: dict[str, str] = {
        "fuzzy_find_sql": build_classifier_fuzzy_sql(key, table_spec),
        "prefix_find_sql": build_classifier_prefix_sql(key, table_spec),
        "details_sql": build_classifier_details_sql(key, table_spec),
    }
    specification: dict[str, Any] = {
        "key": key,
        "display_name": table_spec.get("name") or key.replace("_", " ").title(),
        "id_field": table_spec["id_column"],
        "label_field": "label",
        "properties": build_context_property(table_spec),
        "property_settings": {},
        "reconciliation": marker,
        "sql_queries": sql_queries,
    }
    alternate_identity_column: Any = table_spec.get("alternate_identity_column")
    if isinstance(alternate_identity_column, str) and alternate_identity_column.strip():
        specification["alternate_identity_field"] = alternate_identity_column.strip()
        sql_queries["alternate_identity_sql"] = build_classifier_alternate_identity_sql(key, table_spec)
    return specification


def classifier_view_columns(table_spec: dict[str, Any]) -> set[str]:
    """Returns the column names a marked classifier view exposes for details queries.

    Plain names are listed as-is; qualified or aliased expressions (from extra_columns)
    are listed as the full expression, so details_columns can reference either form.
    """
    columns: set[str] = {table_spec["id_column"], "label", "description"}
    if scope_columns(table_spec):
        columns.update({"context", "norm_context"})
    alternate_identity_column: str | None = table_spec.get("alternate_identity_column")
    if alternate_identity_column:
        columns.add(alternate_identity_column)
    for extra_column in table_spec.get("extra_columns") or []:
        expression: str | None = view_column_source(extra_column)
        if expression:
            columns.add(expression)
            columns.add(view_column_alias(extra_column))
    return columns


_ConfiguredSpecificationResolver = Callable[[str], "dict[str, Any] | None"]  # pylint: disable=invalid-name
_configured_specification_resolver: "_ConfiguredSpecificationResolver | None" = None  # pylint: disable=invalid-name


def set_configured_specification_resolver(resolver: "_ConfiguredSpecificationResolver") -> None:
    """Registers the function that builds a specification for a configured classifier key.

    The strategies package sets this at import time. Keeping the configuration lookup
    outside this module avoids a cyclic import between src.utility and src.configuration.
    """
    global _configured_specification_resolver  # pylint: disable=global-statement
    _configured_specification_resolver = resolver


def resolve_configured_specification(key: str) -> dict[str, Any] | None:
    """Builds a specification for a marked classifier key using the registered resolver."""
    if _configured_specification_resolver is None:
        return None
    return _configured_specification_resolver(key)


def resolve_specification(specification: dict[str, Any] | str | None) -> dict[str, Any]:
    """Resolves a specification which can be either a dict or a resource key string."""
    if isinstance(specification, dict):
        return specification
    if isinstance(specification, str):
        resource_specification: dict[str, Any] | None = load_resource_yaml(specification)
        if resource_specification is not None:
            return resource_specification
        return resolve_configured_specification(specification)  # type: ignore
    return {
        "key": "unknown",
        "id_field": "id",
        "label_field": "name",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }
