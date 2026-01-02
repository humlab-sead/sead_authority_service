"""Comprehensive tests for AdministrativeRegionReconciliationStrategy."""

from src.strategies.administrative_region import AdministrativeRegionReconciliationStrategy
from src.strategies.location import LocationReconciliationStrategy
from src.strategies.query import BaseRepository
from src.strategies.strategy import Strategies
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config


class TestAdministrativeRegionBasics:
    """Test basic initialization and registration of administrative region strategy."""

    @with_test_config
    def test_inherits_from_location_strategy(self, test_provider: ExtendedMockConfigProvider):
        """Verify inheritance from LocationReconciliationStrategy."""
        strategy = AdministrativeRegionReconciliationStrategy()
        assert isinstance(strategy, LocationReconciliationStrategy)

    @with_test_config
    def test_registry_key_attribute(self, test_provider: ExtendedMockConfigProvider):
        """Verify _registry_key attribute is set by decorator."""
        assert hasattr(AdministrativeRegionReconciliationStrategy, "_registry_key")
        assert AdministrativeRegionReconciliationStrategy._registry_key == "administrative_region"

    @with_test_config
    def test_is_registered(self, test_provider: ExtendedMockConfigProvider):
        """Verify strategy is registered in global registry."""
        assert Strategies.is_registered("administrative_region")
        assert Strategies.get("administrative_region") == AdministrativeRegionReconciliationStrategy

    @with_test_config
    def test_key_property(self, test_provider: ExtendedMockConfigProvider):
        """Test key property returns correct value."""
        strategy = AdministrativeRegionReconciliationStrategy()
        assert strategy.key == "administrative_region"

    @with_test_config
    def test_entity_config_loaded(self, test_provider: ExtendedMockConfigProvider):
        """Test entity_config is loaded from configuration."""
        strategy = AdministrativeRegionReconciliationStrategy()

        # entity_config comes from ConfigValue resolution
        assert hasattr(strategy, "entity_config")
        assert isinstance(strategy.entity_config, dict)

    @with_test_config
    def test_get_repository(self, test_provider: ExtendedMockConfigProvider):
        """Test get_repository returns a BaseRepository instance."""
        strategy = AdministrativeRegionReconciliationStrategy()
        repository = strategy.get_repository()

        assert repository is not None
        assert isinstance(repository, BaseRepository)


class TestAdministrativeRegionSpecification:
    """Test specification resolution and structure for administrative regions."""

    @with_test_config
    def test_specification_loaded(self, test_provider: ExtendedMockConfigProvider):
        """Verify specification is loaded from configuration."""
        strategy = AdministrativeRegionReconciliationStrategy()
        assert hasattr(strategy, "specification")
        assert isinstance(strategy.specification, dict)

    @with_test_config
    def test_specification_has_required_fields(self, test_provider: ExtendedMockConfigProvider):
        """Verify specification has all required fields."""
        strategy = AdministrativeRegionReconciliationStrategy()
        spec = strategy.specification

        assert "key" in spec
        assert "id_field" in spec
        assert "label_field" in spec

    @with_test_config
    def test_specification_key(self, test_provider: ExtendedMockConfigProvider):
        """Verify the strategy key is correct."""
        strategy = AdministrativeRegionReconciliationStrategy()
        assert strategy.specification["key"] == "administrative_region"

    @with_test_config
    def test_get_entity_id_field(self, test_provider: ExtendedMockConfigProvider):
        """Test getting entity ID field name."""
        strategy = AdministrativeRegionReconciliationStrategy()
        id_field = strategy.get_entity_id_field()
        assert isinstance(id_field, str)
        assert len(id_field) > 0

    @with_test_config
    def test_get_label_field(self, test_provider: ExtendedMockConfigProvider):
        """Test getting label field name."""
        strategy = AdministrativeRegionReconciliationStrategy()
        label_field = strategy.get_label_field()
        assert isinstance(label_field, str)
        assert len(label_field) > 0

    @with_test_config
    def test_get_display_name(self, test_provider: ExtendedMockConfigProvider):
        """Test getting display name."""
        strategy = AdministrativeRegionReconciliationStrategy()
        display_name = strategy.get_display_name()
        assert isinstance(display_name, str)
        assert "administrative" in display_name.lower() or "region" in display_name.lower()


