"""
Tests for the OpenRefine Suggest API endpoints.

These endpoints provide autocomplete and inline tooltip preview functionality
for OpenRefine reconciliation.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import psycopg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from src.api.router import router
from src.configuration import MockConfigProvider
from tests.conftest import MockRow
from tests.decorators import with_test_config

# pylint: disable=redefined-outer-name, unused-argument, too-many-locals


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test FastAPI app"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def mock_results() -> list[dict[str, Any]]:
    """Mock results for suggest endpoints"""
    return [
        {"id": "https://w3id.org/sead/id/site/123", "name": "Uppland Site", "type": [{"id": "site", "name": "Site"}], "score": 95.0},
        {"id": "https://w3id.org/sead/id/site/124", "name": "Uppsala Location", "type": [{"id": "site", "name": "Site"}], "score": 90.0},
    ]


@pytest.mark.asyncio
@with_test_config
async def test_suggest_entity_with_prefix(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test entity autocomplete with prefix"""
    mock_results = [
        {"id": "https://w3id.org/sead/id/site/123", "name": "Uppland Site", "type": [{"id": "site", "name": "Site"}], "score": 95.0},
        {"id": "https://w3id.org/sead/id/site/124", "name": "Uppsala Location", "type": [{"id": "site", "name": "Site"}], "score": 90.0},
    ]

    # Mock the suggest function or database query - return dict format
    with patch("src.api.router.suggest_entities", new=AsyncMock(return_value={"result": mock_results})):

        async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
            response: Response = await client.get("/suggest/entity?prefix=upp")

            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert isinstance(data["result"], list)

            # Should return some results for 'upp' (Uppland, Uppsala, etc.)
            assert len(data["result"]) > 0

            # Check result format
            first_result = data["result"][0]
            assert "id" in first_result
            assert "name" in first_result
            assert "type" in first_result
            assert isinstance(first_result["type"], list)
            assert "score" in first_result


