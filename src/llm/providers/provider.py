"""
LLM Client abstraction supporting multiple providers
"""

from abc import ABC, abstractmethod

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


class ProviderRegistry(Registry):

    items: dict[str, LLMProvider] = {}
