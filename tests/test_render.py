from typing import LiteralString
from unittest.mock import AsyncMock, patch

from configuration.inject import ConfigProvider
import pytest

from src.configuration.inject import ConfigStore, ConfigValue, MockConfigProvider, set_config_provider, reset_config_provider
from src.configuration.config import Config
from src.render import render_preview
from tests.conftest import mock_strategy_with_get_details
from tests.decorators import with_test_config

ID_BASE = "https://w3id.org/sead/id/"

# pylint: disable=attribute-defined-outside-init,protected-access, redefined-outer-name


GET_DETAILS_DATA: dict[str, dict[str, str]] = {
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
    "notfound": None
}



class TestRenderPreview:
    """Test cases for render_preview function"""

    @pytest.mark.asyncio
    @with_test_config
    async def test_successful_render_with_name(self, test_provider: MockConfigProvider):
        """Test successful rendering when entity has 'Name' field"""
        uri: LiteralString = f"{ID_BASE}site/123"

        # Mock the Strategies to use our test strategy
        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy = AsyncMock()
            mock_strategy.get_details.return_value = GET_DETAILS_DATA["123"]
            mock_strategies.items.get.return_value = lambda: mock_strategy
            result = await render_preview(uri)

        assert isinstance(result, str)
        assert "<h3 style='margin-top:0;'>Test Site</h3>" in result
        assert "<strong style='color:#333; min-width:100px; display:inline-block;'>Name:</strong>" in result
        assert "<span>Test Site</span>" in result
        assert "<strong style='color:#333; min-width:100px; display:inline-block;'>latitude:</strong>" in result
        assert "<span>59.8586</span>" in result
        assert "<strong style='color:#333; min-width:100px; display:inline-block;'>country:</strong>" in result
        assert "<span>Sweden</span>" in result

    @pytest.mark.asyncio
    @with_test_config
    async def test_successful_render_with_label_fallback(self, test_provider):
        """Test rendering when entity has 'label' but no 'Name' field"""
        uri = f"{ID_BASE}site/456"
        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy = AsyncMock()
            mock_strategy.get_details.return_value = GET_DETAILS_DATA["456"]
            mock_strategies.items.get.return_value = lambda: mock_strategy
            result = await render_preview(uri)

        assert isinstance(result, str)
        assert "<h3 style='margin-top:0;'>Site Without Name</h3>" in result

    @pytest.mark.asyncio
    @with_test_config
    async def test_render_filters_empty_values(self, test_provider):
        """Test that None, empty strings, and whitespace-only values are filtered out"""
        uri = f"{ID_BASE}site/789"
        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy = AsyncMock()
            mock_strategy.get_details.return_value = GET_DETAILS_DATA["789"]
            mock_strategies.items.get.return_value = lambda: mock_strategy
            result = await render_preview(uri)

        assert isinstance(result, str)
        # Should include field1 and field5
        assert "<strong style='color:#333; min-width:100px; display:inline-block;'>field1:</strong>" in result
        assert "<span>Value 1</span>" in result
        assert "<strong style='color:#333; min-width:100px; display:inline-block;'>field5:</strong>" in result
        assert "<span>Valid Value</span>" in result

        # Should NOT include field2 (None), field3 (empty), field4 (whitespace only)
        assert "field2:" not in result
        assert "field3:" not in result
        assert "field4:" not in result

    @pytest.mark.asyncio
    @with_test_config
    async def test_invalid_id_format(self, test_provider):
        """Test error when URI doesn't start with id_base"""
        # Use wrong URI that doesn't match the configured id_base
        uri = "https://wrong-domain.org/sead/site/123"
        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, GET_DETAILS_DATA["123"])
            with pytest.raises(ValueError, match="Invalid ID format"):
                await render_preview(uri)
        
    @pytest.mark.asyncio
    @with_test_config
    async def test_invalid_id_path_too_few_parts(self, test_provider):
        """Test error when URI path has insufficient parts"""
        uri: str = f"{ID_BASE}site"  # Missing entity ID

        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, {})
            with pytest.raises(ValueError, match="Invalid ID path"):
                await render_preview(uri)
        
    @pytest.mark.asyncio
    @with_test_config
    async def test_invalid_id_path_too_many_parts(self, test_provider):
        """Test error when URI path has too many parts"""
        uri: str = f"{ID_BASE}site/123/extra"
        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, {})
            with pytest.raises(ValueError, match="Invalid ID path"):
                await render_preview(uri)
        
    @pytest.mark.asyncio
    @with_test_config
    async def test_entity_not_found(self, test_provider):
        """Test error when entity is not found in database"""
        uri = f"{ID_BASE}site/notfound"
        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, GET_DETAILS_DATA["notfound"])
            with pytest.raises(ValueError, match="Entity with ID notfound not found or preview not implemented"):
                await render_preview(uri)
        
    @pytest.mark.asyncio
    @with_test_config
    async def test_html_structure(self, test_provider):
        """Test that generated HTML has correct structure"""
        uri = f"{ID_BASE}site/123"
        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, GET_DETAILS_DATA["123"])
            result = await render_preview(uri)

        # Check main container
        assert result.startswith("<div style='padding:10px; font:14px sans-serif; line-height:1.6;'>")
        assert result.endswith("</div>")

        # Check that it has proper HTML structure
        assert "<h3 style='margin-top:0;'>" in result
        assert "</h3>" in result
        assert "<strong style='color:#333; min-width:100px; display:inline-block;'>" in result
        assert "<span>" in result
        assert "</span>" in result
        
    @pytest.mark.asyncio
    @with_test_config
    async def test_different_entity_types(self, test_provider):
        """Test that different entity types work correctly"""
        # Test with 'taxon' entity type
        uri = f"{ID_BASE}taxon/123"
        with patch("src.render.Strategies") as mock_strategies:
            mock_strategy_with_get_details(mock_strategies, GET_DETAILS_DATA["123"])
            result = await render_preview(uri)

        assert isinstance(result, str)
        assert "<h3 style='margin-top:0;'>Test Site</h3>" in result  # Uses same mock data
        

