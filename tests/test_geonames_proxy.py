"""
Unit tests for GeoNames API proxy.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List

import httpx

from src.geonames.proxy import GeoNamesProxy, NotSupportedError


class TestGeoNamesProxy:
    """Test GeoNamesProxy functionality"""

    def test_init_default_params(self):
        """Test GeoNamesProxy initialization with default parameters"""
        proxy = GeoNamesProxy(username="test_user")
        
        assert proxy.username == "test_user"
        assert proxy.base_url == "https://api.geonames.org"
        assert proxy.lang == "en"
        assert proxy.timeout == 20.0
        assert "sead-GeonamesProxy/1.0" in proxy.user_agent
        assert proxy._client is None

    def test_init_custom_params(self):
        """Test GeoNamesProxy initialization with custom parameters"""
        proxy = GeoNamesProxy(
            username="custom_user",
            base_url="https://custom.geonames.org/",
            lang="sv",
            timeout=30.0,
            user_agent="CustomApp/2.0"
        )
        
        assert proxy.username == "custom_user"
        assert proxy.base_url == "https://custom.geonames.org"  # Should strip trailing slash
        assert proxy.lang == "sv"
        assert proxy.timeout == 30.0
        assert proxy.user_agent == "CustomApp/2.0"

    @pytest.mark.asyncio
    async def test_context_manager_setup_and_teardown(self):
        """Test async context manager behavior"""
        proxy = GeoNamesProxy(username="test_user")
        
        assert proxy._client is None
        
        async with proxy as p:
            assert p is proxy
            assert proxy._client is not None
            assert isinstance(proxy._client, httpx.AsyncClient)
            
        # After exiting context, client should be closed
        assert proxy._client is None

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_context_manager_client_close(self, mock_client_class):
        """Test that client is properly closed on context exit"""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            pass
        
        mock_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_search_basic(self, mock_client_class):
        """Test basic search functionality"""
        # Mock response data
        mock_response_data = {
            "geonames": [
                {
                    "geonameId": 2666199,
                    "name": "Umeå",
                    "lat": "63.82842",
                    "lng": "20.25972",
                    "countryName": "Sweden",
                    "population": 83249
                }
            ]
        }
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            results = await proxy.search("Umeå")
        
        # Verify the request was made correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "/searchJSON" in call_args[0][0]
        
        # Verify parameters
        params = call_args[1]["params"]
        param_dict = dict(params) if isinstance(params, list) else params
        assert param_dict["q"] == "Umeå"
        assert param_dict["username"] == "test_user"
        assert param_dict["type"] == "json"
        assert param_dict["lang"] == "en"
        
        # Verify results
        assert len(results) == 1
        assert results[0]["name"] == "Umeå"
        assert results[0]["geonameId"] == 2666199

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_search_with_all_parameters(self, mock_client_class):
        """Test search with all optional parameters"""
        mock_response_data = {"geonames": []}
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            results = await proxy.search(
                "Stockholm",
                max_rows=5,
                country_bias="SE",
                lang="sv",
                feature_classes=["P", "A"],
                fuzzy=0.9,
                orderby="population",
                style="SHORT",
                extra_params={"custom_param": "custom_value"}
            )
        
        # Verify the request parameters
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        
        # Convert to dict for easier testing
        param_dict = {}
        feature_classes = []
        for param in params:
            if param[0] == "featureClass":
                feature_classes.append(param[1])
            else:
                param_dict[param[0]] = param[1]
        
        assert param_dict["q"] == "Stockholm"
        assert param_dict["maxRows"] == 5
        assert param_dict["countryBias"] == "SE"
        assert param_dict["lang"] == "sv"
        assert param_dict["fuzzy"] == 0.9
        assert param_dict["orderby"] == "population"
        assert param_dict["style"] == "SHORT"
        assert param_dict["custom_param"] == "custom_value"
        assert "P" in feature_classes
        assert "A" in feature_classes

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_details_basic(self, mock_client_class):
        """Test get_details functionality"""
        mock_response_data = {
            "geonameId": 2666199,
            "name": "Umeå",
            "lat": "63.82842",
            "lng": "20.25972",
            "countryName": "Sweden",
            "population": 83249,
            "timezone": {
                "timeZoneId": "Europe/Stockholm"
            }
        }
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            result = await proxy.get_details(2666199)
        
        # Verify the request was made correctly
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "/getJSON" in call_args[0][0]
        
        # Verify parameters
        params = dict(call_args[1]["params"])
        assert params["geonameId"] == 2666199
        assert params["username"] == "test_user"
        assert params["type"] == "json"
        
        # Verify result
        assert result["name"] == "Umeå"
        assert result["geonameId"] == 2666199

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_details_with_string_id(self, mock_client_class):
        """Test get_details with string geoname_id"""
        mock_response_data = {"geonameId": 2666199, "name": "Test"}
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            await proxy.get_details("2666199")  # String ID
        
        # Verify the geonameId parameter was converted to int
        call_args = mock_client.get.call_args
        params = dict(call_args[1]["params"])
        assert params["geonameId"] == 2666199
        assert isinstance(params["geonameId"], int)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_details_with_extra_params(self, mock_client_class):
        """Test get_details with extra parameters"""
        mock_response_data = {"geonameId": 123, "name": "Test"}
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            await proxy.get_details(
                123,
                lang="sv",
                style="MEDIUM",
                extra_params={"include_bbox": True}
            )
        
        # Verify parameters
        call_args = mock_client.get.call_args
        params = dict(call_args[1]["params"])
        assert params["lang"] == "sv"
        assert params["style"] == "MEDIUM"
        assert params["include_bbox"] is True

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_get_json_without_context_manager(self, mock_client_class):
        """Test _get_json fallback when used without context manager"""
        mock_response_data = {"test": "data"}
        
        # Mock for the fallback client
        mock_fallback_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_fallback_client.get.return_value = mock_response
        
        # Mock the context manager behavior
        mock_client_class.return_value.__aenter__.return_value = mock_fallback_client
        mock_client_class.return_value.__aexit__.return_value = None
        
        proxy = GeoNamesProxy(username="test_user")
        # Don't use context manager, so _client is None
        
        result = await proxy._get_json("/test", [("param", "value")])
        
        assert result == mock_response_data
        mock_fallback_client.get.assert_called_once()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_http_error_handling(self, mock_client_class):
        """Test HTTP error handling"""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        )
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        with pytest.raises(httpx.HTTPStatusError):
            async with proxy:
                await proxy.search("test")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_geonames_api_error_handling(self, mock_client_class):
        """Test GeoNames API error handling"""
        # Mock GeoNames error response
        error_response = {
            "status": {
                "message": "user account not enabled to use the free webservice",
                "value": 10
            }
        }
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        with pytest.raises(RuntimeError, match="GeoNames error 10.*not enabled"):
            async with proxy:
                await proxy.search("test")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_geonames_api_error_minimal(self, mock_client_class):
        """Test GeoNames API error with minimal error info"""
        # Mock GeoNames error response with minimal info
        error_response = {
            "status": {}
        }
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = error_response
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        with pytest.raises(RuntimeError, match="GeoNames error unknown.*GeoNames API error"):
            async with proxy:
                await proxy.search("test")

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_search_empty_results(self, mock_client_class):
        """Test search with no results"""
        mock_response_data = {"geonames": []}
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            results = await proxy.search("nonexistentplace12345")
        
        assert results == []

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_search_missing_geonames_key(self, mock_client_class):
        """Test search when response doesn't have geonames key"""
        mock_response_data = {"other_key": "value"}
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            results = await proxy.search("test")
        
        assert results == []

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_feature_classes_parameter(self, mock_client_class):
        """Test that multiple feature classes are handled correctly"""
        mock_response_data = {"geonames": []}
        
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            await proxy.search("test", feature_classes=["P", "A", "H"])
        
        # Verify multiple featureClass parameters
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        
        feature_class_params = [param for param in params if param[0] == "featureClass"]
        assert len(feature_class_params) == 3
        assert ("featureClass", "P") in feature_class_params
        assert ("featureClass", "A") in feature_class_params
        assert ("featureClass", "H") in feature_class_params

    def test_ensure_ok_static_method_success(self):
        """Test _ensure_ok static method with successful response"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"valid": "response"}
        
        result = GeoNamesProxy._ensure_ok(mock_response)
        assert result == {"valid": "response"}

    def test_ensure_ok_static_method_with_error(self):
        """Test _ensure_ok static method with GeoNames error"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "status": {
                "message": "rate limit exceeded",
                "value": 19
            }
        }
        
        with pytest.raises(RuntimeError, match="GeoNames error 19.*rate limit exceeded"):
            GeoNamesProxy._ensure_ok(mock_response)

