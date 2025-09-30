"""
Unit tests for the API router endpoints.
"""

import json
from psycopg import Error
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from configuration.inject import ConfigStore
from src.api.router import router


ID_BASE = "https://w3id.org/sead/id/"


class MockStrategies:
    """Mock Strategies class for testing"""
    def __init__(self):
        self.items = {
            "Site": MagicMock(),
            "Taxon": MagicMock()
        }


@pytest.fixture
def app():
    """Create FastAPI test app with router"""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_config():
    """Set up test configuration"""
    ConfigStore.configure_context(source="./tests/config.yml")
    yield
    

class TestHealthCheck:
    """Test health check endpoint"""
    def setup_method(self):
        """Set up test fixtures"""
        ConfigStore.configure_context(source="./tests/config.yml")
    
    def test_is_alive(self, client, mock_config):
        """Test the health check endpoint"""
        response = client.get("/is_alive")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


class TestMetaEndpoint:
    """Test reconciliation metadata endpoint"""
    
    def setup_method(self):
        """Set up test fixtures"""
        ConfigStore.configure_context(source="./tests/config.yml")
    
    @patch('src.api.router.Strategies', MockStrategies())
    def test_meta_endpoint_structure(self, client):
        """Test metadata endpoint returns correct structure"""
        response = client.get("/reconcile")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check required fields
        assert data["name"] == "SEAD Entity Reconciliation"
        assert data["identifierSpace"] == ID_BASE
        assert data["schemaSpace"] == "http://www.w3.org/2004/02/skos/core#"
        assert "defaultTypes" in data
        
        # Check entity types
        assert len(data["defaultTypes"]) == 2
        type_ids = [t["id"] for t in data["defaultTypes"]]
        assert "Site" in type_ids
        assert "Taxon" in type_ids
    
    @patch('src.api.router.Strategies', MockStrategies())
    def test_meta_endpoint_extensions(self, client):
        """Test metadata endpoint includes property extensions"""
        response = client.get("/reconcile")
        data = response.json()
        
        # Check extend configuration
        assert "extend" in data
        extend = data["extend"]
        
        assert "propose_properties" in extend
        assert extend["propose_properties"]["service_url"] == f"{ID_BASE}reconcile"
        assert extend["propose_properties"]["service_path"] == "/properties"
        
        # Check property settings
        assert "property_settings" in extend
        properties = extend["property_settings"]
        
        property_names = [p["name"] for p in properties]
        assert "latitude" in property_names
        assert "longitude" in property_names
        assert "country" in property_names
        assert "national_id" in property_names
        assert "place_name" in property_names
        
        # Check latitude property details
        lat_prop = next(p for p in properties if p["name"] == "latitude")
        assert lat_prop["type"] == "number"
        assert lat_prop["settings"]["min"] == -90.0
        assert lat_prop["settings"]["max"] == 90.0