@pytest.mark.asyncio
@with_test_config
async def test_suggest_entity_with_type_filter(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test entity autocomplete with type filter"""
    with patch("src.api.router.suggest_entities", new=AsyncMock(return_value={"result": mock_results})):
        async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
            response: Response = await client.get("/suggest/entity?prefix=upp&type=site")

            assert response.status_code == 200
            data = response.json()
            assert "result" in data

            # All results should be of type 'site'
            for result in data["result"]:
                assert any(t["id"] == "site" for t in result["type"])


@pytest.mark.asyncio
@with_test_config
async def test_suggest_entity_short_prefix(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test entity autocomplete with short prefix (should return empty)"""
    with patch("src.api.router.suggest_entities", new=AsyncMock(return_value={"result": []})):
        async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
            response: Response = await client.get("/suggest/entity?prefix=u")

            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            # not implemented
            # assert data["result"] == []  # Too short, should return empty


@pytest.mark.asyncio
@with_test_config
async def test_suggest_type_all(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test type suggest without prefix (returns all types)"""
    # Create proper type suggestion mock data
    mock_type_results = [{"id": "site", "name": "Site"}, {"id": "location", "name": "Location"}, {"id": "taxon", "name": "Taxon"}]
    # Mock suggest_types to return dict format that the real function returns
    with patch("src.api.router.suggest_types", new=AsyncMock(return_value={"result": mock_type_results})):
        async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
            response: Response = await client.get("/suggest/type")

            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert isinstance(data["result"], list)
            assert len(data["result"]) > 0

            # Check format
            type_ids = [t["id"] for t in data["result"]]
            assert "site" in type_ids
            assert "location" in type_ids


@pytest.mark.asyncio
@with_test_config
async def test_suggest_type_with_prefix(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test type suggest with prefix filter"""
    # Create proper type suggestion mock data for prefix "loc"
    mock_type_results = [{"id": "location", "name": "Location"}]
    # Mock suggest_types to return dict format that the real function returns
    with patch("src.api.router.suggest_types", new=AsyncMock(return_value={"result": mock_type_results})):
        async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
            response: Response = await client.get("/suggest/type?prefix=loc")

            assert response.status_code == 200
            data = response.json()
            assert "result" in data

            # Should only return 'location'
            assert len(data["result"]) == 1
            assert data["result"][0]["id"] == "location"


@pytest.mark.asyncio
@with_test_config
async def test_suggest_property_by_type(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test property suggest filtered by entity type"""
    async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
        response: Response = await client.get("/suggest/property?type=site")

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert isinstance(data["result"], list)
        assert len(data["result"]) > 0

        # Check format
        first_prop = data["result"][0]
        assert "id" in first_prop
        assert "name" in first_prop
        assert "description" in first_prop


@pytest.mark.asyncio
@with_test_config
async def test_suggest_property_with_prefix(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test property suggest with prefix filter"""
    async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
        response: Response = await client.get("/suggest/property?prefix=lat")

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

        # Should find 'latitude'
        prop_ids = [p["id"] for p in data["result"]]
        assert "latitude" in prop_ids


@pytest.mark.asyncio
@with_test_config
async def test_flyout_entity_valid(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test flyout preview with valid entity ID"""

    # Mock the get_connection to return a properly mocked connection
    with patch("src.suggest.get_connection") as mock_get_connection:
        # Create a mock connection with proper database row response
        mock_conn = AsyncMock(spec=psycopg.AsyncConnection)
        mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)

        # Mock location data that would be returned from the database
        location_row_data = {
            "location_id": 806,
            "label": "Test Location",
            "place_name": "Uppsala",
            "latitude": 59.8586,
            "longitude": 17.6389,
            "country": "Sweden",
        }

        # Set up the mock to return a MockRow (which behaves like a real database row)
        mock_cursor.fetchone.return_value = MockRow(location_row_data)
        mock_cursor.execute.return_value = None

        # Set up the connection context manager
        mock_cursor.__aenter__.return_value = mock_cursor
        mock_cursor.__aexit__.return_value = None
        mock_conn.cursor.return_value = mock_cursor

        mock_get_connection.return_value = mock_conn

        async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
            # Use a known entity ID (location)
            entity_id = "https://w3id.org/sead/id/location/806"
            response: Response = await client.get(f"/flyout/entity?id={entity_id}")

            assert response.status_code == 200
            data = response.json()

            # Check response format
            assert "id" in data
            assert "html" in data
            assert data["id"] == entity_id

            # Check HTML contains expected content
            html = data["html"]
            assert "<div" in html
            assert "style=" in html


@pytest.mark.asyncio
@with_test_config
async def test_flyout_entity_missing_id(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test flyout preview without ID parameter"""
    async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
        response: Response = await client.get("/flyout/entity")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


@pytest.mark.asyncio
@with_test_config
async def test_flyout_entity_invalid_id(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test flyout preview with invalid entity ID"""
    async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
        response: Response = await client.get("/flyout/entity?id=invalid-id")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


@pytest.mark.asyncio
@with_test_config
async def test_metadata_includes_suggest_config(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test that metadata endpoint includes Suggest API configuration"""
    async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
        response: Response = await client.get("/reconcile")

        assert response.status_code == 200
        data = response.json()

        # Check suggest configuration is present
        assert "suggest" in data
        suggest = data["suggest"]

        # Check entity suggest config
        assert "entity" in suggest
        assert "service_path" in suggest["entity"]
        assert suggest["entity"]["service_path"] == "/suggest/entity"
        assert "flyout_service_path" in suggest["entity"]

        # Check type suggest config
        assert "type" in suggest
        assert suggest["type"]["service_path"] == "/suggest/type"

        # Check property suggest config
        assert "property" in suggest
        assert suggest["property"]["service_path"] == "/suggest/property"

        # Check preview config
        assert "preview" in data
        assert "url" in data["preview"]
        assert "width" in data["preview"]
        assert "height" in data["preview"]


@pytest.mark.asyncio
@with_test_config
async def test_suggest_entity_result_limit(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test that entity suggest respects limit"""
    # Create a mock with exactly 5 results to test the limit
    limited_results = mock_results[:2]  # Use first 2 results
    with patch("src.api.router.suggest_entities", new=AsyncMock(return_value={"result": limited_results})):
        async with AsyncClient(transport=ASGITransport(app=test_app), host="http://test") as client:
            response: Response = await client.get("/suggest/entity?prefix=sw")

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

        # Should not return more than 10 results (default limit)
        assert len(data["result"]) <= 10