class TestGeoNamesProxyIntegration:
    """Integration-style tests for GeoNamesProxy"""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_complete_search_workflow(self, mock_client_class):
        """Test complete workflow: search -> get_details"""
        # Mock search response
        search_response = {
            "geonames": [
                {
                    "geonameId": 2666199,
                    "name": "Umeå",
                    "lat": "63.82842",
                    "lng": "20.25972"
                }
            ]
        }
        
        # Mock details response
        details_response = {
            "geonameId": 2666199,
            "name": "Umeå",
            "lat": "63.82842",
            "lng": "20.25972",
            "countryName": "Sweden",
            "population": 83249,
            "timezone": {"timeZoneId": "Europe/Stockholm"}
        }
        
        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            # First call (search)
            MagicMock(json=lambda: search_response, raise_for_status=lambda: None),
            # Second call (get_details)
            MagicMock(json=lambda: details_response, raise_for_status=lambda: None)
        ]
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user")
        
        async with proxy:
            # Search for places
            search_results = await proxy.search("Umeå", country_bias="SE")
            
            # Get details for first result
            if search_results:
                details = await proxy.get_details(search_results[0]["geonameId"])
        
        # Verify workflow
        assert len(search_results) == 1
        assert search_results[0]["name"] == "Umeå"
        assert details["population"] == 83249
        assert details["timezone"]["timeZoneId"] == "Europe/Stockholm"
        
        # Verify two API calls were made
        assert mock_client.get.call_count == 2


