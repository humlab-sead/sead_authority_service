import pytest

from src.metadata import _compile_property_settings, get_reconcile_properties

# pylint: disable=redefined-outer-name, redefined-builtin


class FakeSiteStrategy:
    def __init__(self):
        pass

    def get_properties_meta(self):
        return [
            {"id": "place_name", "name": "Place Name", "type": "string", "description": "Place"},
            {"id": "latitude", "name": "Latitude", "type": "number", "description": "Latitude"},
        ]

    def get_property_settings(self):
        return {"latitude": {"min": -90.0, "max": 90.0, "precision": 6}}

    def get_id_path(self):
        return "site"


class FakeTaxonStrategy:
    def __init__(self):
        pass

    def get_properties_meta(self):
        return [
            {"id": "scientific_name", "name": "Scientific Name", "type": "string", "description": "Scientific name"},
            {"id": "place_name", "name": "Place Name", "type": "string", "description": "Place"},
        ]

    def get_property_settings(self):
        return {}

    def get_id_path(self):
        return "taxon"


class DummyRegistry:
    def __init__(self, items):
        self.items = items


@pytest.fixture
def strategies():
    return DummyRegistry({"site": FakeSiteStrategy, "taxon": FakeTaxonStrategy})


def test_get_reconcile_properties_no_type(strategies):
    props = get_reconcile_properties(strategies)
    # Expect combined properties from both strategies
    ids = {p["id"] for p in props}
    assert "place_name" in ids
    assert "latitude" in ids
    assert "scientific_name" in ids
    assert len(props) == 4  # two from site, two from taxon


def test_get_reconcile_properties_with_type_site(strategies):
    props = get_reconcile_properties(strategies, entity_type="site")
    # When filtered by site we expect the site's properties only
    ids = {p["id"] for p in props}
    assert ids == {"place_name", "latitude"}


def test_get_reconcile_properties_unknown_type_returns_empty(strategies):
    props = get_reconcile_properties(strategies, entity_type="unknown")
    assert props == []


def test_get_reconcile_properties_query_filter(strategies):
    props = get_reconcile_properties(strategies, query="scientific")
    assert len(props) == 1
    assert props[0]["id"] == "scientific_name"


def test_compile_property_settings_dedup_and_entity_types(strategies):
    compiled = _compile_property_settings(strategies)
    # place_name should be present once and have both entity_types
    place = next((p for p in compiled if p["name"] == "place_name"), None)
    assert place is not None
    assert sorted(place["entity_types"]) == ["site", "taxon"]
    # latitude should include settings from site strategy
    lat = next((p for p in compiled if p["name"] == "latitude"), None)
    assert lat is not None
    assert lat["settings"] == {"min": -90.0, "max": 90.0, "precision": 6}
