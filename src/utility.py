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


def build_classifier_fuzzy_sql(key: str) -> str:
    """Builds the marked-classifier fuzzy query with explicit threshold parameters."""
    return (
        f"select * from authority.fuzzy_{key}("
        "%(q)s::text, %(n)s::int, "
        "%(label_threshold)s::double precision, "
        "%(description_threshold)s::double precision);"
    )


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
    columns: list[str] = [f's.{id_column} as "ID"', 's.label as "Name"']
    if table_spec.get("description_column"):
        columns.append('s.description as "Description"')
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
    """Builds a strategy specification from a marked classifier table specification."""
    return {
        "key": key,
        "display_name": table_spec.get("name") or key.replace("_", " ").title(),
        "id_field": table_spec["id_column"],
        "label_field": "label",
        "properties": [],
        "property_settings": {},
        "reconciliation": "simple",
        "sql_queries": {
            "fuzzy_find_sql": build_classifier_fuzzy_sql(key),
            "details_sql": build_classifier_details_sql(key, table_spec),
        },
    }


def classifier_view_columns(table_spec: dict[str, Any]) -> set[str]:
    """Returns the column names a marked classifier view exposes for details queries.

    Plain names are listed as-is; qualified or aliased expressions (from extra_columns)
    are listed as the full expression, so details_columns can reference either form.
    """
    columns: set[str] = {table_spec["id_column"], "label"}
    if table_spec.get("description_column"):
        columns.add("description")
    alternate_identity_column: str | None = table_spec.get("alternate_identity_column")
    if alternate_identity_column:
        columns.add(alternate_identity_column)
    for extra_column in table_spec.get("extra_columns") or []:
        expression: str | None = view_column_source(extra_column)
        if expression:
            columns.add(expression)
            columns.add(view_column_alias(extra_column))
    return columns


_ConfiguredSpecificationResolver = Callable[[str], "dict[str, Any] | None"]
_configured_specification_resolver: "_ConfiguredSpecificationResolver | None" = None


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
