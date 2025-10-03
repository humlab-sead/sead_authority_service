"""
Unit tests for the API router endpoints.
"""

import json
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.router import router
from src.configuration.inject import MockConfigProvider
from src.strategies.interface import Strategies, StrategyRegistry
from src.metadata import _compile_property_settings, get_reconcile_properties, get_reconciliation_metadata
from tests.decorators import with_test_config

ID_BASE = "https://w3id.org/sead/id/"

# pylint: disable=protected-access, unused-argument, redefined-outer-name


class MockStrategy:
    """Mock strategy class with get_properties_meta method"""

    def get_properties_meta(self):
        return [
            {"id": "latitude", "name": "Latitude", "type": "number", "description": "Geographic latitude"},
            {"id": "longitude", "name": "Longitude", "type": "number", "description": "Geographic longitude"},
            {"id": "country", "name": "Country", "type": "string", "description": "Country name"},
            {"id": "national_id", "name": "National Site ID", "type": "string", "description": "National identifier"},
            {"id": "place_name", "name": "Place Name", "type": "string", "description": "Place name"},
        ]

    def get_property_settings(self):
        return {
            "latitude": {"min": -90.0, "max": 90.0, "precision": 6},
            "longitude": {"min": -180.0, "max": 180.0, "precision": 6},
        }

    def get_id_path(self):
        return "site"
    
class MockStrategies:
    """Mock Strategies class for testing"""

    def __init__(self):
        self.items: dict[str, type[MockStrategy]] = {"site": MockStrategy, "taxon": MockStrategy}


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


class TestHealthCheck:
    """Test health check endpoint"""

    @with_test_config
    def test_is_alive(self, client: TestClient, test_provider: MockConfigProvider):
        """Test the health check endpoint"""
        response = client.get("/is_alive")
        assert response.status_code == 200
        assert response.json() == {"status": "alive"}


class TestMetaEndpoint:
    """Test reconciliation metadata endpoint"""

    @with_test_config
    def test_xyz(self, test_provider: MockConfigProvider) -> None:
        x: StrategyRegistry = _compile_property_settings(Strategies)
        y: list[dict[str, str]] | Any = get_reconcile_properties(Strategies, "lat", "site")
        z: dict[str, Any] = get_reconciliation_metadata(Strategies)
        pass

    @patch("src.api.router.Strategies", MockStrategies())
    @with_test_config
    def test_meta_endpoint_structure(self, client, test_provider: MockConfigProvider):
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
        assert "site" in type_ids
        assert "taxon" in type_ids

    @patch("src.api.router.Strategies", MockStrategies())
    @with_test_config
    def test_meta_endpoint_extensions(self, client, test_provider: MockConfigProvider):
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

    @patch("src.api.router.reconcile_queries")
    @with_test_config
    def test_reconcile_successful_query(self, mock_reconcile_queries, client, test_provider: MockConfigProvider):
        """Test successful reconciliation query"""
        # Mock reconcile_queries response
        mock_reconcile_queries.return_value = {
            "q0": {"result": [{"id": f"{ID_BASE}site/123", "name": "Test Site", "score": 95.0, "match": True, "type": [{"id": "site", "name": "Site"}]}]}
        }

        query_data = {"queries": {"q0": {"query": "test site", "type": "site"}}}

        with patch("src.preview.Strategies", MockStrategies()):
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
        mock_reconcile_queries.assert_called_once_with({"q0": {"query": "test site", "type": "site"}})

    @patch("src.api.router.reconcile_queries")
    @with_test_config
    def test_reconcile_queries_as_string(self, mock_reconcile_queries, client: TestClient, test_provider: MockConfigProvider):
        """Test when queries parameter is a JSON string"""
        mock_reconcile_queries.return_value = {"q0": {"result": []}}

        queries_obj = {"q0": {"query": "test site", "type": "site"}}

        query_data = {"queries": json.dumps(queries_obj)}

        response = client.post("/reconcile", json=query_data)
        assert response.status_code == 200

        # Verify the JSON string was parsed correctly
        mock_reconcile_queries.assert_called_once_with(queries_obj)

    @with_test_config
    def test_reconcile_missing_queries(self, client: TestClient, test_provider: MockConfigProvider):
        """Test error when queries are missing"""
        response = client.post("/reconcile", json={})
        assert response.status_code == 400
        assert "No queries provided" in response.json()["error"]

    @with_test_config
    def test_reconcile_invalid_json(self, client: TestClient, test_provider: MockConfigProvider):
        """Test error when request contains invalid JSON"""
        response = client.post("/reconcile", data="invalid json", headers={"Content-Type": "application/json"})
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["error"]

    # @patch("src.api.router.reconcile_queries")
    # @with_test_config
    # def test_reconcile_database_error(self, mock_reconcile_queries, client: TestClient, test_provider: MockConfigProvider):
    #     """Test database error handling"""

    #     mock_reconcile_queries.side_effect = psycopg.Error("Database connection failed")

    #     query_data: dict[str, dict[str, dict[str, str]]] = {"queries": {"q0": {"query": "test site", "type": "site"}}}
    #     with pytest.raises(psycopg.Error):
    #         response: Response = client.post("/reconcile", json=query_data)
    #         assert response.status_code == 500
    #         assert "Database error" in response.json()["error"]

    @patch("src.api.router.reconcile_queries")
    @with_test_config
    def test_reconcile_general_error(self, mock_reconcile_queries, client, test_provider: MockConfigProvider):
        """Test general error handling"""
        mock_reconcile_queries.side_effect = Exception("Something went wrong")

        query_data = {"queries": {"q0": {"query": "test site", "type": "site"}}}

        with pytest.raises(Exception):
            response = client.post("/reconcile", json=query_data)
            assert response.status_code == 500
            assert "Internal server error" in response.json()["error"]


