import ruff


make rufffrom typing import Any

from openai import AsyncOpenAI
from openai.types.chat.chat_completion import ChatCompletion

from src.configuration import ConfigValue

from . import Providers
from .provider import LLMProvider

# try:
# except ImportError:
#     class AsyncOpenAI:
#         def __init__(self, *args, **kwargs):
#             raise ImportError("openai package not installed, cannot use OpenAIProvider")


@Providers.register(key="openai")
class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:

        api_key = api_key or ConfigValue(f"llm.{self.key}.api_key").resolve() or ""
        self.model: str = model or ConfigValue(f"llm.{self.key}.model").resolve() or ""

        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(self, prompt: str, roles: dict[str, str] | None = None, **kwargs) -> str:
        opts: dict[str, Any] = kwargs.get("options", {})
        opts = opts | (ConfigValue(f"llm.{self.key}.options").resolve() or {})

        messages: list[dict[str, Any]] = self.generate_message_list(prompt, roles)
        response: ChatCompletion = await self.client.chat.completions.create(model=self.model, messages=messages, **opts)  # type: ignore
        return response.choices[0].message.content.lstrip("```json").rstrip("```")  # type: ignore

    def get_options_keys(self) -> list[tuple[str, Any]]:
        return [("temperature", 0.1), ("max_tokens", 4048), ("stream", False)]
