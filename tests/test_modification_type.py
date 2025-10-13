"""Test for modification type LLM reconciliation strategy"""

from unittest.mock import AsyncMock, patch

import pytest

from src.configuration.inject import MockConfigProvider
from src.strategies.llm_models import Candidate, ReconciliationResponse, ReconciliationResult
from src.strategies.modification_type import SPECIFICATION, LLMModificationTypeReconciliationStrategy
from src.strategies.strategy import ReconciliationStrategy
from tests.decorators import with_test_config

# pylint: disable=unused-argument


class TestModificationTypeReconciliationStrategy:
    """Test LLM-based modification type reconciliation"""

    @with_test_config
    def test_initialization(self, test_provider: MockConfigProvider):
        """Test strategy initialization"""
        strategy = LLMModificationTypeReconciliationStrategy()

        assert strategy.specification == SPECIFICATION
        assert strategy.get_entity_id_field() == "modification_type_id"
        assert strategy.get_label_field() == "modification_type_name"
        assert strategy.get_id_path() == "modification_type"

    @with_test_config
    def test_context_description(self, test_provider: MockConfigProvider):
        """Test context description for LLM"""
        strategy: LLMModificationTypeReconciliationStrategy = LLMModificationTypeReconciliationStrategy()
        context: str = strategy.get_context_description()

        assert context.startswith("You are provided")

    @with_test_config
    @pytest.mark.asyncio
    async def test_get_lookup_data(self, test_provider: MockConfigProvider):
        """Test fetching lookup data from database"""
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [
            {"modification_type_id": 1, "modification_type_name": "Carbonised", "modification_type_description": "Organic matter converted to carbon"},
            {"modification_type_id": 2, "modification_type_name": "Calcified", "modification_type_description": "Organic matter replaced by calcium"},
        ]

        strategy: ReconciliationStrategy = LLMModificationTypeReconciliationStrategy()
        lookup_data = await strategy.get_lookup_data(mock_cursor)

        assert len(lookup_data) == 2
        assert lookup_data[0]["modification_type_name"] == "Carbonised"
        assert lookup_data[1]["modification_type_name"] == "Calcified"

    @with_test_config
    def test_format_lookup_data(self, test_provider: MockConfigProvider):
        """Test formatting lookup data for LLM prompt"""
        strategy = LLMModificationTypeReconciliationStrategy()

        lookup_data = [
            {"modification_type_id": 1, "modification_type_name": "Carbonised", "modification_type_description": "Organic matter converted to carbon"},
            {"modification_type_id": 2, "modification_type_name": "Calcified", "modification_type_description": "Organic matter replaced by calcium"},
        ]

        formatted: str = strategy.format_lookup_data(lookup_data)
        lines: list[str] = formatted.split("\n")

        assert len(lines) == 2
        assert "1, Carbonised, Organic matter converted to carbon" in lines[0]
        assert "2, Calcified, Organic matter replaced by calcium" in lines[1]

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_with_llm_success(self, test_provider: MockConfigProvider):
        """Test successful LLM-based candidate finding"""

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

        # Mock database data
        mock_cursor = AsyncMock()
        mock_cursor.fetchall.return_value = [
            {"modification_type_id": 1, "modification_type_name": "Carbonised", "modification_type_description": "Organic matter converted to carbon"}
        ]

        mock_llm = AsyncMock()
        mock_llm.complete.return_value = mock_response
        mock_llm.key = "ollama"

        from src.llm.providers import Providers # pylint: disable=import-outside-toplevel

        #with patch.object(Providers, "items", {"ollama": lambda: mock_llm}): # this works as well
        original_items = Providers.items.copy()
        
        try:
            # Directly modify the registry
            Providers.items["ollama"] = lambda: mock_llm
        
            strategy = LLMModificationTypeReconciliationStrategy()
            candidates = await strategy.find_candidates(mock_cursor, "charred")

            assert len(candidates) == 2
            assert candidates[0]["modification_type_id"] == "1"
            assert candidates[0]["modification_type_name"] == "Carbonised"
            assert candidates[0]["name_sim"] == 0.92
            assert candidates[0]["llm_reasons"] == ["Similar process", "Both involve heating", "Carbon formation"]
        finally:
            # Restore original items
            Providers.items = original_items

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_with_llm_fallback(self, test_provider: MockConfigProvider):
        """Test fallback to traditional matching when LLM fails"""

        mock_cursor = AsyncMock()

        # Mock database lookup data call to fail (simulating LLM failure)
        mock_cursor.fetchall.side_effect = [Exception("LLM failed"), [{"modification_type_id": 1, "modification_type_name": "Carbonised", "name_sim": 0.8}]]

        # with patch("src.strategies.llm.llm_strategy.Providers") as mock_providers:
        with patch("src.llm.providers.Providers") as mock_providers:
            mock_llm = AsyncMock()
            mock_llm.complete.side_effect = Exception("LLM service unavailable")
            mock_providers.items = {"ollama": lambda: mock_llm}

            # Mock the parent class method
            with patch.object(LLMModificationTypeReconciliationStrategy.__bases__[0], "find_candidates") as mock_parent:
                mock_parent.return_value = [{"modification_type_id": 1, "modification_type_name": "Carbonised", "name_sim": 0.8}]

                strategy = LLMModificationTypeReconciliationStrategy()
                candidates = await strategy.find_candidates(mock_cursor, "charred")

                # Should fall back to parent implementation
                mock_parent.assert_called_once()
                assert len(candidates) == 1
                assert candidates[0]["modification_type_name"] == "Carbonised"
