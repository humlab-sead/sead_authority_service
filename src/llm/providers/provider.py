"""
LLM Client abstraction supporting multiple providers
"""

from abc import ABC, abstractmethod
from typing import Any

from src.configuration import ConfigValue
from src.utility import Registry


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    _registry_key: str = "undefined"

    @property
    def key(self) -> str:
        return getattr(self, "_registry_key", "undefined")

    @abstractmethod
    async def complete(self, prompt: str, roles: dict[str, str] = None, **kwargs) -> str:
        pass

    @abstractmethod
    def get_options_keys(self) -> list[str]:
        """Return a list of supported option keys and their default values"""

    def resolve_options(self, kwargs) -> dict[str, Any]:
        opts: dict[str, Any] = kwargs.get("options", {})
        for k, default in self.get_options_keys():
            if k in opts:
                continue
            if k in kwargs:
                opts[k] = kwargs[k]
                continue
            opts[k] = ConfigValue(f"llm.{self.key}.options.{k},llm.options.{k}", default=default).resolve()
        return opts


class ProviderRegistry(Registry):

    items: dict[str, LLMProvider] = {}
