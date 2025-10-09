try:

    from openai import AsyncOpenAI  # type: ignore

except ImportError:

    class AsyncOpenAI:
        def __init__(self, *args, **kwargs):
            raise ImportError("openai package not installed, cannot use OpenAIProvider")


from src.configuration.inject import ConfigValue

from . import Providers
from .provider import LLMProvider


@Providers.register(key="openai")
class OpenAIProvider(LLMProvider):
    """OpenAI API provider"""

    def __init__(self, api_key: str, model: str = None):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model: str = model or ConfigValue("llm.openai.model").resolve()

    async def complete(self, prompt: str, **kwargs) -> str:
        max_tokens: int = kwargs.get("max_tokens", ConfigValue("llm.openai.options.max_tokens").resolve())
        temperature: float = kwargs.get("temperature", ConfigValue("llm.openai.options.temperature").resolve())
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
