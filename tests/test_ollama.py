"""
Unit tests for OllamaProvider LLM implementation.
"""

import asyncio
import os
from unittest.mock import AsyncMock, Mock, patch

from configuration.setup import setup_config_store
import httpx
import pytest
from pydantic import BaseModel

from src.configuration.inject import MockConfigProvider, get_config_provider
from src.llm.providers.ollama import OllamaProvider
from tests.decorators import with_test_config


class TestResponseModel(BaseModel):
    """Test Pydantic model for typed responses"""

    answer: str
    confidence: float


class TestOllamaProvider:

    # @with_test_config
    def test_init_with_defaults(self): #, test_provider: MockConfigProvider):
        """Test OllamaProvider initialization with default configuration"""
        # Set up mock configuration

        os.environ["CONFIG_FILE"] = "./tests/config.yml"
        os.environ["ENV_FILE"] = "./tests/.env"
        asyncio.run(setup_config_store("./tests/config.yml"))
        
        #get_config_provider().get_config().update({"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30}}})

        with patch("ollama.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            provider = OllamaProvider()

            assert provider.base_url == "http://localhost:11434"
            assert provider.model == "llama2"
            assert provider.client == mock_client
            mock_client_class.assert_called_once_with(base_url="http://localhost:11434", timeout=30)

    @with_test_config
    def test_init_with_parameters(self, test_provider: MockConfigProvider):
        """Test OllamaProvider initialization with explicit parameters"""
        # Set up mock configuration (fallback values)
        #test_provider.get_config().update({"llm": {"ollama": {"base_url": "http://default:11434", "model": "default_model", "timeout": 30}}})

        with patch("ollama.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            provider = OllamaProvider(base_url="http://custom:8080", model="custom_model")

            assert provider.base_url == "http://custom:8080"
            assert provider.model == "custom_model"
            mock_client_class.assert_called_once_with(base_url="http://custom:8080", timeout=30)

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_basic(self, test_provider: MockConfigProvider):
        """Test basic completion without typed response"""
        # Set up mock configuration
        test_provider.set_config(
            {"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30, "options": {"max_tokens": 1000, "temperature": 0.7}}}}
        )

        with patch("ollama.Client"), patch("ollama.AsyncClient") as mock_async_client_class:

            # Mock the async client and response
            mock_async_client = Mock()
            mock_async_client_class.return_value = mock_async_client

            mock_response = Mock()
            mock_response.json.return_value = {"response": "Test completion result"}
            mock_async_client.chat = AsyncMock(return_value=mock_response)

            provider = OllamaProvider()
            result = await provider.complete("Test prompt")

            assert result == "Test completion result"

            # Verify the chat call
            mock_async_client.chat.assert_called_once_with(
                model="llama2", messages=[{"role": "user", "content": "Test prompt"}], options={"max_tokens": 1000, "temperature": 0.7}
            )

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_with_custom_options(self, test_provider: MockConfigProvider):
        """Test completion with custom options passed via kwargs"""
        test_provider.set_config(
            {"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30, "options": {"max_tokens": 1000, "temperature": 0.7}}}}
        )

        with patch("ollama.Client"), patch("ollama.AsyncClient") as mock_async_client_class:

            mock_async_client = Mock()
            mock_async_client_class.return_value = mock_async_client

            mock_response = Mock()
            mock_response.json.return_value = {"response": "Custom result"}
            mock_async_client.chat = AsyncMock(return_value=mock_response)

            provider = OllamaProvider()
            result = await provider.complete("Test prompt", max_tokens=500, temperature=0.2)

            assert result == "Custom result"

            # Verify custom options were used
            mock_async_client.chat.assert_called_once_with(
                model="llama2", messages=[{"role": "user", "content": "Test prompt"}], options={"max_tokens": 500, "temperature": 0.2}
            )

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_with_explicit_options(self, test_provider: MockConfigProvider):
        """Test completion with explicit options dictionary"""
        test_provider.set_config({"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30}}})

        with patch("ollama.Client"), patch("ollama.AsyncClient") as mock_async_client_class:

            mock_async_client = Mock()
            mock_async_client_class.return_value = mock_async_client

            mock_response = Mock()
            mock_response.json.return_value = {"response": "Explicit options result"}
            mock_async_client.chat = AsyncMock(return_value=mock_response)

            provider = OllamaProvider()
            custom_options = {"num_predict": 100, "top_k": 40, "top_p": 0.9}

            result = await provider.complete("Test prompt", options=custom_options)

            assert result == "Explicit options result"

            # Verify explicit options were used
            mock_async_client.chat.assert_called_once_with(model="llama2", messages=[{"role": "user", "content": "Test prompt"}], options=custom_options)

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_with_typed_response(self, test_provider: MockConfigProvider):
        """Test completion with Pydantic model for typed response"""
        test_provider.set_config(
            {"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30, "options": {"max_tokens": 1000, "temperature": 0.1}}}}
        )

        with patch("ollama.Client"), patch("ollama.AsyncClient") as mock_async_client_class:

            mock_async_client = Mock()
            mock_async_client_class.return_value = mock_async_client

            # Mock response with message.content for typed response
            mock_response = Mock()
            mock_response.message.content = '{"answer": "Test answer", "confidence": 0.95}'
            mock_async_client.chat = AsyncMock(return_value=mock_response)

            provider = OllamaProvider()
            result = await provider.complete("Test prompt", response_model=TestResponseModel)

            assert isinstance(result, TestResponseModel)
            assert result.answer == "Test answer"
            assert result.confidence == 0.95

            # Verify the schema was passed for formatting
            expected_schema = TestResponseModel.model_json_schema()
            mock_async_client.chat.assert_called_once()
            call_args = mock_async_client.chat.call_args[1]
            assert call_args["format"] == expected_schema

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_typed_response_invalid_model(self, test_provider: MockConfigProvider):
        """Test completion with invalid response_model raises ValueError"""
        test_provider.set_config({"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30}}})

        with patch("ollama.Client"):
            provider = OllamaProvider()

            # Test with non-BaseModel class
            with pytest.raises(ValueError, match="response_model must be a pydantic BaseModel subclass"):
                await provider.complete("Test prompt", response_model=dict)  # Invalid: not a BaseModel

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_network_error_handling(self, test_provider: MockConfigProvider):
        """Test that network errors are properly propagated"""
        test_provider.set_config(
            {"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30, "options": {"max_tokens": 1000, "temperature": 0.7}}}}
        )

        with patch("ollama.Client"), patch("ollama.AsyncClient") as mock_async_client_class:

            mock_async_client = Mock()
            mock_async_client_class.return_value = mock_async_client

            # Simulate network error
            mock_async_client.chat = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))

            provider = OllamaProvider()

            with pytest.raises(httpx.ConnectError):
                await provider.complete("Test prompt")

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_malformed_json_response(self, test_provider: MockConfigProvider):
        """Test handling of malformed JSON response"""
        test_provider.set_config(
            {"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30, "options": {"max_tokens": 1000, "temperature": 0.7}}}}
        )

        with patch("ollama.Client"), patch("ollama.AsyncClient") as mock_async_client_class:

            mock_async_client = Mock()
            mock_async_client_class.return_value = mock_async_client

            # Mock response with invalid JSON
            mock_response = Mock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_async_client.chat = AsyncMock(return_value=mock_response)

            provider = OllamaProvider()

            with pytest.raises(ValueError):
                await provider.complete("Test prompt")

    @with_test_config
    def test_key_property(self, test_provider: MockConfigProvider):
        """Test that the provider has the correct key property"""
        test_provider.set_config({"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30}}})

        with patch("ollama.Client"):
            provider = OllamaProvider()
            # Assuming the provider inherits key from registration
            assert hasattr(provider, "key")
            # The key should be set by the @Providers.register("ollama") decorator

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_empty_prompt(self, test_provider: MockConfigProvider):
        """Test completion with empty prompt"""
        test_provider.set_config(
            {"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30, "options": {"max_tokens": 1000, "temperature": 0.7}}}}
        )

        with patch("ollama.Client"), patch("ollama.AsyncClient") as mock_async_client_class:

            mock_async_client = Mock()
            mock_async_client_class.return_value = mock_async_client

            mock_response = Mock()
            mock_response.json.return_value = {"response": "Empty response"}
            mock_async_client.chat = AsyncMock(return_value=mock_response)

            provider = OllamaProvider()
            result = await provider.complete("")

            assert result == "Empty response"

            # Verify empty prompt was passed correctly
            mock_async_client.chat.assert_called_once_with(
                model="llama2", messages=[{"role": "user", "content": ""}], options={"max_tokens": 1000, "temperature": 0.7}
            )

    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_long_prompt(self, test_provider: MockConfigProvider):
        """Test completion with very long prompt"""
        test_provider.set_config(
            {"llm": {"ollama": {"base_url": "http://localhost:11434", "model": "llama2", "timeout": 30, "options": {"max_tokens": 1000, "temperature": 0.7}}}}
        )

        with patch("ollama.Client"), patch("ollama.AsyncClient") as mock_async_client_class:

            mock_async_client = Mock()
            mock_async_client_class.return_value = mock_async_client

            mock_response = Mock()
            mock_response.json.return_value = {"response": "Long response"}
            mock_async_client.chat = AsyncMock(return_value=mock_response)

            provider = OllamaProvider()
            long_prompt = "This is a very long prompt. " * 1000  # ~30k characters

            result = await provider.complete(long_prompt)

            assert result == "Long response"

            # Verify long prompt was handled correctly
            call_args = mock_async_client.chat.call_args[1]
            assert call_args["messages"][0]["content"] == long_prompt
