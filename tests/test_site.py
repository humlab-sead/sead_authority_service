"""
Unit tests for Site reconciliation strategy.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import pytest

from src.strategies.site import SPECIFICATION, SiteQueryProxy, SiteReconciliationStrategy
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config

# pylint: disable=attribute-defined-outside-init,protected-access, unused-argument

SQL_QUERIES: dict[str, str] = SPECIFICATION["sql_queries"]


class TestSiteQueryProxy:
    """Tests for SiteQueryProxy class."""

    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_site_by_national_id_found(self, test_provider: ExtendedMockConfigProvider):
        """Test fetching site by national ID when site exists."""
        # Mock data returned from database

        mock_row: dict[str, Any] = {"site_id": 1, "label": "Test Site", "name_sim": 1.0, "latitude": 59.3293, "longitude": 18.0686}
        test_provider.create_connection_mock(fetchone=mock_row, execute=None)
        cursor_mock = test_provider.connection_mock.cursor.return_value.__aenter__.return_value

        proxy = SiteQueryProxy(SPECIFICATION, connection=test_provider.connection_mock)

        result: list[dict[str, Any]] = await proxy.fetch_site_by_national_id("TEST123")

        # Verify SQL execution
        expected_sql: str = SQL_QUERIES["fetch_site_by_national_id"]
        cursor_mock.execute.assert_called_once_with(expected_sql, {"identifier": "TEST123"})
        cursor_mock.fetchone.assert_called_once()

        assert result == [mock_row]

    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_site_by_national_id_not_found(self, test_provider: ExtendedMockConfigProvider):
        """Test fetching site by national ID when site doesn't exist."""
        test_provider.create_connection_mock(fetchone=None, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION, connection=test_provider.connection_mock)

        result: list[dict[str, Any]] = await proxy.fetch_site_by_national_id("NONEXISTENT")

        test_provider.cursor_mock.execute.assert_called_once()
        test_provider.cursor_mock.fetchone.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_by_name_search(self, test_provider: ExtendedMockConfigProvider):
        """Test fuzzy name search."""
        mock_rows = [{"site_id": 1, "label": "Test Site 1", "name_sim": 0.9}, {"site_id": 2, "label": "Test Site 2", "name_sim": 0.8}]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION, connection=test_provider.connection_mock)

        result: list[dict[str, Any]] = await proxy.fetch_by_fuzzy_label("test site", limit=5)

        expected_sql: str = SQL_QUERIES["fuzzy_label_sql"]
        test_provider.cursor_mock.execute.assert_called_once_with(expected_sql, {"q": "test site", "n": 5})
        test_provider.cursor_mock.fetchall.assert_called_once()
        # Convert MockRow objects back to dicts for comparison
        result_dicts = [dict(row) for row in result]
        assert result_dicts == mock_rows

    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_by_name_search_default_limit(self, test_provider: ExtendedMockConfigProvider):
        """Test fuzzy name search with default limit."""
        mock_rows = []
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION, connection=test_provider.connection_mock)

        result: list[dict[str, Any]] = await proxy.fetch_by_fuzzy_label("test site")

        expected_sql: str = SQL_QUERIES["fuzzy_label_sql"]
        test_provider.cursor_mock.execute.assert_called_once_with(expected_sql, {"q": "test site", "n": 10})
        test_provider.cursor_mock.fetchall.assert_called_once()
        # Convert MockRow objects back to dicts for comparison
        result_dicts = [dict(row) for row in result]
        assert result_dicts == mock_rows

    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_site_distances(self, test_provider: ExtendedMockConfigProvider):
        """Test fetching site distances."""
        mock_rows = [{"site_id": 1, "distance_km": 1.2}, {"site_id": 2, "distance_km": 5.7}, {"site_id": 3, "distance_km": 12.3}]
        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION, connection=test_provider.connection_mock)
        coordinate: dict[str, float] = {"lat": 59.3293, "lon": 18.0686}
        site_ids: list[int] = [1, 2, 3]

        result: dict[int, float] = await proxy.fetch_site_distances(coordinate, site_ids)

        # Verify SQL execution with proper parameters
        expected_params = {"lat": 59.3293, "lon": 18.0686, "site_ids": [1, 2, 3]}
        test_provider.cursor_mock.execute.assert_called_once()
        args, _ = test_provider.cursor_mock.execute.call_args
        assert args[1] == expected_params

        test_provider.cursor_mock.fetchall.assert_called_once()
        expected_result: dict[int, float] = {1: 1.2, 2: 5.7, 3: 12.3}
        assert result == expected_result

    @pytest.mark.asyncio
    @with_test_config
    async def test_get_site_details_valid_id(self, test_provider: ExtendedMockConfigProvider):
        """Test getting site details with valid ID."""
        test_provider.create_connection_mock(fetchall=None, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION)
        mock_row = {"ID": 123, "Name": "Test Site", "Description": "A test site", "National ID": "TEST123", "Latitude": 59.3293, "Longitude": 18.0686}
        test_provider.cursor_mock.fetchone.return_value = mock_row

        result: dict[str, Any] | None = await proxy.get_details("123")

        expected_sql: str = SQL_QUERIES["details_sql"]
        test_provider.cursor_mock.execute.assert_called_once_with(expected_sql, {"id": 123})

        assert result == mock_row

    @pytest.mark.asyncio
    @with_test_config
    async def test_get_site_details_invalid_id(self, test_provider: ExtendedMockConfigProvider):
        """Test getting site details with invalid ID."""
        test_provider.create_connection_mock(fetchall=None, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION)
        result: dict[str, Any] | None = await proxy.get_details("not_a_number")
        assert result is None
        test_provider.cursor_mock.execute.assert_not_called()

    @pytest.mark.asyncio
    @with_test_config
    async def test_get_site_details_not_found(self, test_provider: ExtendedMockConfigProvider):
        """Test getting site details when site doesn't exist."""
        test_provider.create_connection_mock(fetchone=None, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION, connection=test_provider.connection_mock)

        result: dict[str, Any] | None = await proxy.get_details("999")

        assert result is None
        test_provider.cursor_mock.execute.assert_called_once()

    @pytest.mark.asyncio
    @with_test_config
    async def test_get_site_details_database_error(self, test_provider: ExtendedMockConfigProvider):
        """Test getting site details when database error occurs."""
        test_provider.create_connection_mock(fetchall=None, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION)
        test_provider.cursor_mock.execute.side_effect = psycopg.Error("Database error")

        result: dict[str, Any] | None = await proxy.get_details("123")

        assert result is None

    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_site_location_similarity(self, test_provider: ExtendedMockConfigProvider):
        """Test fetching site location similarity."""
        test_provider.create_connection_mock(fetchall=None, execute=None)

        proxy = SiteQueryProxy(SPECIFICATION)
        candidates: list[dict[str, Any]] = [{"site_id": 1, "label": "Site 1"}, {"site_id": 2, "label": "Site 2"}]

        mock_rows: list[dict[str, Any]] = [{"site_id": 1, "place_sim": 0.8}, {"site_id": 2, "place_sim": 0.6}]
        test_provider.cursor_mock.fetchall.return_value = mock_rows

        result = await proxy.fetch_site_location_similarity(candidates, "Stockholm")

        expected_sql: str = SQL_QUERIES["fetch_site_location_similarity"]
        test_provider.cursor_mock.execute.assert_called_once_with(expected_sql, {"place": "Stockholm", "site_ids": [1, 2]})

        expected_result: dict[int, float] = {1: 0.8, 2: 0.6}
        assert result == expected_result


