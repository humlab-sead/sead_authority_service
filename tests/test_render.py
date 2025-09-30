import pytest
import psycopg
from unittest.mock import AsyncMock, MagicMock, patch

from configuration.inject import ConfigStore
from src.render import render_preview

ID_BASE = "https://w3id.org/sead/id/"

class MockStrategy:
    """Mock strategy for testing"""
    
    async def get_details(self, entity_id: str, cursor):
        """Mock get_details method"""
        if entity_id == "123":
            return {
                "Name": "Test Site",
                "label": "Test Site Label", 
                "latitude": "59.8586",
                "longitude": "17.6389",
                "country": "Sweden",
                "description": "A test archaeological site"
            }
        elif entity_id == "456":
            return {
                "label": "Site Without Name",
                "coordinates": "59.85, 17.64",
                "type": "Settlement"
            }
        elif entity_id == "789":
            return {
                "field1": "Value 1",
                "field2": None,
                "field3": "",
                "field4": "   ",  # Whitespace only
                "field5": "Valid Value"
            }
        elif entity_id == "empty":
            return {}
        elif entity_id == "notfound":
            return None
        else:
            return {"default": "value"}


class MockStrategies:
    """Mock Strategies class that behaves like the real one"""
    def __init__(self):
        self.strategy = MockStrategy()
        self.items = {
            "site": self.strategy,
            "taxon": self.strategy
        }


class MockAsyncContextManager:
    """Proper async context manager for mocking database cursor"""
    def __init__(self, cursor_mock):
        self.cursor_mock = cursor_mock
    
    async def __aenter__(self):
        return self.cursor_mock
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


@pytest.fixture
def mock_strategies():
    """Mock only the Strategies object"""
    mock_strategies_instance = MockStrategies()
    # Patch the Strategies class at the module level where it's imported
    with patch('src.render.Strategies'_instance) as mock_strategies:
        yield mock_strategies

def mock_connection():
    """Create a mock connection with a proper async context manager for cursor"""
    mock_conn = AsyncMock(spec=psycopg.AsyncConnection)
    mock_conn.cursor.return_value = AsyncMock(spec=psycopg.AsyncCursor)
    return mock_conn

class TestRenderPreview:
    """Test cases for render_preview function"""
    
    def setup_method(self):
        """Set up test fixtures."""
        ConfigStore.configure_context(source="./tests/config.yml")
        connection: AsyncMock = mock_connection()
        ConfigStore.config().update({"runtime:connection": connection})
        
        # Store cursor for test access
        self.mock_cursor = connection.cursor()
    
    @pytest.mark.asyncio
    async def test_successful_render_with_name(self):
        """Test successful rendering when entity has 'Name' field"""

        uri = f"{ID_BASE}site/123"
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
    async def test_successful_render_with_label_fallback(self):
        """Test rendering when entity has 'label' but no 'Name' field"""
        uri = f"{ID_BASE}site/456"
        result = await render_preview(uri)
        
        assert isinstance(result, str)
        assert "<h3 style='margin-top:0;'>Site Without Name</h3>" in result
        assert "<strong style='color:#333; min-width:100px; display:inline-block;'>label:</strong>" in result
        assert "<span>Site Without Name</span>" in result
        assert "<strong style='color:#333; min-width:100px; display:inline-block;'>coordinates:</strong>" in result
        assert "<span>59.85, 17.64</span>" in result
    
    @pytest.mark.asyncio
    async def test_render_filters_empty_values(self):
        """Test that None, empty strings, and whitespace-only values are filtered out"""
        uri = f"{ID_BASE}site/789"
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
    async def test_render_empty_details(self):
        """Test rendering when entity details are empty"""
        uri = f"{ID_BASE}site/empty"
        result = await render_preview(uri)
        
        assert isinstance(result, str)
        assert "<h3 style='margin-top:0;'>Details</h3>" in result  # Fallback title
        assert "<div style='padding:10px; font:14px sans-serif; line-height:1.6;'>" in result
        assert result.count("<div style='margin-bottom:5px;'>") == 0  # No detail rows
    
    @pytest.mark.asyncio
    async def test_invalid_id_format(self):
        """Test error when URI doesn't start with id_base"""
        # Use wrong URI that doesn't match the configured id_base
        uri = "https://wrong-domain.org/sead/site/123"

        with pytest.raises(ValueError, match="Invalid ID format"):
            await render_preview(uri)
    
    @pytest.mark.asyncio
    async def test_invalid_id_path_too_few_parts(self):
        """Test error when URI path has insufficient parts"""
        uri = f"{ID_BASE}site"  # Missing entity ID

        with pytest.raises(ValueError, match="Invalid ID path"):
            await render_preview(uri)
    
    @pytest.mark.asyncio
    async def test_invalid_id_path_too_many_parts(self):
        """Test error when URI path has too many parts"""
        uri = f"{ID_BASE}site/123/extra"

        with pytest.raises(ValueError, match="Invalid ID path"):
            await render_preview(uri)
    
    @pytest.mark.asyncio
    async def test_unknown_entity_type(self):
        """Test error when entity type is not supported"""
        uri = f"{ID_BASE}unknown/123"

        with pytest.raises(ValueError, match="Unknown entity type: unknown"):
            await render_preview(uri)
    
    @pytest.mark.asyncio
    async def test_entity_not_found(self):
        """Test error when entity is not found in database"""
        uri = f"{ID_BASE}site/notfound"

        with pytest.raises(ValueError, match="Entity with ID notfound not found or preview not implemented"):
            await render_preview(uri)
    
    @pytest.mark.asyncio
    async def test_html_structure(self):
        """Test that generated HTML has correct structure"""
        uri = f"{ID_BASE}site/123"
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
    async def test_different_entity_types(self):
        """Test that different entity types work correctly"""
        # Test with 'taxon' entity type
        uri = f"{ID_BASE}taxon/123"
        result = await render_preview(uri)
        
        assert isinstance(result, str)
        assert "<h3 style='margin-top:0;'>Test Site</h3>" in result  # Uses same mock data
    
    @pytest.mark.asyncio
    async def test_special_characters_in_values(self):
        """Test handling of special characters in entity values"""
        
        # Mock strategy that returns values with special characters
        with patch.object(MockStrategy, 'get_details') as mock_get_details:
            mock_get_details.return_value = {
                "Name": "Site with <special> & 'chars'",
                "description": 'Description with "quotes" & ampersands'
            }

            uri = f"{ID_BASE}site/special"
            result = await render_preview(uri)
            
            assert isinstance(result, str)
            # HTML should contain the special characters (not escaped in this simple implementation)
            assert "Site with <special> & 'chars'" in result
            assert 'Description with "quotes" & ampersands' in result


class TestRenderPreviewEdgeCases:
    """Test edge cases and error conditions"""
    
    def setup_method(self):
        """Set up test fixtures for edge cases."""
        ConfigStore.configure_context(source="./tests/config.yml")
        ConfigStore.config().update({"runtime:connection": mock_connection()})

    
    @pytest.mark.asyncio 
    async def test_strategy_get_details_raises_exception(self):
        """Test when strategy.get_details raises an exception"""
        ConfigStore.config().add({"runtime:connection": mock_connection()})
        
        with patch('src.render.Strategies', MockStrategies()), \
             patch.object(MockStrategy, 'get_details') as mock_get_details:
            
            mock_get_details.side_effect = Exception("Strategy error")
            uri = f"{ID_BASE}site/123"

            with pytest.raises(Exception, match="Strategy error"):
                await render_preview(uri)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])