class TestAdministrativeRegionMethods:
    """Test inherited methods from LocationReconciliationStrategy."""

    @with_test_config
    def test_get_id_path(self, test_provider: ExtendedMockConfigProvider):
        """Test get_id_path returns strategy key."""
        strategy = AdministrativeRegionReconciliationStrategy()
        assert strategy.get_id_path() == "administrative_region"

    @with_test_config
    def test_get_properties_meta(self, test_provider: ExtendedMockConfigProvider):
        """Test getting properties metadata."""
        strategy = AdministrativeRegionReconciliationStrategy()
        props = strategy.get_properties_meta()
        assert isinstance(props, list)

    @with_test_config
    def test_get_property_settings(self, test_provider: ExtendedMockConfigProvider):
        """Test getting property settings."""
        strategy = AdministrativeRegionReconciliationStrategy()
        settings = strategy.get_property_settings()
        assert isinstance(settings, dict)

    @with_test_config
    def test_as_candidate_basic(self, test_provider: ExtendedMockConfigProvider):
        """Test converting entity data to candidate format."""
        strategy = AdministrativeRegionReconciliationStrategy()

        entity_data = {
            strategy.get_entity_id_field(): "123",
            strategy.get_label_field(): "Test Region",
            "name_sim": 0.95,
        }

        candidate = strategy.as_candidate(entity_data, "test query")

        assert "id" in candidate
        assert "name" in candidate
        assert "score" in candidate
        assert "match" in candidate
        assert "type" in candidate
        assert candidate["name"] == "Test Region"

    @with_test_config
    def test_as_candidate_with_distance(self, test_provider: ExtendedMockConfigProvider):
        """Test candidate includes distance when available."""
        strategy = AdministrativeRegionReconciliationStrategy()

        entity_data = {
            strategy.get_entity_id_field(): "123",
            strategy.get_label_field(): "Test Region",
            "name_sim": 0.75,
            "distance_km": 25.6789,
        }

        candidate = strategy.as_candidate(entity_data, "test")

        assert "distance_km" in candidate
        assert candidate["distance_km"] == 25.68  # Rounded to 2 decimals


class TestAdministrativeRegionIntegration:
    """Integration tests for administrative region strategy."""

    @with_test_config
    def test_strategy_accessible_via_registry(self, test_provider: ExtendedMockConfigProvider):
        """Test strategy can be retrieved from global registry."""
        strategy_class = Strategies.get("administrative_region")
        strategy = strategy_class()

        assert isinstance(strategy, AdministrativeRegionReconciliationStrategy)
        assert strategy.key == "administrative_region"

    @with_test_config
    def test_multiple_instances_independent(self, test_provider: ExtendedMockConfigProvider):
        """Test multiple instances are independent."""
        strategy1 = AdministrativeRegionReconciliationStrategy()
        strategy2 = AdministrativeRegionReconciliationStrategy()

        # Instances are different objects
        assert strategy1 is not strategy2
        # But share the same specification reference
        assert strategy1.key == strategy2.key

    @with_test_config
    def test_inherits_location_strategy_methods(self, test_provider: ExtendedMockConfigProvider):
        """Verify administrative region inherits all location strategy methods."""
        strategy = AdministrativeRegionReconciliationStrategy()

        # Check inherited methods exist
        assert hasattr(strategy, "get_entity_id_field")
        assert hasattr(strategy, "get_label_field")
        assert hasattr(strategy, "get_repository")
        assert hasattr(strategy, "get_id_path")
        assert hasattr(strategy, "get_display_name")
        assert hasattr(strategy, "as_candidate")

        # Verify they're callable
        assert callable(strategy.get_entity_id_field)
        assert callable(strategy.get_label_field)
        assert callable(strategy.get_repository)