class TestGeoNamesProxyEdgeCases:
    """Test edge cases and error conditions"""

    def test_invalid_json_response(self):
        """Test handling of invalid JSON response"""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        
        with pytest.raises(json.JSONDecodeError):
            GeoNamesProxy._ensure_ok(mock_response)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_network_timeout(self, mock_client_class):
        """Test network timeout handling"""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value = mock_client
        
        proxy = GeoNamesProxy(username="test_user", timeout=1.0)
        
        with pytest.raises(httpx.TimeoutException):
            async with proxy:
                await proxy.search("test")

    @pytest.mark.asyncio
    async def test_context_manager_exception_handling(self):
        """Test that context manager properly handles exceptions during setup"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client_class.side_effect = Exception("Client creation failed")
            
            proxy = GeoNamesProxy(username="test_user")
            
            with pytest.raises(Exception, match="Client creation failed"):
                async with proxy:
                    pass

    def test_base_url_stripping(self):
        """Test that base URL properly strips trailing slashes"""
        test_cases = [
            ("https://api.geonames.org", "https://api.geonames.org"),
            ("https://api.geonames.org/", "https://api.geonames.org"),
            ("https://api.geonames.org//", "https://api.geonames.org"),
            ("https://custom.domain.com/api/", "https://custom.domain.com/api"),
        ]
        
        for input_url, expected_url in test_cases:
            proxy = GeoNamesProxy(username="test", base_url=input_url)
            assert proxy.base_url == expected_url


if __name__ == "__main__":
    pytest.main([__file__, "-v"])