class TestConfigProvider:
    """Test edge cases and error conditions"""

    @pytest.mark.asyncio
    @with_test_config
    async def test_config_value_resolution(self, test_provider):
        """Test that ConfigValue works with the new provider system"""
        # Test ConfigValue resolution
        id_base_config = ConfigValue("options:id_base")
        
        # This will use the test_provider's configuration
        assert id_base_config.resolve() == "https://w3id.org/sead/id/"

    def test_config_provider_switching(self):
        """Test that we can switch between providers"""
        # Create two different configs
        config1 = Config(data={"test": {"value": "config1"}})
        config2 = Config(data={"test": {"value": "config2"}})

        provider1 = MockConfigProvider(config1)
        provider2 = MockConfigProvider(config2)

        # Test switching providers
        original = set_config_provider(provider1)

        try:
            config_value = ConfigValue("test:value")
            assert config_value.resolve() == "config1"

            # Switch to second provider
            set_config_provider(provider2)
            assert config_value.resolve() == "config2"

            # Switch back
            set_config_provider(provider1)
            assert config_value.resolve() == "config1"

        finally:
            set_config_provider(original)

    def test_singleton_persistence(self):
        """Test that singleton ConfigStore persists across calls"""
        # Configure the singleton
        config = Config(data={"test": "singleton_value"})
        store = ConfigStore.get_instance()
        store.store["default"] = config

        # Get another instance - should be the same
        store2 = ConfigStore.get_instance()
        assert store is store2
        assert store2.config().get("test") == "singleton_value"

        # Reset and verify it's clean
        ConfigStore.reset_instance()
        store3 = ConfigStore.get_instance()
        assert store3 is not store
        assert store3.store["default"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
