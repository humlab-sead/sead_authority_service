import json
from openai import AsyncOpenAI
from openai.types.chat.chat_completion import ChatCompletion  # type: ignore

from . import Providers
from src.configuration import ConfigValue

from .provider import LLMProvider

# try:
# except ImportError:
#     class AsyncOpenAI:
#         def __init__(self, *args, **kwargs):
#             raise ImportError("openai package not installed, cannot use OpenAIProvider")


@Providers.register(key="openai")
class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""

    def __init__(self, api_key: str = None, model: str = None):

        api_key: str = api_key or ConfigValue(f"llm.{self.key}.api_key").resolve()
        self.model: str = model or ConfigValue(f"llm.{self.key}.model").resolve()

        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(self, prompt: str, roles: dict[str, str] = None, **kwargs) -> str:
        opts: str = kwargs.get("options", {})
        opts = opts | (ConfigValue(f"llm.{self.key}.options").resolve() or {})
        user_message: dict[str, str] = {
            "role": "user",
            "content": prompt,
        }
        messages: list[dict[str, str]] = (roles or []) + [
            {
                "role": "user",
                "content": prompt,
            },
        ]
        response: ChatCompletion = await self.client.chat.completions.create(model=self.model, messages=messages, **opts)
        return response.choices[0].message.content.lstrip("```json").rstrip("```")

    def get_options_keys(self) -> list[str]:
        return [("temperature", 0.1), ("max_tokens", 4048), ("stream", False)]
