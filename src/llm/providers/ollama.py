import json
from typing import Any

import ollama

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
        # response_model: type[BaseModel] | None = None
        # response_format: dict | None = None
        user_message: dict[str, str] = {
            "role": "user",
            "content": prompt,
        }
        args: dict[str, Any] = {
            "model": self.model,
            "messages": (roles or []) + [user_message],
            "options": self.resolve_options(kwargs),
            "stream": False,
        }

        # if bool(kwargs.get("response_model")) or bool(kwargs.get("format")):
        #     if bool(kwargs.get("response_model")):
        #         if not issubclass(kwargs["response_model"], BaseModel):
        #             raise ValueError("response_model must be a pydantic BaseModel subclass")
        #         response_model = kwargs["response_model"]
        #         response_format = response_model.model_json_schema()
        #     elif bool(kwargs.get("format")):
        #         response_format = kwargs["format"]
        #     args["format"] = response_format

        args["format"] = "json"

        with open("tmp/ollama_args.json", "w", encoding="utf-8") as f:
            json.dump(args, f, indent=2)

        with open("tmp/ollama_prompt.txt", "w", encoding="utf-8") as f:
            f.write(prompt)

        response: ollama.ChatResponse = await ollama.AsyncClient().chat(**args)
        message: ollama.Message = response.message

        with open("tmp/ollama_response.json", "w", encoding="utf-8") as f:
            json.dump(response.model_dump_json(), f, indent=2)

        # if response_model:
        #     return response_model.model_validate_json(response.message.content)

        return message.model_dump_json()

    def get_options_keys(self) -> list[str]:
        return [("temperature", 0.1), ("num_predict", 4096), ("stream", False)]
        # ("max_tokens", 1024), ("top_k", 40), ("top_p", 0.7), ("repeat_penalty", 1.1)]