class TestAdministrativeRegionDistinctionFromCountry:
    """Test that administrative region is distinct from country strategy."""

    @with_test_config
    def test_different_registry_keys(self, test_provider: ExtendedMockConfigProvider):
        """Administrative region has different key than country."""
        admin_strategy = AdministrativeRegionReconciliationStrategy()

        # Import country strategy
        from src.strategies.country import CountryReconciliationStrategy

        country_strategy = CountryReconciliationStrategy()

        assert admin_strategy.key == "administrative_region"
        assert country_strategy.key == "country"
        assert admin_strategy.key != country_strategy.key

    @with_test_config
    def test_both_registered_separately(self, test_provider: ExtendedMockConfigProvider):
        """Both administrative_region and country are registered."""
        assert Strategies.is_registered("administrative_region")
        assert Strategies.is_registered("country")

        admin_class = Strategies.get("administrative_region")
        country_class = Strategies.get("country")

        assert admin_class != country_class
        assert admin_class == AdministrativeRegionReconciliationStrategy

    @with_test_config
    def test_both_inherit_from_location(self, test_provider: ExtendedMockConfigProvider):
        """Both strategies inherit from LocationReconciliationStrategy."""
        from src.strategies.country import CountryReconciliationStrategy

        admin_strategy = AdministrativeRegionReconciliationStrategy()
        country_strategy = CountryReconciliationStrategy()

        assert isinstance(admin_strategy, LocationReconciliationStrategy)
        assert isinstance(country_strategy, LocationReconciliationStrategy)


class TestAdministrativeRegionEdgeCases:
    """Test edge cases and error handling."""

    @with_test_config
    def test_handles_missing_repository_initially(self, test_provider: ExtendedMockConfigProvider):
        """Test repository is None before get_repository is called."""
        strategy = AdministrativeRegionReconciliationStrategy()
        assert strategy.repository is None

        # Getting repository should create it
        repo = strategy.get_repository()
        assert repo is not None
        assert strategy.repository is not None

    @with_test_config
    def test_repository_reused_on_subsequent_calls(self, test_provider: ExtendedMockConfigProvider):
        """Test repository instance is reused."""
        strategy = AdministrativeRegionReconciliationStrategy()

        repo1 = strategy.get_repository()
        repo2 = strategy.get_repository()

        # Should be the same instance
        assert repo1 is repo2

    @with_test_config
    def test_as_candidate_high_score_match(self, test_provider: ExtendedMockConfigProvider):
        """Test high similarity score results in match=True."""
        strategy = AdministrativeRegionReconciliationStrategy()

        entity_data = {
            strategy.get_entity_id_field(): "1",
            strategy.get_label_field(): "Test",
            "name_sim": 0.95,  # High score
        }

        candidate = strategy.as_candidate(entity_data, "test")
        assert candidate["match"] is True

    @with_test_config
    def test_as_candidate_low_score_no_match(self, test_provider: ExtendedMockConfigProvider):
        """Test low similarity score results in match=False."""
        strategy = AdministrativeRegionReconciliationStrategy()

        entity_data = {
            strategy.get_entity_id_field(): "1",
            strategy.get_label_field(): "Different",
            "name_sim": 0.3,  # Low score
        }

        candidate = strategy.as_candidate(entity_data, "test")
        assert candidate["match"] is False

    @with_test_config
    def test_as_candidate_exact_match_case_insensitive(self, test_provider: ExtendedMockConfigProvider):
        """Test exact label match (case insensitive) results in match=True."""
        strategy = AdministrativeRegionReconciliationStrategy()

        entity_data = {
            strategy.get_entity_id_field(): "1",
            strategy.get_label_field(): "Test Region",
            "name_sim": 0.5,  # Even with low similarity
        }

        candidate = strategy.as_candidate(entity_data, "TEST REGION")
        assert candidate["match"] is True


class TestAdministrativeRegionRepositorySetup:
    """Test repository initialization and configuration."""

    @with_test_config
    def test_repository_cls_inherited(self, test_provider: ExtendedMockConfigProvider):
        """Test repository_cls is inherited from parent."""
        strategy = AdministrativeRegionReconciliationStrategy()
        assert hasattr(strategy, "repository_instance_or_cls")

    @with_test_config
    def test_repository_creation_with_specification(self, test_provider: ExtendedMockConfigProvider):
        """Test repository is created with strategy specification."""
        strategy = AdministrativeRegionReconciliationStrategy()
        repo = strategy.get_repository()

        # Repository should have specification
        assert hasattr(repo, "specification")
        assert repo.specification == strategy.specification

    @with_test_config
    def test_repository_type(self, test_provider: ExtendedMockConfigProvider):
        """Test repository is correct type."""
        strategy = AdministrativeRegionReconciliationStrategy()
        repo = strategy.get_repository()

        # Should be BaseRepository or subclass
        assert isinstance(repo, BaseRepository)