class TestSiteReconciliationStrategy:
    """Tests for SiteReconciliationStrategy class."""

    @with_test_config
    def test_get_entity_id_field(self, test_provider: ExtendedMockConfigProvider):
        """Test getting entity ID field name."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        assert strategy.get_entity_id_field() == "site_id"

    @with_test_config
    def test_get_label_field(self, test_provider: ExtendedMockConfigProvider):
        """Test getting label field name."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        assert strategy.get_label_field() == "label"

    @with_test_config
    def test_get_id_path(self, test_provider: ExtendedMockConfigProvider):
        """Test getting ID path."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        assert strategy.get_id_path() == "site"

    @with_test_config
    def test_get_property_settings(self, test_provider: ExtendedMockConfigProvider):
        """Test get_property_settings method returns site-specific settings."""
        strategy = SiteReconciliationStrategy()
        settings = strategy.get_property_settings()

        assert isinstance(settings, dict)
        assert "latitude" in settings
        assert "longitude" in settings

        # Check latitude settings
        lat_settings = settings["latitude"]
        assert lat_settings["min"] == -90.0
        assert lat_settings["max"] == 90.0
        assert lat_settings["precision"] == 6

        # Check longitude settings
        lon_settings = settings["longitude"]
        assert lon_settings["min"] == -180.0
        assert lon_settings["max"] == 180.0
        assert lon_settings["precision"] == 6

    @with_test_config
    def test_get_properties_meta(self, test_provider: ExtendedMockConfigProvider):
        """Test get_properties_meta method returns site-specific properties."""
        strategy = SiteReconciliationStrategy()
        properties = strategy.get_properties_meta()

        assert isinstance(properties, list)
        assert len(properties) == 5  # latitude, longitude, country, national_id, place_name

        # Check that all properties have required fields
        for prop in properties:
            assert "id" in prop
            assert "name" in prop
            assert "type" in prop
            assert "description" in prop

        # Check specific properties exist
        property_ids = [prop["id"] for prop in properties]
        assert "latitude" in property_ids
        assert "longitude" in property_ids
        assert "country" in property_ids
        assert "national_id" in property_ids
        assert "place_name" in property_ids

    @patch("src.strategies.site.SiteQueryProxy")
    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_by_national_id(self, mock_query_proxy_class, test_provider: ExtendedMockConfigProvider):
        """Test finding candidates by national ID."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy

        # Mock national ID search returns results
        mock_sites: list[dict[str, Any]] = [{"site_id": 1, "label": "Test Site", "name_sim": 1.0}]
        mock_proxy.fetch_site_by_national_id.return_value = mock_sites

        properties: dict[str, str] = {"national_id": "TEST123"}
        result = await strategy.find_candidates("test query", properties, limit=10)

        mock_proxy.fetch_site_by_national_id.assert_called_once_with("TEST123")
        mock_proxy.fetch_by_fuzzy_label.assert_not_called()
        assert result == mock_sites

    @patch("src.strategies.site.SiteQueryProxy")
    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_by_fuzzy_search(self, mock_query_proxy_class, test_provider: ExtendedMockConfigProvider):
        """Test finding candidates by fuzzy search when no national ID."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy

        mock_proxy.fetch_site_by_national_id.return_value = []
        mock_sites: list[dict[str, Any]] = [{"site_id": 1, "label": "Test Site", "name_sim": 0.9}, {"site_id": 2, "label": "Another Site", "name_sim": 0.7}]
        mock_proxy.fetch_by_fuzzy_label.return_value = mock_sites

        result = await strategy.find_candidates("test site", {}, limit=5)

        mock_proxy.fetch_by_fuzzy_label.assert_called_once_with("test site", 5)
        # Results should be sorted by name_sim in descending order
        assert result[0]["name_sim"] >= result[1]["name_sim"]

    @patch("src.strategies.site.SiteQueryProxy")
    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_with_geographic_scoring(self, mock_query_proxy_class, test_provider: ExtendedMockConfigProvider):
        """Test finding candidates with geographic scoring."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy

        mock_proxy.fetch_site_by_national_id.return_value = []
        mock_sites: list[dict[str, Any]] = [{"site_id": 1, "label": "Near Site", "name_sim": 0.8}, {"site_id": 2, "label": "Far Site", "name_sim": 0.9}]
        mock_proxy.fetch_by_fuzzy_label.return_value = mock_sites

        # Mock the geographic scoring method
        with patch.object(strategy, "_apply_geographic_scoring", new_callable=AsyncMock) as mock_geo_scoring:
            mock_geo_scoring.return_value = mock_sites

            properties: dict[str, float] = {"latitude": 59.3293, "longitude": 18.0686}
            await strategy.find_candidates("test site", properties, limit=10)

            mock_geo_scoring.assert_called_once_with(mock_sites, {"lat": 59.3293, "lon": 18.0686}, mock_proxy)

    @patch("src.strategies.site.SiteQueryProxy")
    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_with_place_context_scoring(self, mock_query_proxy_class, test_provider: ExtendedMockConfigProvider):
        """Test finding candidates with place context scoring."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy

        mock_proxy.fetch_site_by_national_id.return_value = []
        mock_sites: list[dict[str, Any]] = [{"site_id": 1, "label": "Test Site", "name_sim": 0.8}]
        mock_proxy.fetch_by_fuzzy_label.return_value = mock_sites

        with patch.object(strategy, "_apply_place_context_scoring", new_callable=AsyncMock) as mock_place_scoring:
            mock_place_scoring.return_value = mock_sites

            properties: dict[str, str] = {"place_name": "Stockholm"}  # Fixed key name
            await strategy.find_candidates("test site", properties, limit=10)

            mock_place_scoring.assert_called_once_with(mock_sites, "Stockholm", mock_proxy)

    @patch("src.configuration.ConfigValue")
    @pytest.mark.asyncio
    @with_test_config
    async def test_apply_geographic_scoring(self, mock_config_value, test_provider: ExtendedMockConfigProvider):
        """Test geographic scoring application."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.2, 10.0]  # very_near_distance_km, too_far_distance_km
        mock_config_value.return_value = mock_config_instance

        candidates: list[dict[str, Any]] = [{"site_id": 1, "label": "Near Site", "name_sim": 0.7}, {"site_id": 2, "label": "Far Site", "name_sim": 0.8}]

        coordinate: dict[str, float] = {"lat": 59.3293, "lon": 18.0686}
        distances: dict[int, float] = {1: 0.5, 2: 15.0}  # 0.5km and 15km away

        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_distances.return_value = distances

        result = await strategy._apply_geographic_scoring(candidates, coordinate, mock_proxy)

        # Verify distances were fetched
        mock_proxy.fetch_site_distances.assert_called_once_with(coordinate, [1, 2])

        # Check that proximity boost was applied
        assert result[0]["distance_km"] == 0.5
        assert result[1]["distance_km"] == 15.0

        # Near site should get a boost (0.7 + proximity_boost)
        # Far site should get no boost (too far)
        assert result[0]["name_sim"] > 0.7  # Got proximity boost
        assert result[1]["name_sim"] == 0.8  # No boost, too far

    @pytest.mark.asyncio
    @with_test_config
    async def test_apply_geographic_scoring_no_coordinates(self, test_provider: ExtendedMockConfigProvider):
        """Test geographic scoring with no coordinates."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        candidates = [{"site_id": 1, "label": "Site", "name_sim": 0.8}]
        mock_proxy = AsyncMock()

        result = await strategy._apply_geographic_scoring(candidates, {}, mock_proxy)

        assert result == candidates
        mock_proxy.fetch_site_distances.assert_not_called()

    @pytest.mark.asyncio
    @with_test_config
    async def test_apply_geographic_scoring_no_candidates(self, test_provider: ExtendedMockConfigProvider):
        """Test geographic scoring with no candidates."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        coordinate: dict[str, float] = {"lat": 59.3293, "lon": 18.0686}
        mock_proxy = AsyncMock()

        result = await strategy._apply_geographic_scoring([], coordinate, mock_proxy)

        assert result == []
        mock_proxy.fetch_site_distances.assert_not_called()

    @patch("src.configuration.ConfigValue")
    @pytest.mark.asyncio
    @with_test_config
    async def test_apply_place_context_scoring(self, mock_config_value, test_provider: ExtendedMockConfigProvider):
        """Test place context scoring application."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.3, 0.1]  # similarity_threshold, max_boost
        mock_config_value.return_value = mock_config_instance

        candidates = [{"site_id": 1, "label": "Stockholm Site", "name_sim": 0.7}, {"site_id": 2, "label": "Other Site", "name_sim": 0.8}]

        place_results: dict[int, float] = {1: 0.9, 2: 0.2}  # High similarity for site 1, low for site 2

        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_location_similarity.return_value = place_results

        result = await strategy._apply_place_context_scoring(candidates, "Stockholm", mock_proxy)

        mock_proxy.fetch_site_location_similarity.assert_called_once_with(candidates, "Stockholm")

        # Site 1 should get place boost (similarity 0.9 > threshold 0.3)
        # Site 2 should not get boost (similarity 0.2 < threshold 0.3)
        assert result[0]["name_sim"] > 0.7  # Got place boost
        assert result[1]["name_sim"] == 0.8  # No boost

    @patch("src.strategies.site.SiteQueryProxy")
    @pytest.mark.asyncio
    @with_test_config
    async def test_get_details(self, mock_query_proxy_class, test_provider: ExtendedMockConfigProvider):
        """Test getting site details."""
        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy

        expected_details = {"ID": 123, "Name": "Test Site", "Description": "A test site"}
        mock_proxy.get_details.return_value = expected_details

        result = await strategy.get_details("123")

        # The SiteQueryProxy is called with the SPECIFICATION
        mock_query_proxy_class.assert_called_once_with(SPECIFICATION)
        mock_proxy.get_details.assert_called_once_with("123")
        assert result == expected_details

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_empty_properties(self, test_provider: ExtendedMockConfigProvider):
        """Test finding candidates with empty properties."""
        with patch("src.strategies.site.SiteQueryProxy") as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy

            mock_proxy.fetch_site_by_national_id.return_value = []
            mock_sites: list[dict[str, Any]] = [{"site_id": 1, "label": "Test Site", "name_sim": 0.8}]
            mock_proxy.fetch_by_fuzzy_label.return_value = mock_sites

            strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
            result = await strategy.find_candidates("test query", None, limit=10)

            # Should not call national_id search
            mock_proxy.fetch_site_by_national_id.assert_not_called()
            mock_proxy.fetch_by_fuzzy_label.assert_called_once_with("test query", 10)
            assert result == mock_sites

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_sorting(self, test_provider: ExtendedMockConfigProvider):
        """Test that candidates are sorted by name_sim in descending order."""
        with patch("src.strategies.site.SiteQueryProxy") as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy

            mock_proxy.fetch_site_by_national_id.return_value = []
            # Unsorted candidates
            mock_sites: list[dict[str, Any]] = [
                {"site_id": 1, "label": "Low Score", "name_sim": 0.3},
                {"site_id": 2, "label": "High Score", "name_sim": 0.9},
                {"site_id": 3, "label": "Medium Score", "name_sim": 0.6},
            ]
            mock_proxy.fetch_by_fuzzy_label.return_value = mock_sites

            strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
            result = await strategy.find_candidates("test query", {}, limit=10)

            # Should be sorted by name_sim descending
            assert result[0]["name_sim"] == 0.9
            assert result[1]["name_sim"] == 0.6
            assert result[2]["name_sim"] == 0.3

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_limit_applied(self, test_provider: ExtendedMockConfigProvider):
        """Test that limit is properly applied to results."""
        with patch("src.strategies.site.SiteQueryProxy") as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy

            mock_proxy.fetch_site_by_national_id.return_value = []
            # More candidates than limit
            mock_sites: list[dict[str, Any]] = [{"site_id": i, "label": f"Site {i}", "name_sim": 1.0 - i * 0.1} for i in range(15)]  # 15 candidates
            mock_proxy.fetch_by_fuzzy_label.return_value = mock_sites

            strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
            result = await strategy.find_candidates("test query", {}, limit=5)  # Limit to 5

            assert len(result) == 5
            # Should be the top 5 by score
            for i in range(5):
                assert result[i]["site_id"] == i


# Integration tests
class TestSiteStrategyIntegration:
    """Integration tests for the complete site reconciliation workflow."""

    @patch("src.configuration.ConfigValue")
    @pytest.mark.asyncio
    @with_test_config
    async def test_complete_reconciliation_workflow(self, mock_config_value, test_provider: ExtendedMockConfigProvider):
        """Test the complete reconciliation workflow."""
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.2, 10.0, 0.3, 0.1]
        mock_config_value.return_value = mock_config_instance

        with patch("src.strategies.site.SiteQueryProxy") as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy

            # No national ID match
            mock_proxy.fetch_site_by_national_id.return_value = []

            # Fuzzy search results
            candidates = [{"site_id": 1, "label": "Stockholm Archaeological Site", "name_sim": 0.8}, {"site_id": 2, "label": "Uppsala Site", "name_sim": 0.7}]
            mock_proxy.fetch_by_fuzzy_label.return_value = candidates

            # Geographic distances
            distances = {1: 0.1, 2: 5.0}  # Very close and moderately close
            mock_proxy.fetch_site_distances.return_value = distances

            # Place similarity
            place_results = {1: 0.9, 2: 0.2}  # High similarity for Stockholm site
            mock_proxy.fetch_site_location_similarity.return_value = place_results

            properties = {"latitude": 59.3293, "longitude": 18.0686, "place_name": "Stockholm"}

            strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
            result = await strategy.find_candidates("archaeological site", properties, limit=10)

            # Verify all methods were called
            mock_proxy.fetch_by_fuzzy_label.assert_called_once()
            mock_proxy.fetch_site_distances.assert_called_once()
            mock_proxy.fetch_site_location_similarity.assert_called_once()

            # Results should be enhanced with distance and boosted scores
            assert len(result) == 2
            assert all("distance_km" in candidate for candidate in result)

            # Stockholm site should have higher score due to proximity and place match
            stockholm_site = next(c for c in result if c["site_id"] == 1)
            uppsala_site = next(c for c in result if c["site_id"] == 2)

            assert stockholm_site["name_sim"] > 0.8  # Original score + boosts
            assert uppsala_site["name_sim"] >= 0.7  # May have some geographic boost

    @pytest.mark.asyncio
    @with_test_config
    async def test_error_handling_in_geographic_scoring(self, test_provider: ExtendedMockConfigProvider):
        """Test error handling when geographic scoring fails."""

        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        candidates = [{"site_id": 1, "label": "Test Site", "name_sim": 0.8}]
        coordinate = {"lat": 59.3293, "lon": 18.0686}

        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_distances.side_effect = Exception("Database error")

        with pytest.raises(Exception) as _:
            _ = await strategy._apply_geographic_scoring(candidates, coordinate, mock_proxy)


class TestSiteStrategyEdgeCases:
    """Edge case tests for SiteReconciliationStrategy."""

    @pytest.mark.asyncio
    @patch("src.configuration.ConfigValue")
    @with_test_config
    async def test_geographic_scoring_with_missing_site_distances(self, mock_config_value, test_provider: ExtendedMockConfigProvider):
        """Test geographic scoring when some sites don't have distance data."""

        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.2, 10.0]
        mock_config_value.return_value = mock_config_instance

        candidates = [
            {"site_id": 1, "label": "Site 1", "name_sim": 0.8},
            {"site_id": 2, "label": "Site 2", "name_sim": 0.7},
            {"site_id": 3, "label": "Site 3", "name_sim": 0.6},
        ]

        coordinate = {"lat": 59.3293, "lon": 18.0686}
        # Only distances for sites 1 and 3
        distances = {1: 0.5, 3: 15.0}

        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_distances.return_value = distances

        result = await strategy._apply_geographic_scoring(candidates, coordinate, mock_proxy)

        # Sites with distances should have distance_km field
        site_1 = next(c for c in result if c["site_id"] == 1)
        site_2 = next(c for c in result if c["site_id"] == 2)
        site_3 = next(c for c in result if c["site_id"] == 3)

        assert "distance_km" in site_1
        assert "distance_km" not in site_2  # No distance data
        assert "distance_km" in site_3

    @pytest.mark.asyncio
    @patch("src.configuration.ConfigValue")
    @with_test_config
    async def test_place_scoring_with_no_matches(self, mock_config_value, test_provider: ExtendedMockConfigProvider):
        """Test place context scoring when no sites match the place."""

        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()

        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.3, 0.1]
        mock_config_value.return_value = mock_config_instance

        candidates = [{"site_id": 1, "label": "Site 1", "name_sim": 0.8}, {"site_id": 2, "label": "Site 2", "name_sim": 0.7}]

        # No place similarity results
        place_results = {}

        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_location_similarity.return_value = place_results

        result = await strategy._apply_place_context_scoring(candidates, "Unknown Place", mock_proxy)

        # Scores should remain unchanged
        assert result[0]["name_sim"] == 0.8
        assert result[1]["name_sim"] == 0.7

    @pytest.mark.asyncio
    @patch("src.configuration.ConfigValue")
    @with_test_config
    async def test_place_scoring_below_threshold(self, mock_config_value, test_provider: ExtendedMockConfigProvider):
        """Test place context scoring with similarities below threshold."""

        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.5, 0.1]  # High threshold
        mock_config_value.return_value = mock_config_instance

        candidates = [{"site_id": 1, "label": "Site 1", "name_sim": 0.8}]

        # Similarity below threshold
        place_results = {1: 0.3}

        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_location_similarity.return_value = place_results

        result = await strategy._apply_place_context_scoring(candidates, "Place", mock_proxy)

        # Score should remain unchanged (below threshold)
        assert result[0]["name_sim"] == 0.8

    @pytest.mark.asyncio
    @patch("src.configuration.ConfigValue")
    @with_test_config
    async def test_geographic_scoring_max_score_cap(self, mock_config_value, test_provider: ExtendedMockConfigProvider):
        """Test that geographic scoring doesn't exceed maximum score of 1.0."""

        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.5, 10.0]  # High boost
        mock_config_value.return_value = mock_config_instance

        candidates = [{"site_id": 1, "label": "Site 1", "name_sim": 0.9}]  # Already high score

        coordinate = {"lat": 59.3293, "lon": 18.0686}
        distances = {1: 0.1}  # Very close - should get max boost

        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_distances.return_value = distances

        result = await strategy._apply_geographic_scoring(candidates, coordinate, mock_proxy)

        # Score should be capped at 1.0
        assert result[0]["name_sim"] == 1.0

    @pytest.mark.asyncio
    @patch("src.configuration.ConfigValue")
    @with_test_config
    async def test_place_scoring_max_score_cap(self, mock_config_value, test_provider: ExtendedMockConfigProvider):
        """Test that place context scoring doesn't exceed maximum score of 1.0."""

        strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()

        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.3, 0.5]  # High boost
        mock_config_value.return_value = mock_config_instance

        candidates = [{"site_id": 1, "label": "Site 1", "name_sim": 0.8}]

        place_results = {1: 1.0}  # Perfect place match

        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_location_similarity.return_value = place_results

        result = await strategy._apply_place_context_scoring(candidates, "Place", mock_proxy)

        # Score should be capped at 1.0
        assert result[0]["name_sim"] <= 1.0

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_all_enhancements_applied(self, test_provider: ExtendedMockConfigProvider):
        """Test that all enhancements are applied in the correct order."""

        with patch("src.strategies.site.SiteQueryProxy") as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy

            # No national_id provided, so fuzzy search will be used
            mock_proxy.fetch_site_by_national_id.return_value = []
            mock_sites: list[dict[str, Any]] = [{"site_id": 1, "label": "Test Site", "name_sim": 0.5}]
            mock_proxy.fetch_by_fuzzy_label.return_value = mock_sites

            strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()

            # Mock both enhancement methods
            with (
                patch.object(strategy, "_apply_geographic_scoring", new_callable=AsyncMock) as mock_geo,
                patch.object(strategy, "_apply_place_context_scoring", new_callable=AsyncMock) as mock_place,
            ):

                enhanced_sites_geo = [{"site_id": 1, "label": "Test Site", "name_sim": 0.7, "distance_km": 1.5}]
                enhanced_sites_place = [{"site_id": 1, "label": "Test Site", "name_sim": 0.8, "distance_km": 1.5}]

                mock_geo.return_value = enhanced_sites_geo
                mock_place.return_value = enhanced_sites_place

                properties = {"latitude": 59.0, "longitude": 18.0, "place_name": "Stockholm"}

                result = await strategy.find_candidates("test site", properties, limit=10)

                # Verify methods were called in correct order
                mock_geo.assert_called_once()
                mock_place.assert_called_once()

                # Final result should have both enhancements
                assert result == enhanced_sites_place

    @pytest.mark.asyncio
    @with_test_config
    async def test_empty_query_string(self, test_provider: ExtendedMockConfigProvider):
        """Test behavior with empty query string."""

        with patch("src.strategies.site.SiteQueryProxy") as mock_query_proxy_class:

            strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()

            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy

            mock_proxy.fetch_site_by_national_id.return_value = []
            mock_proxy.fetch_by_fuzzy_label.return_value = []

            result = await strategy.find_candidates("", {}, limit=10)

            mock_proxy.fetch_by_fuzzy_label.assert_called_once_with("", 10)
            assert result == []

    @pytest.mark.asyncio
    @with_test_config
    async def test_zero_limit(self, test_provider: ExtendedMockConfigProvider):
        """Test behavior with zero limit."""

        with patch("src.strategies.site.SiteQueryProxy") as mock_query_proxy_class:

            strategy: SiteReconciliationStrategy = SiteReconciliationStrategy()

            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy

            mock_proxy.fetch_site_by_national_id.return_value = []
            mock_sites: list[dict[str, Any]] = [{"site_id": 1, "label": "Site", "name_sim": 0.8}]
            mock_proxy.fetch_by_fuzzy_label.return_value = mock_sites

            result = await strategy.find_candidates("test", {}, limit=0)

            # Should return empty list due to limit=0
            assert result == []
