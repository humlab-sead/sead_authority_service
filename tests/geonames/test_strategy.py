"""
Unit tests for GeoNames reconciliation strategy and query proxy.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.configuration import MockConfigProvider
from src.strategies.geonames import SPECIFICATION, GeoNamesQueryProxy, GeoNamesReconciliationStrategy
from tests.decorators import with_test_config

# pylint: disable=unused-argument, protected-access


class TestGeoNamesQueryProxy:
    """Test GeoNamesQueryProxy functionality"""

    @with_test_config
    def test_init_default_config(self, test_provider: MockConfigProvider):
        """Test initialization with default configuration values"""
        test_provider.get_config().update(
            {
                "geonames.username": "test_user",
                "geonames.lang": "sv",
                "geonames.country_bias": "SE",
                "geonames.fuzzy": 0.9,
                "geonames.feature_classes": ["P", "A", "H"],
                "geonames.orderby": "population",
                "geonames.style": "SHORT",
            }
        )

        proxy = GeoNamesQueryProxy(SPECIFICATION)

        assert proxy.username == "test_user"
        assert proxy.lang == "sv"
        assert proxy.country_bias == "SE"
        assert proxy.fuzzy == 0.9
        assert proxy.feature_classes == ("P", "A", "H")
        assert proxy.orderby == "population"
        assert proxy.style == "SHORT"

    @with_test_config
    def test_init_with_kwargs(self, test_provider: MockConfigProvider):
        """Test initialization with explicit kwargs overriding config"""
        test_provider.get_config().update(
            {
                "geonames.username": "config_user",
                "geonames.lang": "en",
            }
        )

        proxy = GeoNamesQueryProxy(
            SPECIFICATION, username="override_user", lang="fr", country_bias="FR", fuzzy=0.7, feature_classes=["P"], orderby="relevance", style="MEDIUM"
        )

        assert proxy.username == "override_user"
        assert proxy.lang == "fr"
        assert proxy.country_bias == "FR"
        assert proxy.fuzzy == 0.7
        assert proxy.feature_classes == ("P",)
        assert proxy.orderby == "relevance"
        assert proxy.style == "MEDIUM"

    @with_test_config
    def test_init_fallback_defaults(self, test_provider: MockConfigProvider):
        """Test initialization with fallback default values when config is empty"""
        # No config values set
        proxy = GeoNamesQueryProxy(SPECIFICATION)

        assert proxy.username == "demo"
        assert proxy.lang == "en"
        assert proxy.country_bias is None
        assert proxy.fuzzy == 0.8
        assert proxy.feature_classes == ("P", "A")
        assert proxy.orderby == "relevance"
        assert proxy.style == "FULL"

    @pytest.mark.asyncio
    @with_test_config
    @patch("src.strategies.geonames.GeoNamesProxy")
    async def test_find_basic(self, mock_proxy_class, test_provider: MockConfigProvider):
        """Test basic find functionality"""
        # Mock response data
        mock_results = [{"geonameId": 2666199, "name": "Umeå", "lat": "63.82842", "lng": "20.25972", "countryName": "Sweden"}]

        mock_proxy = AsyncMock()
        mock_proxy.search.return_value = mock_results
        mock_proxy_class.return_value = mock_proxy

        proxy = GeoNamesQueryProxy(SPECIFICATION, username="test_user")

        result = await proxy.find("Umeå", limit=5)

        # Verify proxy was called with correct parameters
        mock_proxy.search.assert_called_once_with(
            q="Umeå",
            max_rows=5,
            fuzzy=0.8,  # default value
            feature_classes=("P", "A"),  # default value
            country_bias=None,  # default value
            orderby="relevance",  # default value
            style="FULL",  # default value
        )

        assert result == mock_results

    @with_test_config
    @pytest.mark.asyncio
    @patch("src.strategies.geonames.GeoNamesProxy")
    async def test_find_with_custom_config(self, mock_proxy_class, test_provider: MockConfigProvider):
        """Test find with custom configuration"""
        mock_results = []
        mock_proxy = AsyncMock()
        mock_proxy.search.return_value = mock_results
        mock_proxy_class.return_value = mock_proxy

        proxy = GeoNamesQueryProxy(
            SPECIFICATION, username="test_user", fuzzy=0.9, feature_classes=["P", "H"], country_bias="SE", orderby="population", style="SHORT"
        )

        await proxy.find("Stockholm", limit=10)

        mock_proxy.search.assert_called_once_with(
            q="Stockholm", max_rows=10, fuzzy=0.9, feature_classes=("P", "H"), country_bias="SE", orderby="population", style="SHORT"
        )

    @with_test_config
    @pytest.mark.asyncio
    @patch("src.strategies.geonames.GeoNamesProxy")
    async def test_get_details(self, mock_proxy_class, test_provider: MockConfigProvider):
        """Test get_details functionality"""
        mock_details = {"geonameId": 2666199, "name": "Umeå", "lat": "63.82842", "lng": "20.25972", "countryName": "Sweden", "population": 83249}

        mock_proxy = AsyncMock()
        mock_proxy.get_details.return_value = mock_details
        mock_proxy_class.return_value = mock_proxy

        proxy = GeoNamesQueryProxy(SPECIFICATION, username="test_user")

        result = await proxy.get_details("2666199", lang="sv", style="MEDIUM")

        mock_proxy.get_details.assert_called_once_with("2666199", lang="sv", style="MEDIUM")
        assert result == mock_details

    @with_test_config
    @pytest.mark.asyncio
    async def test_fetch_by_alternate_identity_not_implemented(self, test_provider: MockConfigProvider):
        """Test that fetch_by_alternate_identity raises NotImplementedError"""
        proxy = GeoNamesQueryProxy(SPECIFICATION, username="test_user")

        with pytest.raises(NotImplementedError, match="Alternate identity lookup not implemented for GeoNames"):
            await proxy.fetch_by_alternate_identity("some_id")


class TestGeoNamesReconciliationStrategy:
    """Test GeoNamesReconciliationStrategy functionality"""

    @with_test_config
    @patch("src.strategies.geonames.GeoNamesQueryProxy")
    def test_init_default(self, mock_query_proxy_class, test_provider: MockConfigProvider):
        """Test initialization with default specification"""
        mock_proxy = MagicMock()
        mock_query_proxy_class.return_value = mock_proxy

        strategy = GeoNamesReconciliationStrategy()

        mock_query_proxy_class.assert_called_once_with(SPECIFICATION)
        assert strategy.specification == SPECIFICATION

    @with_test_config
    @patch("src.strategies.geonames.GeoNamesQueryProxy")
    def test_init_with_custom_specification(self, mock_query_proxy_class, test_provider: MockConfigProvider):
        """Test initialization with custom specification"""
        custom_spec = {"key": "custom_geonames", "display_name": "Custom GeoNames"}
        mock_proxy = MagicMock()
        mock_query_proxy_class.return_value = mock_proxy

        strategy = GeoNamesReconciliationStrategy(custom_spec)

        mock_query_proxy_class.assert_called_once_with(SPECIFICATION)  # Still uses SPECIFICATION for proxy
        assert strategy.specification == custom_spec

    @with_test_config
    @patch("src.strategies.geonames.GeoNamesQueryProxy")
    def test_init_with_strategy_options(self, mock_query_proxy_class, test_provider: MockConfigProvider):
        """Test initialization with strategy options from config"""
        test_provider.get_config().update({"policy.geonames.geonames.options": {"username": "strategy_user", "lang": "sv", "country_bias": "SE"}})

        mock_proxy = MagicMock()
        mock_query_proxy_class.return_value = mock_proxy

        _ = GeoNamesReconciliationStrategy()

        # Verify proxy was created with strategy options
        mock_query_proxy_class.assert_called_once_with(SPECIFICATION, username="strategy_user", lang="sv", country_bias="SE")

    @with_test_config
    def test_as_candidate_basic(self, test_provider: MockConfigProvider):
        """Test basic candidate conversion"""
        strategy = GeoNamesReconciliationStrategy()

        geonames_data = {
            "geonameId": 2666199,
            "name": "Umeå",
            "adminName1": "Västerbotten",
            "countryName": "Sweden",
            "score": 85.5,
            "population": 83249,
            "fcodeName": "seat of a second-order administrative division",
            "fcl": "P",
            "fcode": "PPLA2",
        }

        result = strategy.as_candidate(geonames_data, "umea")

        assert result["id"] == "2666199"
        assert result["name"] == "Umeå, Västerbotten, Sweden"
        assert result["match"] is False  # "umea" != "Umeå, Västerbotten, Sweden"
        assert result["uri"] == "https://www.geonames.org/2666199"
        assert result["type"] == [{"id": "/location/citytown", "name": "City/Town"}]
        assert "pop 83,249" in result["description"]
        assert isinstance(result["score"], float)
        assert isinstance(result["name_sim"], float)
        assert result["name_sim"] == result["score"] / 100.0

    @with_test_config
    def test_as_candidate_exact_match(self, test_provider: MockConfigProvider):
        """Test candidate conversion with exact match"""
        strategy = GeoNamesReconciliationStrategy()

        geonames_data = {"geonameId": 123, "name": "Stockholm", "countryName": "Sweden"}

        result = strategy.as_candidate(geonames_data, "Stockholm, Sweden")

        assert result["match"] is True  # Case-insensitive exact match
        assert result["name"] == "Stockholm, Sweden"

    @with_test_config
    def test_as_candidate_minimal_data(self, test_provider: MockConfigProvider):
        """Test candidate conversion with minimal data"""
        strategy = GeoNamesReconciliationStrategy()

        geonames_data = {"geonameId": 123, "name": "Test Place"}

        result = strategy.as_candidate(geonames_data, "test")

        assert result["id"] == "123"
        assert result["name"] == "Test Place"
        assert result["description"] == ""  # No population or fcodeName
        assert result["type"] == [{"id": "/location/place", "name": "Place"}]

    @with_test_config
    def test_as_candidate_administrative_area(self, test_provider: MockConfigProvider):
        """Test candidate conversion for administrative area"""
        strategy = GeoNamesReconciliationStrategy()

        geonames_data = {"geonameId": 456, "name": "Västerbotten", "fcl": "A", "fcode": "ADM1", "fcodeName": "first-order administrative division"}

        result = strategy.as_candidate(geonames_data, "vasterbotten")

        assert result["type"] == [{"id": "/location/administrative_area", "name": "Administrative Area"}]

    @with_test_config
    def test_calculate_score_basic(self, test_provider: MockConfigProvider):
        """Test score calculation with basic data"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"score": 80.0, "population": 100000}

        score = strategy._calculate_score(data)

        # Expected: 60 + 40 * min(1.0, (80/100) + (log10(100000)/7))
        # log10(100000) = 5, so (5/7) ≈ 0.714
        # 60 + 40 * min(1.0, 0.8 + 0.714) = 60 + 40 * 1.0 = 100
        assert score == 100.0

    @with_test_config
    def test_calculate_score_no_population(self, test_provider: MockConfigProvider):
        """Test score calculation with no population data"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"score": 60.0, "population": 0}

        score = strategy._calculate_score(data)

        # Expected: 60 + 40 * min(1.0, (60/100) + 0) = 60 + 40 * 0.6 = 84.0
        assert score == 84.0

    @with_test_config
    def test_calculate_score_missing_data(self, test_provider: MockConfigProvider):
        """Test score calculation with missing data"""
        strategy = GeoNamesReconciliationStrategy()

        data = {}  # No score or population

        score = strategy._calculate_score(data)

        # Expected: 60 + 40 * min(1.0, 0 + 0) = 60.0
        assert score == 60.0

    @with_test_config
    def test_calculate_score_high_population(self, test_provider: MockConfigProvider):
        """Test score calculation with very high population"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"score": 50.0, "population": 10000000}  # 10 million

        score = strategy._calculate_score(data)

        # log10(10000000) = 7, so (7/7) = 1.0
        # 60 + 40 * min(1.0, 0.5 + 1.0) = 60 + 40 * 1.0 = 100.0
        assert score == 100.0

    @with_test_config
    def test_generate_description_full(self, test_provider: MockConfigProvider):
        """Test description generation with all data"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"fcodeName": "seat of a first-order administrative division", "population": 1500000}

        description = strategy._generate_description(data)

        assert description == "seat of a first-order administrative division · pop 1,500,000"

    @with_test_config
    def test_generate_description_fcode_fallback(self, test_provider: MockConfigProvider):
        """Test description generation with fcode fallback"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"fcode": "PPLA", "population": 50000}

        description = strategy._generate_description(data)

        assert description == "PPLA · pop 50,000"

    @with_test_config
    def test_generate_description_no_population(self, test_provider: MockConfigProvider):
        """Test description generation without population"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"fcodeName": "populated place", "population": 0}

        description = strategy._generate_description(data)

        assert description == "populated place"

    @with_test_config
    def test_generate_description_minimal(self, test_provider: MockConfigProvider):
        """Test description generation with minimal data"""
        strategy = GeoNamesReconciliationStrategy()

        data = {}

        description = strategy._generate_description(data)

        assert description == ""

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_basic(self, test_provider: MockConfigProvider):
        """Test find_candidates functionality"""
        mock_proxy = AsyncMock()
        mock_geonames_results = [
            {"geonameId": 2666199, "name": "Umeå", "score": 90.0, "population": 83249, "name_sim": 0.9},
            {"geonameId": 2673730, "name": "Stockholm", "score": 85.0, "population": 975551, "name_sim": 0.8},
        ]
        mock_proxy.find.return_value = mock_geonames_results

        strategy = GeoNamesReconciliationStrategy()
        with patch.object(strategy, "get_proxy", return_value=mock_proxy):
            result = await strategy.find_candidates("Swedish cities", limit=5)

        mock_proxy.find.assert_called_once_with("Swedish cities", 5, properties={})

        # Results should be sorted by name_sim in descending order
        assert len(result) == 2
        assert result[0]["name_sim"] >= result[1]["name_sim"]

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_with_properties(self, test_provider: MockConfigProvider):
        """Test find_candidates with properties"""
        mock_proxy = AsyncMock()
        mock_proxy.find.return_value = []

        strategy = GeoNamesReconciliationStrategy()
        properties = {"country": "SE", "feature_class": "P"}

        with patch.object(strategy, "get_proxy", return_value=mock_proxy):
            await strategy.find_candidates("test", properties=properties, limit=3)

        mock_proxy.find.assert_called_once_with("test", 3, properties=properties)

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_limit_applied(self, test_provider: MockConfigProvider):
        """Test that limit is properly applied to results"""
        mock_proxy = AsyncMock()
        # Return more results than limit
        mock_results = [{"geonameId": i, "name": f"Place {i}", "name_sim": 1.0 - i * 0.1} for i in range(10)]
        mock_proxy.find.return_value = mock_results

        strategy = GeoNamesReconciliationStrategy()

        with patch.object(strategy, "get_proxy", return_value=mock_proxy):
            result = await strategy.find_candidates("test", limit=3)

        # Should only return top 3 results
        assert len(result) == 3
        # Should be sorted by name_sim descending
        for i in range(len(result) - 1):
            assert result[i]["name_sim"] >= result[i + 1]["name_sim"]

    @with_test_config
    @pytest.mark.asyncio
    async def test_get_details(self, test_provider: MockConfigProvider):
        """Test get_details functionality"""
        mock_proxy = AsyncMock()
        mock_details = {"geonameId": 2666199, "name": "Umeå", "lat": "63.82842", "lng": "20.25972"}
        mock_proxy.get_details.return_value = mock_details

        strategy = GeoNamesReconciliationStrategy()

        with patch.object(strategy, "get_proxy", return_value=mock_proxy):
            result = await strategy.get_details("2666199", lang="sv", style="FULL")

        mock_proxy.get_details.assert_called_once_with(entity_id="2666199", lang="sv", style="FULL")
        assert result == mock_details

    @with_test_config
    @pytest.mark.asyncio
    async def test_get_details_filtered_kwargs(self, test_provider: MockConfigProvider):
        """Test get_details with filtered kwargs"""
        mock_proxy = AsyncMock()
        mock_proxy.get_details.return_value = {}

        strategy = GeoNamesReconciliationStrategy()

        # Pass various kwargs, only lang and style should be passed through
        with patch.object(strategy, "get_proxy", return_value=mock_proxy):
            await strategy.get_details("123", lang="fr", style="MEDIUM", invalid_param="should_be_filtered", another_param=123)

        mock_proxy.get_details.assert_called_once_with(entity_id="123", lang="fr", style="MEDIUM")

    @with_test_config
    def test_geonames_type_for_refine_city(self, test_provider: MockConfigProvider):
        """Test type classification for cities"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"fcl": "P", "fcode": "PPLA"}

        result = strategy._geonames_type_for_refine(data)

        assert result == {"id": "/location/citytown", "name": "City/Town"}

    @with_test_config
    def test_geonames_type_for_refine_admin_area(self, test_provider: MockConfigProvider):
        """Test type classification for administrative areas"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"fcl": "A", "fcode": "ADM1"}

        result = strategy._geonames_type_for_refine(data)

        assert result == {"id": "/location/administrative_area", "name": "Administrative Area"}

    @with_test_config
    def test_geonames_type_for_refine_admin_area_adm2(self, test_provider: MockConfigProvider):
        """Test type classification for second-order administrative areas"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"fcl": "A", "fcode": "ADM2"}

        result = strategy._geonames_type_for_refine(data)

        assert result == {"id": "/location/administrative_area", "name": "Administrative Area"}

    @with_test_config
    def test_geonames_type_for_refine_other_admin(self, test_provider: MockConfigProvider):
        """Test type classification for non-ADM administrative areas"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"fcl": "A", "fcode": "PCL"}  # Political entity

        result = strategy._geonames_type_for_refine(data)

        assert result == {"id": "/location/place", "name": "Place"}

    @with_test_config
    def test_geonames_type_for_refine_generic(self, test_provider: MockConfigProvider):
        """Test type classification for generic places"""
        strategy = GeoNamesReconciliationStrategy()

        data = {"fcl": "H", "fcode": "LK"}  # Lake

        result = strategy._geonames_type_for_refine(data)

        assert result == {"id": "/location/place", "name": "Place"}

    @with_test_config
    def test_geonames_type_for_refine_missing_data(self, test_provider: MockConfigProvider):
        """Test type classification with missing data"""
        strategy = GeoNamesReconciliationStrategy()

        data = {}

        result = strategy._geonames_type_for_refine(data)

        assert result == {"id": "/location/place", "name": "Place"}


class TestGeoNamesSpecification:
    """Test SPECIFICATION constant"""

    def test_specification_structure(self):
        """Test that SPECIFICATION has required fields"""
        assert SPECIFICATION["key"] == "geonames"
        assert SPECIFICATION["display_name"] == "GeoNames Places"
        assert SPECIFICATION["id_field"] == "geoname_id"
        assert SPECIFICATION["label_field"] == "label"
        assert isinstance(SPECIFICATION["properties"], list)
        assert isinstance(SPECIFICATION["property_settings"], dict)
        assert isinstance(SPECIFICATION["sql_queries"], dict)


class TestGeoNamesIntegration:
    """Integration tests for GeoNames components"""

    @with_test_config
    @pytest.mark.asyncio
    @patch("src.strategies.geonames.GeoNamesProxy")
    async def test_complete_workflow(self, mock_geonames_proxy_class, test_provider: MockConfigProvider):
        """Test complete search and details workflow"""
        # Mock the GeoNames proxy
        mock_proxy = AsyncMock()

        # Mock search results
        search_results = [
            {
                "geonameId": 2666199,
                "name": "Umeå",
                "lat": "63.82842",
                "lng": "20.25972",
                "countryName": "Sweden",
                "adminName1": "Västerbotten",
                "score": 95.0,
                "population": 83249,
                "fcl": "P",
                "fcode": "PPLA2",
                "fcodeName": "seat of a second-order administrative division",
            }
        ]

        # Mock details result
        details_result = {"geonameId": 2666199, "name": "Umeå", "timezone": {"timeZoneId": "Europe/Stockholm"}}

        mock_proxy.search.return_value = search_results
        mock_proxy.get_details.return_value = details_result
        mock_geonames_proxy_class.return_value = mock_proxy

        # Test the workflow
        strategy = GeoNamesReconciliationStrategy()

        # Search for candidates
        candidates = await strategy.find_candidates("Umea", limit=5)

        # Convert to OpenRefine format
        refine_candidates = [strategy.as_candidate(c, "Umea") for c in candidates]

        # Get details for first candidate
        if refine_candidates:
            details = await strategy.get_details(refine_candidates[0]["id"])

            assert details == details_result

        # Verify the workflow
        assert len(candidates) == 1
        assert len(refine_candidates) == 1

        candidate = refine_candidates[0]
        assert candidate["id"] == "2666199"
        assert candidate["name"] == "Umeå, Västerbotten, Sweden"
        assert candidate["type"] == [{"id": "/location/citytown", "name": "City/Town"}]
        assert "pop 83,249" in candidate["description"]


class TestGeoNamesEdgeCases:
    """Test edge cases and error conditions"""

    @with_test_config
    @pytest.mark.asyncio
    async def test_find_candidates_empty_results(self, test_provider: MockConfigProvider):
        """Test find_candidates with no results"""
        mock_proxy = AsyncMock()
        mock_proxy.find.return_value = []

        strategy = GeoNamesReconciliationStrategy()

        with patch.object(strategy, "get_proxy", return_value=mock_proxy):
            result = await strategy.find_candidates("nonexistent place")

        assert result == []

    @with_test_config
    @pytest.mark.asyncio
    async def test_get_details_not_found(self, test_provider: MockConfigProvider):
        """Test get_details when entity is not found"""
        mock_proxy = AsyncMock()
        mock_proxy.get_details.return_value = None
        strategy = GeoNamesReconciliationStrategy()

        with patch.object(strategy, "get_proxy", return_value=mock_proxy):
            result = await strategy.get_details("999999999")

        assert result is None

    @with_test_config
    def test_as_candidate_string_conversion(self, test_provider: MockConfigProvider):
        """Test as_candidate handles various data types properly"""
        strategy = GeoNamesReconciliationStrategy()

        # Test with numeric geonameId
        data = {
            "geonameId": 123,  # Integer instead of string
            "name": "Test",
            "score": "85.5",  # String instead of float
            "population": "50000",  # String instead of int
        }

        result = strategy.as_candidate(data, "test")

        assert result["id"] == "123"  # Should be converted to string
        assert isinstance(result["score"], float)

    @with_test_config
    def test_calculate_score_edge_values(self, test_provider: MockConfigProvider):
        """Test score calculation with edge values"""
        strategy = GeoNamesReconciliationStrategy()

        # Test with very high score and population
        data = {"score": 100.0, "population": 1000000000}  # 1 billion

        score = strategy._calculate_score(data)

        # Score should be capped at 100
        assert score == 100.0

        # Test with negative population (shouldn't happen but handle gracefully)
        data = {"score": 50.0, "population": -1000}

        score = strategy._calculate_score(data)

        # Should handle gracefully (log of negative number would cause error)
        assert isinstance(score, float)
        assert score >= 60.0  # At least base score


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