class TestPropertiesEndpoint:
    """Test property suggestion endpoint"""

    @with_test_config
    def test_properties_all(self, client: TestClient, test_provider: MockConfigProvider):
        """Test getting all properties without filter - returns properties from all strategies"""
        response = client.get("/reconcile/properties")
        assert response.status_code == 200

        data = response.json()
        assert "properties" in data

        properties = data["properties"]
        assert len(properties) > 0

        # Check that we have properties from both strategies
        property_ids = [p["id"] for p in properties]

        # Site properties
        site_properties: list[str] = ["latitude", "longitude", "country", "national_id", "place_name"]
        for expected_id in site_properties:
            assert expected_id in property_ids

        # Taxon properties
        taxon_properties: list[str] = ["scientific_name", "genus", "species", "family"]
        for expected_id in taxon_properties:
            assert expected_id in property_ids

        # Check property structure
        for prop in properties:
            assert "id" in prop
            assert "name" in prop
            assert "type" in prop
            assert "description" in prop

    @with_test_config
    def test_properties_filtered_by_query(self, client: TestClient, test_provider: MockConfigProvider):
        """Test filtering properties by query string"""
        response = client.get("/reconcile/properties?query=lat")
        assert response.status_code == 200

        data = response.json()
        properties = data["properties"]

        # Should return latitude (matches "lat" in id)
        assert len(properties) == 1
        assert properties[0]["id"] == "latitude"

    @with_test_config
    def test_properties_filtered_by_name(self, client: TestClient, test_provider: MockConfigProvider):
        """Test filtering properties by name"""
        response = client.get("/reconcile/properties?query=country")
        assert response.status_code == 200

        data = response.json()
        properties = data["properties"]

        # Should return country property
        assert len(properties) == 1
        assert properties[0]["id"] == "country"

    @with_test_config
    def test_properties_filtered_by_description(self, client: TestClient, test_provider: MockConfigProvider):
        """Test filtering properties by description"""
        response = client.get("/reconcile/properties?query=geographic")
        assert response.status_code == 200

        data = response.json()
        properties = data["properties"]

        # Should return latitude, longitude, and place_name (all have "geographic" in description)
        assert len(properties) == 4
        property_ids = [p["id"] for p in properties]
        assert "latitude" in property_ids
        assert "longitude" in property_ids
        assert "place_name" in property_ids

    @with_test_config
    def test_properties_no_matches(self, client: TestClient, test_provider: MockConfigProvider):
        """Test query with no matches"""
        response = client.get("/reconcile/properties?query=nonexistent")
        assert response.status_code == 200

        data = response.json()
        properties = data["properties"]
        assert len(properties) == 0

    @with_test_config
    def test_properties_filtered_by_site_type(self, client: TestClient, test_provider: MockConfigProvider):
        """Test filtering properties by site entity type"""
        response = client.get("/reconcile/properties?type=site")
        assert response.status_code == 200

        data = response.json()
        properties = data["properties"]

        # Should return only site properties
        assert len(properties) == 5
        property_ids = [p["id"] for p in properties]
        expected_site_ids = ["latitude", "longitude", "country", "national_id", "place_name"]
        for expected_id in expected_site_ids:
            assert expected_id in property_ids

        # Should not contain taxon properties
        taxon_ids = ["label", "genus", "species", "family"]
        for taxon_id in taxon_ids:
            assert taxon_id not in property_ids

    @with_test_config
    def test_properties_filtered_by_taxon_type(self, client: TestClient, test_provider: MockConfigProvider):
        """Test filtering properties by taxon entity type"""
        response = client.get("/reconcile/properties?type=taxon")
        assert response.status_code == 200

        data = response.json()
        properties = data["properties"]

        # Should return only taxon properties
        assert len(properties) == 4
        property_ids = [p["id"] for p in properties]
        expected_taxon_ids = ["scientific_name", "genus", "species", "family"]
        for expected_id in expected_taxon_ids:
            assert expected_id in property_ids

        # Should not contain site properties
        site_ids = ["latitude", "longitude", "country", "national_id", "place_name"]
        for site_id in site_ids:
            assert site_id not in property_ids

    @with_test_config
    def test_properties_unknown_entity_type(self, client: TestClient, test_provider: MockConfigProvider):
        """Test filtering properties by unknown entity type returns empty list"""
        response = client.get("/reconcile/properties?type=unknown")
        assert response.status_code == 200

        data = response.json()
        properties = data["properties"]
        assert len(properties) == 0

    @with_test_config
    def test_properties_combined_filters(self, client: TestClient, test_provider: MockConfigProvider):
        """Test combining type and query filters"""
        response = client.get("/reconcile/properties?type=site&query=lat")
        assert response.status_code == 200

        data = response.json()
        properties = data["properties"]

        # Should return only latitude from site properties
        assert len(properties) == 1
        assert properties[0]["id"] == "latitude"


