import pytest

from src.metadata import (
    _compile_property_settings,
    _get_default_types,
    _get_supported_types,
    get_reconcile_properties,
    get_reconciliation_metadata,
)
from src.strategies.configured_classifier import CLASSIFIER_KEYS
from src.strategies.location import LocationReconciliationStrategy
from src.strategies.strategy import Strategies
from tests.decorators import with_test_config

# pylint: disable=redefined-outer-name, redefined-builtin


class FakeSiteStrategy:
    support_status = "supported"

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
    support_status = "excluded"

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


def _registry_with_support_status() -> DummyRegistry:
    class FakeLocationStrategy(FakeSiteStrategy):
        support_status = "supported"

    return DummyRegistry(
        {
            "site": FakeSiteStrategy,
            "taxon": FakeTaxonStrategy,
            "location": FakeLocationStrategy,
        }
    )


def test_supported_types_come_from_registration_status():
    supported = _get_supported_types(_registry_with_support_status())

    assert supported == ["location", "site"]
    assert len(supported) == len(set(supported))


def test_excluded_type_is_published_but_not_supported():
    registry = _registry_with_support_status()
    default_types = _get_default_types(registry)

    published_ids = {entry["id"] for entry in default_types}
    supported = _get_supported_types(registry)

    assert "taxon" in published_ids
    assert "taxon" not in supported


def test_every_registered_strategy_declares_a_valid_support_status():
    for key, strategy_cls in Strategies.items.items():
        assert getattr(strategy_cls, "support_status", None) in {"supported", "excluded"}, key


@with_test_config
def test_manifest_publishes_every_approved_classifier(test_provider):  # pylint: disable=unused-argument
    supported = _get_supported_types(Strategies)
    published_ids = {entry["id"] for entry in _get_default_types(Strategies)}

    for key in CLASSIFIER_KEYS:
        assert key in supported
        assert key in published_ids

    assert len(supported) == len(set(supported))
    for excluded_key in ("abundance_element_group", "coordinate_method_dimension", "value_qualifier_symbol"):
        assert excluded_key not in supported
        assert excluded_key not in published_ids


@with_test_config
def test_reconciliation_metadata_adds_supported_types_only(test_provider):  # pylint: disable=unused-argument
    registry = _registry_with_support_status()

    metadata = get_reconciliation_metadata(registry, "http://testserver/")

    assert metadata["reconciliation"]["supportedTypes"] == ["location", "site"]
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
    registry = DummyRegistry({"feature_type": Strategies.items["feature_type"], "location": LocationReconciliationStrategy})

    assert get_reconcile_properties(registry, entity_type="feature_type") == []
    assert [prop["id"] for prop in get_reconcile_properties(registry, entity_type="location")] == ["place_name"]
    compiled = _compile_property_settings(registry)
    assert [(entry["name"], entry["entity_types"]) for entry in compiled] == [("place_name", ["location"])]
