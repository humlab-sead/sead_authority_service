# from src.configuration.inject import ConfigValue

# from . import Providers
# from .provider import LLMProvider

# try:
#     import anthropic  # type: ignore
# except ImportError:

#     def _AnthropicX(self, *args, **kwargs):  # pylint: disable=invalid-name
#         raise ImportError("anthropic package not installed, cannot use AnthropicProvider")

#     anthropic = object()
#     anthropic.Anthropic = _AnthropicX


# # @Providers.register(key="anthropic")
# class AnthropicProvider(LLMProvider):
#     """Anthropic Claude API provider"""

#     def __init__(self, api_key: str, model: str = None):
#         self.client = anthropic.Anthropic(api_key=api_key)
#         self.model: str = model or ConfigValue("llm.anthropic.model").resolve()

#     async def complete(self, prompt: str, **kwargs) -> str:
#         max_tokens: int = kwargs.get("max_tokens", ConfigValue("llm.anthropic.options.max_tokens").resolve())
#         temperature: float = kwargs.get("temperature", ConfigValue("llm.anthropic.options.temperature").resolve())
#         response = await self.client.messages.create(
#             model=self.model,
#             messages=[{"role": "user", "content": prompt}],
#             max_tokens=max_tokens,
#             temperature=temperature,
#         )
#         return response.content[0].text
