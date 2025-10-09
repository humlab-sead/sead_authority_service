"""
LLM Client abstraction supporting multiple providers
"""

from abc import ABC, abstractmethod
from typing import Any

from src.configuration.inject import ConfigValue
from src.utility import Registry


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    _registry_key: str = "undefined"

    @property
    def key(self) -> str:
        return getattr(self, "_registry_key", "undefined")

    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    def get_options_keys(self) -> list[str]:
        """Return a list of supported option keys and their default values"""

    def resolve_options(self, args, kwargs) -> dict[str, Any]:
        opts = kwargs.get("options", {})
        for key, default in self.get_options_keys():
            if key in opts:
                continue
            if key in kwargs:
                args[key] = kwargs[key]
                continue
            opts[key] = ConfigValue(f"llm.{self.key}.options.{key},llm.options.{key}", default=default).resolve()
        return opts


class ProviderRegistry(Registry):

    items: dict[str, LLMProvider] = {}
