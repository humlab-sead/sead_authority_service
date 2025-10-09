from typing import Any

import httpx
import ollama
from pydantic import BaseModel

from src.configuration.inject import ConfigValue

from . import Providers
from .provider import LLMProvider


@Providers.register(key="ollama")
class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""

    def __init__(self, base_url: str = None, model: str = None) -> None:
        self.base_url: str = base_url or ConfigValue(f"llm.{self.key}.base_url").resolve()
        self.model: str = model or ConfigValue(f"llm.{self.key}.model").resolve()
        self.client: ollama.Client = ollama.Client(
            base_url=self.base_url,
            timeout=ConfigValue(f"llm.{self.key}.timeout").resolve(),
        )

    async def complete(self, prompt: str, **kwargs) -> str:

        is_typed_response: bool = bool(kwargs.get("response_model"))
        response_model: type[BaseModel] | None = None

        args: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": prompt},
            ],
        }
        if is_typed_response:
            # verify that model is a pydantic model
            response_model = kwargs["response_model"]
            if not issubclass(response_model, BaseModel):
                raise ValueError("response_model must be a pydantic BaseModel subclass")
            # pass a pydantic model to get typed response
            args["format"] = response_model.model_json_schema()

        if kwargs.get("options"):
            args["options"] = kwargs["options"]
        else:
            max_tokens: int = kwargs.get("max_tokens", ConfigValue(f"llm.{self.key}.options.max_tokens").resolve())
            temperature: float = kwargs.get("temperature", ConfigValue(f"llm.{self.key}.options.temperature").resolve())
            args["options"] = {
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

        response: httpx.Response = await ollama.AsyncClient().chat(**args)

        if is_typed_response and response_model:
            return response_model.model_validate_json(response.message.content)
        return response.json()["response"]
