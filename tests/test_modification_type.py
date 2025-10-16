"""Test for modification type LLM reconciliation strategy"""

import sys
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from loguru import logger
from psycopg import AsyncConnection

from src.configuration import SingletonConfigProvider, get_config_provider, get_connection
from src.configuration.interface import ConfigLike
from src.configuration.provider import ConfigProvider
from src.strategies.strategy import ReconciliationStrategy
from strategies.llm.llm_models import Candidate, ReconciliationResponse, ReconciliationResult
from strategies.llm.modification_type import SPECIFICATION, LLMModificationTypeReconciliationStrategy
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config

# pylint: disable=unused-argument, import-outside-toplevel

logger.remove()
logger.add(sys.stderr, diagnose=True)


class TestModificationTypeReconciliationStrategy:
    """Test LLM-based modification type reconciliation"""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test that uses production config and external LLM service")
    async def test_using_production(self):
        """Test that production config is not used in tests"""
        import os

        from src.configuration import setup_config_store

        os.environ["CONFIG_FILE"] = "./config/config.yml"
        os.environ["ENV_FILE"] = ".env"
        await setup_config_store("./config/config.yml", force=True)

        strategy: ReconciliationStrategy = LLMModificationTypeReconciliationStrategy()
        assert strategy.specification.get("key") == "modification_type"
        assert strategy.key == "modification_type"

        provider: ConfigProvider = get_config_provider()
        assert isinstance(provider, SingletonConfigProvider)

        assert provider.is_configured()
        config: ConfigLike = provider.get_config()

        assert config.exists("runtime")
        assert not config.exists("connection_factory")

        _: AsyncConnection[tuple[Any, ...]] = await get_connection()

        assert config.exists("runtime:connection")

        os.environ["OLLAMA_HOST"] = config.get("llm.ollama.host")
        os.environ["OLLAMA_MODEL"] = config.get("llm.ollama.model")
        os.environ["OLLAMA_TIMEOUT"] = str(config.get("llm.ollama.timeout", default=30))

        #         # Test with a simple direct LLM call to debug JSON generation
        #         from src.llm.providers import Providers
        #         provider_class = Providers.get("ollama")
        #         provider = provider_class()  # Create instance

        #         simple_prompt = '''Generate JSON array for reconciliation task.
        #         simple_response = await provider.complete(simple_prompt)
        #         print(f"Simple response: {simple_response}")

        #         import json
        #         try:
        #             json.loads(simple_response)
        #             print("Simple JSON parsing: SUCCESS")
        #         except json.JSONDecodeError as e:
        #             print(f"Simple JSON parsing: FAILED - {e}")
        #             print(f"Response was: {simple_response[:200]}...")

        candidates: list[dict[str, Any]] = await strategy.find_candidates(
            query="Carbonised", properties={"description": "Organic matter converted to carbon"}, limit=5
        )
        assert isinstance(candidates, list)

    @with_test_config
    def test_initialization(self, test_provider: ExtendedMockConfigProvider):
        """Test strategy initialization"""
        strategy = LLMModificationTypeReconciliationStrategy()

        assert strategy.specification == SPECIFICATION
        assert strategy.get_entity_id_field() == "modification_type_id"
        assert strategy.get_label_field() == "modification_type_name"
        assert strategy.get_id_path() == "modification_type"

    @with_test_config
    def test_context_description(self, test_provider: ExtendedMockConfigProvider):
        """Test context description for LLM"""
        strategy: LLMModificationTypeReconciliationStrategy = LLMModificationTypeReconciliationStrategy()
        context: str = strategy.get_context_description()

        assert context.startswith("You are provided")

    @with_test_config
    @pytest.mark.asyncio
    async def test_get_lookup_data(self, test_provider: ExtendedMockConfigProvider):
        """Test fetching lookup data from database"""
        mock_data = [
            {"modification_type_id": 1, "modification_type_name": "Carbonised", "modification_type_description": "Organic matter converted to carbon"},
            {"modification_type_id": 2, "modification_type_name": "Calcified", "modification_type_description": "Organic matter replaced by calcium"},
        ]
        test_provider.create_connection_mock(fetchall=mock_data)

        strategy: ReconciliationStrategy = LLMModificationTypeReconciliationStrategy()
        lookup_data = await strategy.get_lookup_data()

        assert len(lookup_data) == 2
        assert lookup_data[0]["modification_type_name"] == "Carbonised"
        assert lookup_data[1]["modification_type_name"] == "Calcified"

    @with_test_config
    def test_format_lookup_data(self, test_provider: ExtendedMockConfigProvider):
        """Test formatting lookup data for LLM prompt"""
        strategy: LLMModificationTypeReconciliationStrategy = LLMModificationTypeReconciliationStrategy()

        lookup_data = [
            {"modification_type_id": 1, "modification_type_name": "Carbonised", "modification_type_description": "Organic matter converted to carbon"},
            {"modification_type_id": 2, "modification_type_name": "Calcified", "modification_type_description": "Organic matter replaced by calcium"},
        ]

        test_provider.create_connection_mock(fetchall=lookup_data)

        formatted: str = strategy.format_lookup_data(lookup_data)
        lines: list[str] = formatted.split("\n")

        assert len(lines) == 2
        assert "1, Carbonised, Organic matter converted to carbon" in lines[0]
        assert "2, Calcified, Organic matter replaced by calcium" in lines[1]

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_with_llm_success(self, test_provider: ExtendedMockConfigProvider):
        """Test successful LLM-based candidate finding"""

        # Configure the test to use ollama provider with required settings
        test_provider.get_config().update({"llm": {"provider": "ollama", "prompts": {"reconciliation": "Find matches for {{ query }} in: {{ lookup_data }}"}}})

        # Mock the LLM response
        mock_response = ReconciliationResponse(
            results=[
                ReconciliationResult(
                    input_id="1",
                    input_value="charred",
                    candidates=[
                        Candidate(id="1", value="Carbonised", score=0.92, reasons=["Similar process", "Both involve heating", "Carbon formation"]),
                        Candidate(id="8", value="Petrified", score=0.15, reasons=["Different process", "Stone formation"]),
                    ],
                )
            ]
        )

        test_provider.create_connection_mock(
            fetchall=[
                {
                    "modification_type_id": 1,
                    "modification_type_name": "Carbonised",
                    "modification_type_description": "Organic matter converted to carbon",
                }
            ],
        )

        mock_llm = AsyncMock()
        # Return just the results array as expected by the _response_to_candidates method
        import json

        mock_llm.complete.return_value = json.dumps([result.model_dump() for result in mock_response.results])
        mock_llm.key = "ollama"

        from src.llm.providers import Providers  # pylint: disable=import-outside-toplevel

        # Use patch.object to properly mock the Providers registry
        with patch.object(Providers, "items", {"ollama": lambda: mock_llm}):
            strategy = LLMModificationTypeReconciliationStrategy()
            candidates = await strategy.find_candidates("charred")

            assert len(candidates) == 2
            assert candidates[0]["modification_type_id"] == "1"
            assert candidates[0]["modification_type_name"] == "Carbonised"
            assert candidates[0]["name_sim"] == 0.92
            assert candidates[0]["llm_reasons"] == ["Similar process", "Both involve heating", "Carbon formation"]

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_with_llm_fallback(self, test_provider: ExtendedMockConfigProvider):
        """Test fallback to traditional matching when LLM fails"""

        test_provider.create_connection_mock(
            fetchone=Exception("LLM failed"), fetchall=[{"modification_type_id": 1, "modification_type_name": "Carbonised", "name_sim": 0.8}]
        )

        # with patch("src.strategies.llm.llm_strategy.Providers") as mock_providers:
        with patch("src.llm.providers.Providers") as mock_providers:
            mock_llm = AsyncMock()
            mock_llm.complete.side_effect = Exception("LLM service unavailable")
            mock_providers.items = {"ollama": lambda: mock_llm}

            # Mock the parent class method
            with patch.object(LLMModificationTypeReconciliationStrategy.__bases__[0], "find_candidates") as mock_parent:
                mock_parent.return_value = [{"modification_type_id": 1, "modification_type_name": "Carbonised", "name_sim": 0.8}]

                strategy = LLMModificationTypeReconciliationStrategy()
                candidates = await strategy.find_candidates("charred")

                # Should fall back to parent implementation
                mock_parent.assert_called_once()
                assert len(candidates) == 1
                assert candidates[0]["modification_type_name"] == "Carbonised"
