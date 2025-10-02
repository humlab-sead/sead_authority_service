from __future__ import annotations

import functools
import inspect
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields
from inspect import isclass
from typing import Any, Callable, Generic, Self, Type, TypeVar

from src.utility import dget, recursive_filter_dict, recursive_update

from .config import Config

T = TypeVar("T", str, int, float)

# pylint: disable=global-statement


class ConfigProvider(ABC):
    """Abstract configuration provider for dependency injection"""

    @abstractmethod
    def get_config(self, context: str = None) -> Config:
        """Get configuration for the given context"""

    @abstractmethod
    def is_configured(self, context: str = None) -> bool:
        """Check if configuration exists for the given context"""


class SingletonConfigProvider(ConfigProvider):
    """Production config provider using Config Store singleton"""

    def get_config(self, context: str = None) -> Config:
        return ConfigStore.get_instance().config(context)

    def is_configured(self, context: str = None) -> bool:
        return ConfigStore.get_instance().is_configured(context)


class MockConfigProvider(ConfigProvider):
    """Test config provider with controllable configuration"""

    def __init__(self, config: Config, context: str = "default"):
        self._config = config
        self._context = context

    def get_config(self, context: str = None) -> Config:
        return self._config

    def is_configured(self, context: str = None) -> bool:
        return self._config is not None


# Global provider instance - can be swapped for testing
_current_provider: ConfigProvider = SingletonConfigProvider()
_provider_lock = threading.Lock()


def get_config_provider() -> ConfigProvider:
    """Get the current configuration provider"""
    return _current_provider


def set_config_provider(provider: ConfigProvider) -> ConfigProvider:
    """Set the current configuration provider (useful for testing)"""
    global _current_provider
    with _provider_lock:
        old_provider = _current_provider
        _current_provider = provider
        return old_provider


def reset_config_provider() -> None:
    """Reset to the default singleton provider"""
    global _current_provider
    with _provider_lock:
        _current_provider = SingletonConfigProvider()


@dataclass
class Configurable:
    """A decorator for dataclassed classes that will resolve all ConfigValue fields"""

    def resolve(self):
        """Resolve all ConfigValue fields in the dataclass."""
        for attrib in fields(self):
            if isinstance(getattr(self, attrib.name), ConfigValue):
                setattr(self, attrib.name, getattr(self, attrib.name).resolve())

    # def __post_init__(self):
    #     self.resolve()


@dataclass
class ConfigValue(Generic[T]):
    """A class to represent a value that should be resolved from a configuration file"""

    key: str | Type[T]
    default: T | None = None
    description: str | None = None
    after: Callable[[T], T] | None = None
    mandatory: bool = False

    @property
    def value(self) -> T:
        """Resolve the value from the current store (configuration file)"""
        return self.resolve()

    def resolve(self, context: str = None) -> T:
        """Resolve the value from the current store (configuration file)"""
        if isinstance(self.key, Config):
            return get_config_provider().get_config(context)  # type: ignore
        if isclass(self.key):
            return self.key()
        if self.mandatory and not self.default:
            if not get_config_provider().get_config(context).exists(self.key):
                raise ValueError(f"ConfigValue {self.key} is mandatory but missing from config")

        value = get_config_provider().get_config(context).get(*self.key.split(","), default=self.default)
        if value and self.after:
            return self.after(value)
        return value

    @staticmethod
    def create_field(key: str, default: Any = None, description: str = None) -> Any:
        """Create a field for a dataclass that will be resolved from the configuration file"""
        return field(default_factory=lambda: ConfigValue(key=key, default=default, description=description).resolve())  # pylint: disable=invalid-field-call


class ConfigStore:
    """A class to manage configuration files and contexts"""

    _instance: "ConfigStore" = None
    _lock = threading.Lock()

    def __init__(self):
        if ConfigStore._instance is not None:
            raise RuntimeError("ConfigStore is a singleton. Use get_instance()")
        self.store: dict[str, Config] = {"default": None}
        self.context: str = "default"

    @classmethod
    def get_instance(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton - useful for testing"""
        with cls._lock:
            cls._instance = None
            # Also reset the provider to singleton when resetting Config Store
            reset_config_provider()

    def is_configured(self, context: str = None) -> bool:
        return isinstance(self.store.get(context or self.context), Config)

    def config(self, context: str = None) -> Config:
        if not self.is_configured(context):
            raise ValueError(f"Config context {self.context} not properly initialized")
        return self.store.get(context or self.context)

    # Convenience class methods for backward compatibility
    @classmethod
    def is_configured_global(cls, context: str = None) -> bool:
        """Check if configuration is available (uses provider layer)"""
        return get_config_provider().is_configured(context)

    @classmethod
    def config_global(cls, context: str = None) -> Config:
        """Get configuration (uses provider layer)"""
        return get_config_provider().get_config(context)

    def resolve(self, value: T | ConfigValue, context: str = None) -> T:
        if not isinstance(value, ConfigValue):
            return value
        return dget(self.config(context), value.key)

    def configure_context(
        self,
        *,
        context: str = "default",
        source: Config | str | dict = None,
        env_filename: str | None = None,
        env_prefix: str = None,
        switch_to_context: bool = True,
    ) -> Self:
        if not self.store.get(context) and not source:
            raise ValueError(f"Config context {context} undefined, cannot initialize")

        if isinstance(source, Config):
            return self._set_config(context=context, cfg=source)

        if not source and isinstance(self.store.get(context), Config):
            return self.store.get(context)

        cfg: Config = Config.load(
            source=source or self.store.get(context),
            context=context,
            env_filename=env_filename,
            env_prefix=env_prefix,
        )

        return self._set_config(context=context, cfg=cfg, switch_to_context=switch_to_context)

    def consolidate(
        self,
        opts: dict[str, Any],
        ignore_keys: set[str] = None,
        context: str = "default",
        section: str = None,
    ) -> Self:

        if not self.store.get(context):
            raise ValueError(f"Config context {context} undefined, cannot consolidate")

        if not section:
            raise ValueError("Config section cannot be undefined, cannot consolidate")

        ignore_keys: set[str] = ignore_keys or set(opts.keys())

        opts = recursive_update(
            opts,
            recursive_filter_dict(
                self.store[context].get(section, {}),
                filter_keys=ignore_keys,
                filter_mode="exclude",
            ),
        )

        self.store[context].data[section] = opts

        return opts

    def _set_config(
        self,
        *,
        context: str = "default",
        cfg: Config | None = None,
        switch_to_context: bool = True,
    ) -> Self:
        if not isinstance(cfg, Config):
            raise ValueError(f"Expected Config, found {type(cfg)}")
        self.store[context] = cfg
        if switch_to_context:
            self.context = context
        return self.store[context]


configure_context = ConfigStore.configure_context


def resolve_arguments(fn_or_cls, args, kwargs):
    """Resolve any ConfigValue arguments in a function or class constructor"""
    kwargs = {
        k: v.default
        for k, v in inspect.signature(fn_or_cls).parameters.items()
        if isinstance(v.default, ConfigValue) and v.default is not inspect.Parameter.empty
    } | kwargs
    args = (a.resolve() if isinstance(a, ConfigValue) else a for a in args)
    for k, v in kwargs.items():
        if isinstance(v, ConfigValue):
            kwargs[k] = v.resolve()
    return args, kwargs


def inject_config(fn_or_cls: T) -> Callable[..., T]:
    @functools.wraps(fn_or_cls)
    def decorated(*args, **kwargs):
        args, kwargs = resolve_arguments(fn_or_cls, args, kwargs)
        return fn_or_cls(*args, **kwargs)

    return decorated
