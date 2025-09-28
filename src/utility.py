import importlib
import os
from typing import Any, Callable


def import_sub_modules(module_folder: str) -> Any:
    __all__ = []
    # current_dir: str = os.path.dirname(__file__)
    for filename in os.listdir(module_folder):
        if filename.endswith(".py") and filename != "__init__.py":
            module_name: str = filename[:-3]
            __all__.append(module_name)
            importlib.import_module(f".{module_name}", package=__name__)


class Registry:
    items: dict = {}

    @classmethod
    def get(cls, key: str) -> Any | None:
        if key not in cls.items:
            raise ValueError(f"preprocessor {key} is not registered")
        return cls.items.get(key)

    @classmethod
    def register(cls, **args) -> Callable[..., Any]:
        def decorator(fn):
            if args.get("type") == "function":
                fn = fn()
            cls.items[args.get("key") or fn.__name__] = fn
            return fn

        return decorator

    @classmethod
    def is_registered(cls, key: str) -> bool:
        return key in cls.items
