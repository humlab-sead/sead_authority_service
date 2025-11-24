from typing import Any, LiteralString
from unittest.mock import AsyncMock, patch

import pytest

from src.configuration import MockConfigProvider
from src.preview import render_preview
from tests.conftest import mock_strategy_with_get_details
from tests.decorators import with_test_config

ID_BASE = "https://w3id.org/sead/id/"

# pylint: disable=attribute-defined-outside-init,protected-access, redefined-outer-name, unused-argument


GET_DETAILS_DATA: dict[str, Any] = {
    "123": {
        "Name": "Test Site",
        "label": "Test Site Label",
        "latitude": "59.8586",
        "longitude": "17.6389",
        "country": "Sweden",
        "description": "A test archaeological site",
    },
    "456": {"label": "Site Without Name", "coordinates": "59.85, 17.64", "type": "Settlement"},
    "789": {"field1": "Value 1", "field2": None, "field3": "", "field4": "   ", "field5": "Valid Value"},
    "empty": {},
    "notfound": None,
}


class TestRenderPreview:
    """Test cases for render_preview function"""

    @pytest.mark.asyncio
    @with_test_config
    async def test_successful_render_with_name(self, test_provider: MockConfigProvider):
        """Test successful rendering when entity has 'Name' field"""
        uri: LiteralString = f"{ID_BASE}site/123"

        # Mock the Strategies to use our test strategy
        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy = AsyncMock()
            mock_strategy.get_details.return_value = GET_DETAILS_DATA["123"]
            mock_strategies.items.get.return_value = lambda: mock_strategy
            result = await render_preview(uri)

        assert isinstance(result, str)
        assert "<title>Test Site – Preview</title>" in result
        assert "<h1>Test Site</h1>" in result
        assert '<div class="label">longitude:</div>' in result
        assert '<div class="value">17.6389</div>' in result
        assert '<div class="label">country:</div>' in result
        assert '<div class="value">Sweden</div>' in result

    @pytest.mark.asyncio
    @with_test_config
    async def test_successful_render_with_label_fallback(self, test_provider: MockConfigProvider):
        """Test rendering when entity has 'label' but no 'Name' field"""
        uri = f"{ID_BASE}site/456"
        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy = AsyncMock()
            mock_strategy.get_details.return_value = GET_DETAILS_DATA["456"]
            mock_strategies.items.get.return_value = lambda: mock_strategy
            result = await render_preview(uri)

        assert isinstance(result, str)
        assert "<title>Site Without Name – Preview</title>" in result

    @pytest.mark.asyncio
    @with_test_config
    async def test_render_filters_empty_values(self, test_provider: MockConfigProvider):
        """Test that None, empty strings, and whitespace-only values are filtered out"""
        uri = f"{ID_BASE}site/789"
        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy = AsyncMock()
            mock_strategy.get_details.return_value = GET_DETAILS_DATA["789"]
            mock_strategies.items.get.return_value = lambda: mock_strategy
            result = await render_preview(uri)

        assert isinstance(result, str)
        # Should include field1 and field5
        assert '<div class="label">field1:</div>' in result
        assert '<div class="value">Value 1</div>' in result
        assert '<div class="label">field5:</div>' in result
        assert '<div class="value">Valid Value</div>' in result

        # Should NOT include field2 (None), field3 (empty), field4 (whitespace only)
        assert "field2:" not in result
        assert "field3:" not in result
        assert "field4:" not in result

    @pytest.mark.asyncio
    @with_test_config
    async def test_invalid_id_format(self, test_provider: MockConfigProvider):
        """Test error when URI doesn't start with id_base"""
        # Use wrong URI that doesn't match the configured id_base
        uri = "https://wrong-domain.org/sead/site/123"
        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, GET_DETAILS_DATA["123"])
            with pytest.raises(ValueError, match="Invalid ID format"):
                await render_preview(uri)

    @pytest.mark.asyncio
    @with_test_config
    async def test_invalid_id_path_too_few_parts(self, test_provider: MockConfigProvider):
        """Test error when URI path has insufficient parts"""
        uri: str = f"{ID_BASE}site"  # Missing entity ID

        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, {})
            with pytest.raises(ValueError, match="Invalid ID path"):
                await render_preview(uri)

    @pytest.mark.asyncio
    @with_test_config
    async def test_invalid_id_path_too_many_parts(self, test_provider: MockConfigProvider):
        """Test error when URI path has too many parts"""
        uri: str = f"{ID_BASE}site/123/extra"
        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, {})
            with pytest.raises(ValueError, match="Invalid ID path"):
                await render_preview(uri)

    @pytest.mark.asyncio
    @with_test_config
    async def test_entity_not_found(self, test_provider: MockConfigProvider):
        """Test error when entity is not found in database"""
        uri = f"{ID_BASE}site/notfound"
        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, GET_DETAILS_DATA["notfound"])
            with pytest.raises(ValueError, match="Entity with ID notfound not found or preview not implemented"):
                await render_preview(uri)

    @pytest.mark.asyncio
    @with_test_config
    async def test_html_structure(self, test_provider: MockConfigProvider):
        """Test that generated HTML has correct structure"""
        uri = f"{ID_BASE}site/123"
        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, GET_DETAILS_DATA["123"])
            result = await render_preview(uri)

        assert isinstance(result, str)
        assert result.startswith("<!DOCTYPE html>")
        assert result.endswith("</html>")
        assert "<body>" in result
        assert "</body>" in result

    @pytest.mark.asyncio
    @with_test_config
    async def test_different_entity_types(self, test_provider: MockConfigProvider):
        """Test that different entity types work correctly"""
        # Test with 'taxon' entity type
        uri = f"{ID_BASE}taxon/123"
        with patch("src.preview.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, GET_DETAILS_DATA["123"])
            result = await render_preview(uri)

        assert isinstance(result, str)
        assert "<title>Test Site – Preview</title>" in result  # Uses same mock data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
