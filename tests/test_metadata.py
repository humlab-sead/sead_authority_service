import pytest

from src.metadata import (
    SUPPORTED_RECONCILIATION_TYPES,
    _compile_property_settings,
    _get_default_types,
    _get_supported_types,
    get_reconcile_properties,
    get_reconciliation_metadata,
)
from src.strategies.feature_type import FeatureTypeReconciliationStrategy
from src.strategies.location import LocationReconciliationStrategy
from tests.decorators import with_test_config

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

    def get_display_name(self):
        return "Sites"


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

    def get_display_name(self):
        return "Taxa"


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
    assert len(props) == 3  # two from site, two from taxon


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


def _registered_strategies(**overrides) -> DummyRegistry:
    """Build a registry containing every declared supported type."""
    items: dict[str, type] = {type_id: FakeSiteStrategy for type_id in SUPPORTED_RECONCILIATION_TYPES}
    items.update(overrides)
    return DummyRegistry(items)


def test_supported_types_are_declared_once_and_published():
    registry = _registered_strategies(taxon=FakeTaxonStrategy)
    default_types = _get_default_types(registry)

    supported = _get_supported_types(default_types)

    assert supported == list(SUPPORTED_RECONCILIATION_TYPES)
    assert len(supported) == len(set(supported))
    published_ids = {entry["id"] for entry in default_types}
    assert set(supported) <= published_ids


def test_registered_placeholder_type_stays_openrefine_only():
    registry = _registered_strategies(taxon=FakeTaxonStrategy)
    default_types = _get_default_types(registry)

    published_ids = {entry["id"] for entry in default_types}
    supported = _get_supported_types(default_types)

    assert "taxon" in published_ids
    assert "taxon" not in supported


def test_declared_supported_type_must_be_registered():
    items: dict[str, type] = {type_id: FakeSiteStrategy for type_id in SUPPORTED_RECONCILIATION_TYPES if type_id != "location"}
    default_types = _get_default_types(DummyRegistry(items))

    with pytest.raises(ValueError, match="location"):
        _get_supported_types(default_types)


@with_test_config
def test_reconciliation_metadata_adds_supported_types_only(test_provider):  # pylint: disable=unused-argument
    registry = _registered_strategies(taxon=FakeTaxonStrategy)

    metadata = get_reconciliation_metadata(registry, "http://testserver/")

    assert metadata["reconciliation"]["supportedTypes"] == list(SUPPORTED_RECONCILIATION_TYPES)
    assert [entry["id"] for entry in metadata["defaultTypes"]].count("taxon") == 1
    # Existing OpenRefine fields stay available.
    assert metadata["view"]["url"] == "http://testserver/reconcile/preview?id={{id}}"
    assert metadata["preview"]["url"] == "http://testserver/reconcile/preview?id={{id}}"
    assert metadata["suggest"]["entity"]["service_path"] == "/suggest/entity"
    assert metadata["extend"]["propose_properties"]["service_path"] == "/properties"
    compiled_names = {entry["name"] for entry in metadata["extend"]["property_settings"]}
    assert {"place_name", "latitude", "scientific_name"} <= compiled_names


@with_test_config
def test_real_strategies_declare_their_own_properties(test_provider):  # pylint: disable=unused-argument
    registry = DummyRegistry({"feature_type": FeatureTypeReconciliationStrategy, "location": LocationReconciliationStrategy})

    assert get_reconcile_properties(registry, entity_type="feature_type") == []
    assert [prop["id"] for prop in get_reconcile_properties(registry, entity_type="location")] == ["place_name"]
    compiled = _compile_property_settings(registry)
    assert [(entry["name"], entry["entity_types"]) for entry in compiled] == [("place_name", ["location"])]