class TestReconcileEndpoint:
    """Test reconciliation endpoint"""
    
    def setup_method(self):
        """Set up test fixtures"""
        ConfigStore.configure_context(source="./tests/config.yml")
    
    @patch('src.api.router.reconcile_queries')
    def test_reconcile_successful_query(self, mock_reconcile_queries, client):
        """Test successful reconciliation query"""
        # Mock reconcile_queries response
        mock_reconcile_queries.return_value = {
            "q0": {
                "result": [
                    {
                        "id": f"{ID_BASE}site/123",
                        "name": "Test Site",
                        "score": 95.0,
                        "match": True,
                        "type": [{"id": "site", "name": "Site"}]
                    }
                ]
            }
        }
        
        query_data = {
            "queries": {
                "q0": {
                    "query": "test site",
                    "type": "site"
                }
            }
        }
        
        with patch("src.render.Strategies", MockStrategies()):
            response = client.post("/reconcile", json=query_data)

        assert response.status_code == 200
        
        data = response.json()
        assert "q0" in data
        assert "result" in data["q0"]
        
        results = data["q0"]["result"]
        assert len(results) == 1
        assert results[0]["name"] == "Test Site"
        assert results[0]["score"] == 95.0
        
        # Verify reconcile_queries was called with correct data
        mock_reconcile_queries.assert_called_once_with({
            "q0": {
                "query": "test site",
                "type": "site"
            }
        })
    
    @patch('src.api.router.reconcile_queries')
    def test_reconcile_queries_as_string(self, mock_reconcile_queries, client):
        """Test when queries parameter is a JSON string"""
        mock_reconcile_queries.return_value = {"q0": {"result": []}}
        
        queries_obj = {
            "q0": {
                "query": "test site",
                "type": "Site"
            }
        }
        
        query_data = {
            "queries": json.dumps(queries_obj)
        }
        
        response = client.post("/reconcile", json=query_data)
        assert response.status_code == 200
        
        # Verify the JSON string was parsed correctly
        mock_reconcile_queries.assert_called_once_with(queries_obj)
    
    def test_reconcile_missing_queries(self, client):
        """Test error when queries are missing"""
        response = client.post("/reconcile", json={})
        assert response.status_code == 400
        assert "No queries provided" in response.json()["error"]
    
    def test_reconcile_invalid_json(self, client):
        """Test error when request contains invalid JSON"""
        response = client.post(
            "/reconcile",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["error"]
    
    @patch('src.api.router.reconcile_queries')
    def test_reconcile_database_error(self, mock_reconcile_queries, client):
        """Test database error handling"""
        import psycopg
        mock_reconcile_queries.side_effect = psycopg.Error("Database connection failed")
        
        query_data = {
            "queries": {
                "q0": {
                    "query": "test site",
                    "type": "Site"
                }
            }
        }
        with pytest.raises(Error):
            response = client.post("/reconcile", json=query_data)
            assert response.status_code == 500
            assert "Database error" in response.json()["error"]
    
    @patch('src.api.router.reconcile_queries')
    def test_reconcile_general_error(self, mock_reconcile_queries, client):
        """Test general error handling"""
        mock_reconcile_queries.side_effect = Exception("Something went wrong")
        
        query_data = {
            "queries": {
                "q0": {
                    "query": "test site",
                    "type": "Site"
                }
            }
        }
        
        with pytest.raises(Exception):
            response = client.post("/reconcile", json=query_data)
            assert response.status_code == 500
            assert "Internal server error" in response.json()["error"]


class TestPropertiesEndpoint:
    """Test property suggestion endpoint"""
    
    def setup_method(self):
        """Set up test fixtures"""
        ConfigStore.configure_context(source="./tests/config.yml")
    
    def test_properties_all(self, client, mock_config):
        """Test getting all properties without filter"""
        response = client.get("/reconcile/properties")
        assert response.status_code == 200
        
        data = response.json()
        assert "properties" in data
        
        properties = data["properties"]
        assert len(properties) == 5
        
        # Check all expected properties are present
        property_ids = [p["id"] for p in properties]
        expected_ids = ["latitude", "longitude", "country", "national_id", "place_name"]
        for expected_id in expected_ids:
            assert expected_id in property_ids
        
        # Check property structure
        for prop in properties:
            assert "id" in prop
            assert "name" in prop
            assert "type" in prop
            assert "description" in prop
    
    def test_properties_filtered_by_query(self, client, mock_config):
        """Test filtering properties by query string"""
        response = client.get("/reconcile/properties?query=lat")
        assert response.status_code == 200
        
        data = response.json()
        properties = data["properties"]
        
        # Should return latitude (matches "lat" in id)
        assert len(properties) == 1
        assert properties[0]["id"] == "latitude"
    
    def test_properties_filtered_by_name(self, client, mock_config):
        """Test filtering properties by name"""
        response = client.get("/reconcile/properties?query=country")
        assert response.status_code == 200
        
        data = response.json()
        properties = data["properties"]
        
        # Should return country property
        assert len(properties) == 1
        assert properties[0]["id"] == "country"
    
    def test_properties_filtered_by_description(self, client, mock_config):
        """Test filtering properties by description"""
        response = client.get("/reconcile/properties?query=geographic")
        assert response.status_code == 200
        
        data = response.json()
        properties = data["properties"]
        
        # Should return latitude, longitude, and place_name (all have "geographic" in description)
        assert len(properties) == 3
        property_ids = [p["id"] for p in properties]
        assert "latitude" in property_ids
        assert "longitude" in property_ids
        assert "place_name" in property_ids
    
    def test_properties_no_matches(self, client, mock_config):
        """Test query with no matches"""
        response = client.get("/reconcile/properties?query=nonexistent")
        assert response.status_code == 200
        
        data = response.json()
        properties = data["properties"]
        assert len(properties) == 0


class TestPreviewEndpoint:
    """Test preview endpoint"""
    
    def setup_method(self):
        """Set up test fixtures"""
        ConfigStore.configure_context(source="./tests/config.yml")
    
    @patch('src.api.router.render_preview')
    def test_preview_valid_id(self, mock_render_preview, client):
        """Test preview with valid ID"""
        mock_render_preview.return_value = "<div>Preview content</div>"
        
        response = client.get(f"/reconcile/preview?id={ID_BASE}site/123")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Preview content" in response.text
        
        mock_render_preview.assert_called_once_with(f"{ID_BASE}site/123")
    
    def test_preview_invalid_id_format(self, client):
        """Test preview with invalid ID format"""
        response = client.get("/reconcile/preview?id=https://wrong-domain.org/sead/site/123")
        assert response.status_code == 400
        assert "Invalid ID format" in response.text
    
    def test_preview_invalid_id_path_too_few_parts(self, client):
        """Test preview with insufficient path parts"""
        response = client.get(f"/reconcile/preview?id={ID_BASE}site")
        assert response.status_code == 400
        assert "Invalid ID path" in response.text
    
    def test_preview_invalid_id_path_too_many_parts(self, client):
        """Test preview with too many path parts"""
        response = client.get(f"/reconcile/preview?id={ID_BASE}site/123/extra")
        assert response.status_code == 400
        assert "Invalid ID path" in response.text
    
    @patch('src.api.router.render_preview')
    def test_preview_render_error(self, mock_render_preview, client):
        """Test preview when render_preview raises ValueError"""
        mock_render_preview.side_effect = ValueError("Entity not found")
        
        response = client.get(f"/reconcile/preview?id={ID_BASE}site/123")
        assert response.status_code == 500
        assert "Error: Entity not found" in response.text


class TestEndpointIntegration:
    """Integration tests for endpoint interactions"""
    
    def setup_method(self):
        """Set up test fixtures"""
        ConfigStore.configure_context(source="./tests/config.yml")
    
    @patch('src.api.router.Strategies', MockStrategies())
    @patch('src.api.router.reconcile_queries')
    @patch('src.api.router.render_preview')
    def test_full_reconciliation_workflow(self, mock_render_preview, mock_reconcile_queries, client):
        """Test a complete reconciliation workflow"""
        # Step 1: Get service metadata
        meta_response = client.get("/reconcile")
        assert meta_response.status_code == 200
        meta_data = meta_response.json()
        assert "Site" in [t["id"] for t in meta_data["defaultTypes"]]
        
        # Step 2: Get available properties
        props_response = client.get("/reconcile/properties")
        assert props_response.status_code == 200
        props_data = props_response.json()
        assert len(props_data["properties"]) == 5
        
        # Step 3: Perform reconciliation
        mock_reconcile_queries.return_value = {
            "q0": {
                "result": [
                    {
                        "id": f"{ID_BASE}site/123",
                        "name": "Test Site",
                        "score": 95.0,
                        "match": True,
                        "type": [{"id": "Site", "name": "Site"}]
                    }
                ]
            }
        }
        
        reconcile_response = client.post("/reconcile", json={
            "queries": {
                "q0": {
                    "query": "test site",
                    "type": "Site",
                    "properties": [
                        {"pid": "country", "v": "Sweden"}
                    ]
                }
            }
        })
        assert reconcile_response.status_code == 200
        reconcile_data = reconcile_response.json()
        entity_id = reconcile_data["q0"]["result"][0]["id"]
        
        # Step 4: Get preview for the result
        mock_render_preview.return_value = "<div>Site details</div>"
        preview_response = client.get(f"/reconcile/preview?id={entity_id}")
        assert preview_response.status_code == 200
        assert "Site details" in preview_response.text

class TestSetupConfigStore:

    """Test setup_config_store function"""
    
    # @patch('src.api.router.ConfigStore.configure_context')
    @pytest.mark.asyncio
    async def test_setup_config_store_success(self): #, mock_configure_context):
        """Test successful configuration setup"""
        from src.api.router import setup_config_store
        
        await setup_config_store()
        
        # mock_configure_context.assert_called_once_with(source="./config.yml")

class TestErrorHandling:
    """Test error handling across endpoints"""
    
    def setup_method(self):
        """Set up test fixtures"""
        ConfigStore.configure_context(source="./tests/config.yml")
    
    def test_malformed_json_requests(self, client):
        """Test various malformed JSON requests"""
        # Missing content-type
        # Patch get_default_config_filename to return the test config path
        with patch('src.api.router.get_default_config_filename', return_value="./tests/config.yml"):
            response = client.post("/reconcile", data='{"invalid": json}')
            assert response.status_code in [400, 422]  # FastAPI validation error
        
        # Empty JSON object
        response = client.post("/reconcile", json={})
        assert response.status_code in [400, 422]
        assert "No queries provided" in response.json()["error"]
    
if __name__ == "__main__":
    pytest.main([__file__, "-v"])