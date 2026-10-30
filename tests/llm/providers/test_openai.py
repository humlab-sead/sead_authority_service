from unittest.mock import patch

from src.configuration import MockConfigProvider
from src.llm.providers.openai import OpenAIProvider
from tests.decorators import with_test_config


@with_test_config
def test_openai_provider_uses_configured_endpoint(test_provider: MockConfigProvider) -> None:
    test_provider.get_config().update(
        {
            "llm.openai.api_key": "test-key",
            "llm.openai.model": "test-model",
            "llm.openai.base_url": "http://example.test:8081/v1",
        }
    )

    with patch("src.llm.providers.openai.AsyncOpenAI") as client:
        provider = OpenAIProvider()

    assert provider.model == "test-model"
    client.assert_called_once_with(api_key="test-key", base_url="http://example.test:8081/v1")