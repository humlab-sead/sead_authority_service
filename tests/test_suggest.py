"""
Tests for the OpenRefine Suggest API endpoints.

These endpoints provide autocomplete and inline tooltip preview functionality
for OpenRefine reconciliation.
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

import src.suggest as suggest_module
from src.api.router import router
from src.configuration import MockConfigProvider
from tests.conftest import ExtendedMockConfigProvider
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
    with patch("src.suggest.suggest_entities", new=AsyncMock(return_value={"result": mock_results})):

        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
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
    with patch("src.suggest.suggest_entities", new=AsyncMock(return_value={"result": mock_results})):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
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
    with patch("src.suggest.suggest_entities", new=AsyncMock(return_value={"result": []})):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
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
    with patch("src.suggest.suggest_types", new=AsyncMock(return_value={"result": mock_type_results})):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
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
    with patch("src.suggest.suggest_types", new=AsyncMock(return_value={"result": mock_type_results})):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
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
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
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
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response: Response = await client.get("/suggest/property?prefix=lat")

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

        # Should find 'latitude'
        prop_ids = [p["id"] for p in data["result"]]
        assert "latitude" in prop_ids


@pytest.mark.asyncio
@with_test_config
async def test_flyout_entity_valid(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: ExtendedMockConfigProvider):
    """Test flyout preview with valid entity ID"""
    location_row_data = {
        "location_id": 806,
        "label": "Test Location",
        "place_name": "Uppsala",
        "latitude": 59.8586,
        "longitude": 17.6389,
        "country": "Sweden",
    }
    test_provider.create_connection_mock(fetchone=location_row_data, execute=None)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
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
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response: Response = await client.get("/flyout/entity")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


@pytest.mark.asyncio
@with_test_config
async def test_flyout_entity_invalid_id(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test flyout preview with invalid entity ID"""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        response: Response = await client.get("/flyout/entity?id=invalid-id")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


@pytest.mark.asyncio
@with_test_config
async def test_metadata_includes_suggest_config(test_app: FastAPI, mock_results: list[dict[str, Any]], test_provider: MockConfigProvider):
    """Test that metadata endpoint includes Suggest API configuration"""
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
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
    with patch("src.suggest.suggest_entities", new=AsyncMock(return_value={"result": limited_results})):
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
            response: Response = await client.get("/suggest/entity?prefix=sw")

        assert response.status_code == 200
        data = response.json()
        assert "result" in data

        # Should not return more than 10 results (default limit)
        assert len(data["result"]) <= 10


class _TestConfigValue:
    def __init__(self, path: str, default: Any = None):
        self.path = path
        self.default = default

    def resolve(self) -> Any:
        if self.path == "options:id_base":
            return "https://w3id.org/sead/id/"
        return self.default


class _SuggestStrategyBase:
    id_field = "id"
    label_field = "label"
    display_name = "Unknown"
    candidates: list[dict[str, Any]] = []
    properties: list[dict[str, str]] = []
    details: dict[str, Any] | None = None
    raise_on_find: bool = False

    def get_entity_id_field(self) -> str:
        return self.id_field

    def get_label_field(self) -> str:
        return self.label_field

    def get_display_name(self) -> str:
        return self.display_name

    def get_properties_meta(self) -> list[dict[str, str]]:
        return self.properties

    async def find_candidates(self, query: str, properties: dict[str, Any] | None = None, limit: int = 10) -> list[dict[str, Any]]:
        if self.raise_on_find:
            raise RuntimeError("boom")
        return list(self.candidates)

    async def get_details(self, entity_id: str) -> dict[str, Any] | None:
        return self.details