class TestPreviewEndpoint:
    """Test preview endpoint"""

    @patch("src.api.router.render_preview")
    @with_test_config
    def test_preview_valid_id(self, mock_render_preview, client: TestClient, test_provider: MockConfigProvider):
        """Test preview with valid ID"""
        mock_render_preview.return_value = "<div>Preview content</div>"

        response = client.get(f"/reconcile/preview?id={ID_BASE}site/123")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"
        assert "Preview content" in response.text

        mock_render_preview.assert_called_once_with(f"{ID_BASE}site/123")

    @with_test_config
    def test_preview_invalid_id_format(self, client: TestClient, test_provider: MockConfigProvider):
        """Test preview with invalid ID format"""
        response = client.get("/reconcile/preview?id=https://wrong-domain.org/sead/site/123")
        assert response.status_code == 400
        assert "Invalid ID format" in response.text

    @with_test_config
    def test_preview_invalid_id_path_too_few_parts(self, client: TestClient, test_provider: MockConfigProvider):
        """Test preview with insufficient path parts"""
        response = client.get(f"/reconcile/preview?id={ID_BASE}site")
        assert response.status_code == 400
        assert "Invalid ID path" in response.text

    @with_test_config
    def test_preview_invalid_id_path_too_many_parts(self, client: TestClient, test_provider: MockConfigProvider):
        """Test preview with too many path parts"""
        response = client.get(f"/reconcile/preview?id={ID_BASE}site/123/extra")
        assert response.status_code == 400
        assert "Invalid ID path" in response.text

    @patch("src.api.router.render_preview")
    @with_test_config
    def test_preview_render_error(self, mock_render_preview, client: TestClient, test_provider: MockConfigProvider):
        """Test preview when render_preview raises ValueError"""
        mock_render_preview.side_effect = ValueError("Entity not found")

        response = client.get(f"/reconcile/preview?id={ID_BASE}site/123")
        assert response.status_code == 500
        assert "Error: Entity not found" in response.text


class TestEndpointIntegration:
    """Integration tests for endpoint interactions"""

    @patch("src.api.router.Strategies", MockStrategies())
    @patch("src.api.router.reconcile_queries")
    @patch("src.api.router.render_preview")
    @with_test_config
    def test_full_reconciliation_workflow(self, mock_render_preview, mock_reconcile_queries, client: TestClient, test_provider: MockConfigProvider):
        """Test a complete reconciliation workflow"""
        # Step 1: Get service metadata
        meta_response = client.get("/reconcile")
        assert meta_response.status_code == 200
        meta_data = meta_response.json()
        assert "site" in [t["id"] for t in meta_data["defaultTypes"]]

        # Step 2: Get available properties (both strategies return same properties, so we get duplicates)
        props_response = client.get("/reconcile/properties")
        assert props_response.status_code == 200
        props_data = props_response.json()
        assert len(props_data["properties"]) == 10  # 5 properties from each of the 2 mock strategies

        # Step 3: Perform reconciliation
        mock_reconcile_queries.return_value = {
            "q0": {"result": [{"id": f"{ID_BASE}site/123", "name": "Test Site", "score": 95.0, "match": True, "type": [{"id": "site", "name": "Site"}]}]}
        }

        reconcile_response = client.post(
            "/reconcile", json={"queries": {"q0": {"query": "test site", "type": "site", "properties": [{"pid": "country", "v": "Sweden"}]}}}
        )
        assert reconcile_response.status_code == 200
        reconcile_data = reconcile_response.json()
        entity_id = reconcile_data["q0"]["result"][0]["id"]

        # Step 4: Get preview for the result
        mock_render_preview.return_value = "<div>Site details</div>"
        preview_response = client.get(f"/reconcile/preview?id={entity_id}")
        assert preview_response.status_code == 200
        assert "Site details" in preview_response.text


class TestErrorHandling:
    """Test error handling across endpoints"""

    @with_test_config
    def test_malformed_json_requests(self, client: TestClient, test_provider: MockConfigProvider):
        """Test various malformed JSON requests"""
        # Missing content-type
        # Patch get_default_config_filename to return the test config path
        response = client.post("/reconcile", data='{"invalid": json}')
        assert response.status_code in [400, 422]  # FastAPI validation error

        # Empty JSON object
        response = client.post("/reconcile", json={})
        assert response.status_code in [400, 422]
        assert "No queries provided" in response.json()["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
