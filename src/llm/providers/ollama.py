from typing import Any

import httpx
import ollama
from pydantic import BaseModel

from src.configuration import ConfigValue

from . import Providers
from .provider import LLMProvider


@Providers.register(key="ollama")
class OllamaProvider(LLMProvider):
    """Ollama local LLM provider"""

    def __init__(self, host: str = None, model: str = None) -> None:
        self.host: str = host or ConfigValue(f"llm.{self.key}.host").resolve()
        self.model: str = model or ConfigValue(f"llm.{self.key}.model").resolve()
        self.timeout: int = ConfigValue(f"llm.{self.key}.timeout", default=30).resolve()
        self.client: ollama.Client = ollama.Client(host=self.host, timeout=self.timeout, follow_redirects=True)

    async def complete(self, prompt: str, roles: dict[str, str] = None, **kwargs) -> str:
        # prompt: the prompt to generate a response for
        # suffix: the text after the model response
        # images: (optional) a list of base64-encoded images (for multimodal models such as llava)
        # think: (for thinking models) should the model think before responding?
        # Advanced parameters (optional):
        #   format: the format to return a response in. Format can be json or a JSON schema
        #   options: additional model parameters listed in the documentation for the Modelfile such as temperature
        #   system: system message to (overrides what is defined in the Modelfile)
        #   template: the prompt template to use (overrides what is defined in the Modelfile)
        #   stream: if false the response will be returned as a single response object, rather than a stream of objects
        #   raw: if true no formatting will be applied to the prompt. You may choose to use the raw parameter if you are
        #         specifying a full templated prompt in your request to the API
        #   keep_alive: controls how long the model will stay loaded into memory following the request (default: 5m)
        #   context (deprecated): the context parameter returned from a previous request to /generate, this can be used to keep a short conversational memory
        response_model: type[BaseModel] | None = None
        response_format: dict | None = None
        user_message: dict[str, str] = {
            "role": "user",
            "content": prompt,
        }
        args: dict[str, Any] = {
            "model": self.model,
            "messages": [user_message] + (roles or []),
            "options": self.resolve_options(kwargs),
        }

        if bool(kwargs.get("response_model")) or bool(kwargs.get("format")):
            if bool(kwargs.get("response_model")):
                if not issubclass(kwargs["response_model"], BaseModel):
                    raise ValueError("response_model must be a pydantic BaseModel subclass")
                response_model = kwargs["response_model"]
                response_format = response_model.model_json_schema()
            elif bool(kwargs.get("format")):
                response_format = kwargs["format"]
            args["format"] = response_format

        response: httpx.Response = await ollama.AsyncClient().chat(**args)

        if response_model:
            return response_model.model_validate_json(response.message.content)

        return response.json()["response"]

    def get_options_keys(self) -> list[str]:
        return [("max_tokens", 1024), ("temperature", 0.1)]
