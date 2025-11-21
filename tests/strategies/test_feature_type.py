"""Unit tests for FeatureTypeReconciliationStrategy"""

import pytest

from src.strategies.feature_type import (
    FeatureTypeReconciliationStrategy,
    FeatureTypeRepository,
)
from tests.conftest import ExtendedMockConfigProvider, MockRow
from tests.decorators import with_test_config

# pylint: disable=unused-argument


class TestFeatureTypeReconciliationStrategy:
    """Test suite for FeatureTypeReconciliationStrategy"""

    @with_test_config
    def test_initialization(self, test_provider: ExtendedMockConfigProvider):
        """Test strategy initialization with default specification"""
        strategy = FeatureTypeReconciliationStrategy()

        assert isinstance(strategy.specification, dict)
        assert strategy.get_entity_id_field() == "feature_type_id"
        assert strategy.get_label_field() == "label"
        assert strategy.get_id_path() == "feature_type"
        assert strategy.get_display_name() == "Feature Types"

    @with_test_config
    def test_initialization_with_custom_specification(self, test_provider: ExtendedMockConfigProvider):
        """Test strategy initialization with custom specification"""
        custom_spec = {
            "key": "custom_feature_type",
            "display_name": "Custom Feature Types",
            "id_field": "custom_id",
            "label_field": "custom_label",
            "properties": [],
            "property_settings": {},
            "sql_queries": {},
        }

        strategy = FeatureTypeReconciliationStrategy(specification=custom_spec)

        assert strategy.specification == custom_spec
        assert strategy.get_entity_id_field() == "custom_id"
        assert strategy.get_label_field() == "custom_label"

    @with_test_config
    def test_repository_initialization(self, test_provider: ExtendedMockConfigProvider):
        """Test that repository is initialized correctly"""
        strategy = FeatureTypeReconciliationStrategy()
        proxy = strategy.get_repository()

        assert isinstance(proxy, FeatureTypeRepository)
        assert isinstance(proxy.specification, dict)

    @with_test_config
    @pytest.mark.asyncio
    async def test_get_details_success(self, test_provider: ExtendedMockConfigProvider):
        """Test fetching details for a specific feature type"""
        mock_details = MockRow(
            {
                "ID": 1,
                "Feature Type Name": "Archaeological Feature",
                "Description": "A feature of archaeological significance",
            }
        )

        test_provider.create_connection_mock(fetchone=mock_details)

        strategy = FeatureTypeReconciliationStrategy()
        details = await strategy.get_details("1")

        assert details is not None
        assert details["ID"] == 1
        assert details["Feature Type Name"] == "Archaeological Feature"
        assert details["Description"] == "A feature of archaeological significance"

    @with_test_config
    @pytest.mark.asyncio
    async def test_get_details_not_found(self, test_provider: ExtendedMockConfigProvider):
        """Test fetching details for non-existent feature type"""
        test_provider.create_connection_mock(fetchone=None)

        strategy = FeatureTypeReconciliationStrategy()
        details = await strategy.get_details("999")

        assert details is None

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_basic(self, test_provider: ExtendedMockConfigProvider):
        """Test finding candidates with basic fuzzy matching"""
        mock_candidates = [
            MockRow(
                {
                    "feature_type_id": 1,
                    "label": "Archaeological Feature",
                    "name_sim": 0.95,
                }
            ),
            MockRow(
                {
                    "feature_type_id": 2,
                    "label": "Architectural Feature",
                    "name_sim": 0.85,
                }
            ),
        ]

        test_provider.create_connection_mock(fetchall=mock_candidates)

        strategy = FeatureTypeReconciliationStrategy()
        candidates = await strategy.find_candidates("archaeological", limit=10)

        assert len(candidates) == 2
        assert candidates[0]["feature_type_id"] == 1
        assert candidates[0]["label"] == "Archaeological Feature"
        assert candidates[0]["name_sim"] == 0.95
        assert candidates[1]["feature_type_id"] == 2
        assert candidates[1]["name_sim"] == 0.85

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_sorting(self, test_provider: ExtendedMockConfigProvider):
        """Test that candidates are sorted by similarity score"""
        mock_candidates = [
            MockRow({"feature_type_id": 1, "label": "Low Match", "name_sim": 0.65}),
            MockRow({"feature_type_id": 2, "label": "High Match", "name_sim": 0.95}),
            MockRow({"feature_type_id": 3, "label": "Medium Match", "name_sim": 0.80}),
        ]

        test_provider.create_connection_mock(fetchall=mock_candidates)

        strategy = FeatureTypeReconciliationStrategy()
        candidates = await strategy.find_candidates("test", limit=10)

        # Should be sorted by name_sim in descending order
        assert len(candidates) == 3
        assert candidates[0]["name_sim"] == 0.95
        assert candidates[1]["name_sim"] == 0.80
        assert candidates[2]["name_sim"] == 0.65

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_limit(self, test_provider: ExtendedMockConfigProvider):
        """Test that candidate limit is respected"""
        mock_candidates = [MockRow({"feature_type_id": i, "label": f"Feature {i}", "name_sim": 0.9 - i * 0.1}) for i in range(1, 11)]

        test_provider.create_connection_mock(fetchall=mock_candidates)

        strategy = FeatureTypeReconciliationStrategy()
        candidates = await strategy.find_candidates("test", limit=5)

        assert len(candidates) == 5
        assert all("name_sim" in c for c in candidates)

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_empty_result(self, test_provider: ExtendedMockConfigProvider):
        """Test finding candidates when no matches exist"""
        test_provider.create_connection_mock(fetchall=[])

        strategy = FeatureTypeReconciliationStrategy()
        candidates = await strategy.find_candidates("nonexistent", limit=10)

        assert candidates == []

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_with_properties(self, test_provider: ExtendedMockConfigProvider):
        """Test finding candidates with additional properties"""
        mock_candidates = [
            MockRow(
                {
                    "feature_type_id": 1,
                    "label": "Test Feature",
                    "name_sim": 0.90,
                }
            )
        ]

        test_provider.create_connection_mock(fetchall=mock_candidates)

        strategy = FeatureTypeReconciliationStrategy()
        properties = {"description": "Test description"}
        candidates = await strategy.find_candidates("test", properties=properties, limit=10)

        assert len(candidates) == 1
        assert candidates[0]["feature_type_id"] == 1

    @with_test_config
    def test_as_candidate_basic(self, test_provider: ExtendedMockConfigProvider):
        """Test converting entity data to OpenRefine candidate format"""
        strategy = FeatureTypeReconciliationStrategy()

        entity_data = {
            "feature_type_id": 1,
            "label": "Archaeological Feature",
            "name_sim": 0.85,
        }

        candidate = strategy.as_candidate(entity_data, "archaeological")

        assert "id" in candidate
        assert candidate["id"].endswith("feature_type/1")
        assert candidate["name"] == "Archaeological Feature"
        assert candidate["score"] == 85.0
        assert candidate["match"] is False
        assert len(candidate["type"]) == 1
        assert candidate["type"][0]["name"] == "Archaeological Feature"

    @with_test_config
    def test_as_candidate_exact_match(self, test_provider: ExtendedMockConfigProvider):
        """Test candidate with exact label match"""
        strategy = FeatureTypeReconciliationStrategy()

        entity_data = {
            "feature_type_id": 1,
            "label": "Archaeological Feature",
            "name_sim": 0.75,
        }

        candidate = strategy.as_candidate(entity_data, "archaeological feature")

        assert candidate["match"] is True  # Exact match despite lower score

    @with_test_config
    def test_as_candidate_auto_accept(self, test_provider: ExtendedMockConfigProvider):
        """Test candidate with score above auto-accept threshold"""
        strategy = FeatureTypeReconciliationStrategy()

        entity_data = {
            "feature_type_id": 1,
            "label": "Archaeological Feature",
            "name_sim": 0.90,
        }

        candidate = strategy.as_candidate(entity_data, "archaeological")

        assert candidate["match"] is True  # Above threshold (0.85)
        assert candidate["score"] == 90.0

    @with_test_config
    def test_get_properties_meta(self, test_provider: ExtendedMockConfigProvider):
        """Test retrieving properties metadata"""
        strategy = FeatureTypeReconciliationStrategy()
        properties = strategy.get_properties_meta()

        assert isinstance(properties, list)
        assert properties == []

    @with_test_config
    def test_get_property_settings(self, test_provider: ExtendedMockConfigProvider):
        """Test retrieving property settings"""
        strategy = FeatureTypeReconciliationStrategy()
        settings = strategy.get_property_settings()

        assert isinstance(settings, dict)
        assert settings == {}

    @with_test_config
    def test_key_property(self, test_provider: ExtendedMockConfigProvider):
        """Test that key property returns correct value after registration"""
        strategy = FeatureTypeReconciliationStrategy()

        # After registration via @Strategies.register decorator
        assert strategy.key == "feature_type"

    @with_test_config
    @pytest.mark.asyncio
    async def test_proxy_reuse(self, test_provider: ExtendedMockConfigProvider):
        """Test that proxy instance is reused across calls"""
        strategy = FeatureTypeReconciliationStrategy()

        proxy1 = strategy.get_repository()
        proxy2 = strategy.get_repository()

        assert proxy1 is proxy2  # Same instance

    @with_test_config
    @pytest.mark.asyncio
    async def test_database_error_handling(self, test_provider: ExtendedMockConfigProvider):
        """Test handling of database errors during operations"""
        test_provider.create_connection_mock(fetchone=Exception("Database connection failed"))

        strategy = FeatureTypeReconciliationStrategy()

        with pytest.raises(Exception) as exc_info:
            await strategy.get_details("1")

        # assert "Database connection failed" in str(exc_info.value)
