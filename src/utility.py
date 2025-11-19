import importlib
import os
import sys
import unicodedata
from datetime import datetime
from typing import Any, Callable, Literal

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


def recursive_filter_dict(data: dict[str, Any], filter_keys: set[str], filter_mode: Literal["keep", "exclude"] = "exclude") -> dict[str, Any]:
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


def configure_logging(opts: dict[str, Any] | None=None) -> None:

    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )
    if not opts:
        return

    if opts.get("handlers"):

        for handler in opts["handlers"]:

            if not handler.get("sink"):
                continue

            if handler["sink"] == "sys.stdout":
                handler["sink"] = sys.stdout

            elif isinstance(handler["sink"], str) and handler["sink"].endswith(".log"):
                handler["sink"] = os.path.join(
                    opts.get("folder", "logs"),
                    f"{datetime.now().strftime('%Y%m%d')}_{handler['sink']}",
                )

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
    """Searches dict data recursively for values that are strings and matches £´${ENV_VAR} and replaces value with os.getenv("ENV_VAR", "")"""
    if isinstance(data, dict):
        return {k: replace_env_vars(v) for k, v in data.items()}
    if isinstance(data, list):
        return [replace_env_vars(i) for i in data]
    if isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        env_var: str = data[2:-1]
        return os.getenv(env_var, "")
    return data


class Registry:
    items: dict = {}

    @classmethod
    def get(cls, key: str) -> Any | None:
        if key not in cls.items:
            raise KeyError(f"preprocessor {key} is not registered")
        return cls.items.get(key)

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
            return fn_or_class

        return decorator

    @classmethod
    def is_registered(cls, key: str) -> bool:
        return key in cls.items


def create_db_uri(*, host: str, port: int | str, user: str, dbname: str) -> str:
    """
    Builds database URI from the individual config elements.
    """
    return f"postgresql://{user}@{host}:{port}/{dbname}"


def get_connection_uri(connection: Any) -> str:
    conn_info = connection.get_dsn_parameters()
    user: str = conn_info.get("user")
    host: str = conn_info.get("host")
    port: str = conn_info.get("port")
    dbname: str = conn_info.get("dbname")
    uri: str = f"postgresql://{user}@{host}:{port}/{dbname}"
    return uri


def load_resource_yaml(key: str) -> dict[str, Any] | None:
    """Loads a resource YAML file from the resources folder."""

    resource_path: str = os.path.join(os.path.dirname(__file__), "resources", f"{key}.yaml")
    if not os.path.exists(resource_path):
        return None

    with open(resource_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