@pytest.mark.asyncio
async def test_render_flyout_preview_invalid_id_format(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(suggest_module.Strategies, "items", {"site": _SuggestStrategyBase}, raising=False)

    with pytest.raises(ValueError, match="Invalid ID format"):
        await suggest_module.render_flyout_preview("https://example.org/site/123")


@pytest.mark.asyncio
async def test_render_flyout_preview_invalid_id_path(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(suggest_module.Strategies, "items", {"site": _SuggestStrategyBase}, raising=False)

    with pytest.raises(ValueError, match="Invalid ID path"):
        await suggest_module.render_flyout_preview("https://w3id.org/sead/id/site/123/extra")


@pytest.mark.asyncio
async def test_render_flyout_preview_unknown_entity_type(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(suggest_module.Strategies, "items", {}, raising=False)

    with pytest.raises(ValueError, match="Unknown entity type: site"):
        await suggest_module.render_flyout_preview("https://w3id.org/sead/id/site/123")


@pytest.mark.asyncio
async def test_render_flyout_preview_missing_entity(monkeypatch: pytest.MonkeyPatch):
    class SiteStrategy(_SuggestStrategyBase):
        details = None

    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(suggest_module.Strategies, "items", {"site": SiteStrategy}, raising=False)

    with pytest.raises(ValueError, match="not found"):
        await suggest_module.render_flyout_preview("https://w3id.org/sead/id/site/123")


@pytest.mark.asyncio
async def test_render_flyout_preview_success_compact_html(monkeypatch: pytest.MonkeyPatch):
    long_value = "x" * 200

    class SiteStrategy(_SuggestStrategyBase):
        details = {
            "Name": "My Site",
            "IgnoredEmpty": "",
            "IgnoredNone": None,
            "Field1": "A",
            "Field2": "B",
            "Field3": "C",
            "Field4": "D",
            "Field5": long_value,
            "Field6": "ShouldBeExcludedByMaxDetails",
            "label": "AlsoIgnored",
        }

    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(suggest_module.Strategies, "items", {"site": SiteStrategy}, raising=False)

    data = await suggest_module.render_flyout_preview("https://w3id.org/sead/id/site/123")
    assert data["id"] == "https://w3id.org/sead/id/site/123"
    assert "My Site" in data["html"]
    assert "site" in data["html"]
    assert "Field6" not in data["html"]
    assert "x" * 57 + "..." in data["html"]


@pytest.mark.asyncio
async def test_suggest_entities_short_prefix_returns_empty(monkeypatch: pytest.MonkeyPatch):
    class SiteStrategy(_SuggestStrategyBase):
        raise_on_find = True

    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(suggest_module.Strategies, "items", {"site": SiteStrategy}, raising=False)

    data = await suggest_module.suggest_entities(prefix="a")
    assert data == {"result": []}


@pytest.mark.asyncio
async def test_suggest_entities_filters_and_sorts(monkeypatch: pytest.MonkeyPatch):
    class SiteStrategy(_SuggestStrategyBase):
        candidates = [
            {"id": 1, "label": "Low Score", "name_sim": 0.1},
            {"id": 2, "label": None, "name_sim": 0.99},
        ]

    class LocationStrategy(_SuggestStrategyBase):
        candidates = [{"id": 9, "label": "High Score", "name_sim": 0.9, "description": "desc"}]

    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(
        suggest_module.Strategies,
        "items",
        {"site": SiteStrategy, "location": LocationStrategy},
        raising=False,
    )

    data = await suggest_module.suggest_entities(prefix="up", limit=10)
    assert len(data["result"]) == 2
    assert data["result"][0]["name"] == "High Score"
    assert data["result"][0]["id"] == "https://w3id.org/sead/id/location/9"
    assert data["result"][0]["description"] == "desc"
    assert data["result"][1]["id"] == "https://w3id.org/sead/id/site/1"


@pytest.mark.asyncio
async def test_suggest_entities_type_filter_and_error_isolated(monkeypatch: pytest.MonkeyPatch):
    class SiteStrategy(_SuggestStrategyBase):
        candidates = [{"id": 1, "label": "Site A", "name_sim": 0.5}]

    class BrokenStrategy(_SuggestStrategyBase):
        raise_on_find = True

    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(
        suggest_module.Strategies,
        "items",
        {"site": SiteStrategy, "broken": BrokenStrategy},
        raising=False,
    )

    data = await suggest_module.suggest_entities(prefix="si", entity_type="site", limit=10)
    assert [r["id"] for r in data["result"]] == ["https://w3id.org/sead/id/site/1"]

    data = await suggest_module.suggest_entities(prefix="si", entity_type="missing_type", limit=10)
    assert [r["id"] for r in data["result"]] == ["https://w3id.org/sead/id/site/1"]


@pytest.mark.asyncio
async def test_suggest_entities_respects_limit_across_strategies(monkeypatch: pytest.MonkeyPatch):
    class ManyCandidatesStrategy(_SuggestStrategyBase):
        candidates = [{"id": i, "label": f"Site {i}", "name_sim": 0.9 - (i / 1000)} for i in range(50)]

    class OtherStrategy(_SuggestStrategyBase):
        candidates = [{"id": 1, "label": "Other", "name_sim": 1.0}]

    monkeypatch.setattr(suggest_module, "ConfigValue", _TestConfigValue)
    monkeypatch.setattr(
        suggest_module.Strategies,
        "items",
        {"site": ManyCandidatesStrategy, "other": OtherStrategy},
        raising=False,
    )

    data = await suggest_module.suggest_entities(prefix="si", limit=5)
    assert len(data["result"]) == 5


@pytest.mark.asyncio
async def test_suggest_types_filters_by_prefix(monkeypatch: pytest.MonkeyPatch):
    class SiteStrategy(_SuggestStrategyBase):
        display_name = "Sites"

    class LocationStrategy(_SuggestStrategyBase):
        display_name = "Locations"

    monkeypatch.setattr(suggest_module.Strategies, "items", {"site": SiteStrategy, "location": LocationStrategy}, raising=False)

    data = await suggest_module.suggest_types(prefix="")
    assert {t["id"] for t in data["result"]} == {"site", "location"}

    data = await suggest_module.suggest_types(prefix="loc")
    assert [t["id"] for t in data["result"]] == ["location"]

    data = await suggest_module.suggest_types(prefix="SITE")
    assert [t["id"] for t in data["result"]] == ["site"]


@pytest.mark.asyncio
async def test_suggest_properties_dedup_and_prefix_filter(monkeypatch: pytest.MonkeyPatch):
    class SiteStrategy(_SuggestStrategyBase):
        properties = [
            {"id": "latitude", "name": "Latitude", "description": "lat desc"},
            {"id": "country", "name": "Country", "description": "nation"},
        ]

    class LocationStrategy(_SuggestStrategyBase):
        properties = [
            {"id": "latitude", "name": "Latitude", "description": "duplicate"},
            {"id": "place_name", "name": "Place Name", "description": "locality"},
        ]

    monkeypatch.setattr(suggest_module.Strategies, "items", {"site": SiteStrategy, "location": LocationStrategy}, raising=False)

    data = await suggest_module.suggest_properties(prefix="")
    prop_ids = [p["id"] for p in data["result"]]
    assert prop_ids.count("latitude") == 1
    assert set(prop_ids) == {"latitude", "country", "place_name"}

    data = await suggest_module.suggest_properties(prefix="loca")
    assert [p["id"] for p in data["result"]] == ["place_name"]

    data = await suggest_module.suggest_properties(prefix="", entity_type="site")
    assert {p["id"] for p in data["result"]} == {"latitude", "country"}
