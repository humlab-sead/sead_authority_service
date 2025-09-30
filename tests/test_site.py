from configuration.inject import ConfigStore
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any, Dict, List

import psycopg

from src.strategies.site import QueryProxy, SiteReconciliationStrategy


class TestQueryProxy:
    """Tests for QueryProxy class."""

    def setup_method(self):
        """Set up test fixtures."""
        ConfigStore.configure_context(source="./tests/config.yml")
        self.mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
        self.proxy = QueryProxy(self.mock_cursor)

    @pytest.mark.asyncio
    async def test_fetch_site_by_national_id_found(self):
        """Test fetching site by national ID when site exists."""
        # Mock data returned from database
        mock_row = {
            "site_id": 1,
            "label": "Test Site",
            "name_sim": 1.0,
            "latitude": 59.3293,
            "longitude": 18.0686
        }
        self.mock_cursor.fetchone.return_value = mock_row

        result = await self.proxy.fetch_site_by_national_id("TEST123")

        # Verify SQL execution
        expected_sql = """
            select site_id, label, 1.0 as name_sim, latitude_dd as latitude, longitude_dd as longitude
            from authority.sites
            where national_site_identifier = %(identifier)s
            limit 1
        """
        self.mock_cursor.execute.assert_called_once_with(expected_sql, {"identifier": "TEST123"})
        self.mock_cursor.fetchone.assert_called_once()
        
        assert result == [mock_row]

    @pytest.mark.asyncio
    async def test_fetch_site_by_national_id_not_found(self):
        """Test fetching site by national ID when site doesn't exist."""
        self.mock_cursor.fetchone.return_value = None

        result = await self.proxy.fetch_site_by_national_id("NONEXISTENT")

        self.mock_cursor.execute.assert_called_once()
        self.mock_cursor.fetchone.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_by_fuzzy_name_search(self):
        """Test fuzzy name search."""
        mock_rows = [
            {"site_id": 1, "label": "Test Site 1", "name_sim": 0.9},
            {"site_id": 2, "label": "Test Site 2", "name_sim": 0.8}
        ]
        self.mock_cursor.fetchall.return_value = mock_rows

        result = await self.proxy.fetch_by_fuzzy_name_search("test site", limit=5)

        expected_sql = "SELECT * FROM authority.fuzzy_sites(%(q)s, %(n)s);"
        self.mock_cursor.execute.assert_called_once_with(expected_sql, {"q": "test site", "n": 5})
        self.mock_cursor.fetchall.assert_called_once()
        assert result == mock_rows

    @pytest.mark.asyncio
    async def test_fetch_by_fuzzy_name_search_default_limit(self):
        """Test fuzzy name search with default limit."""
        self.mock_cursor.fetchall.return_value = []

        await self.proxy.fetch_by_fuzzy_name_search("test")

        self.mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM authority.fuzzy_sites(%(q)s, %(n)s);",
            {"q": "test", "n": 10}
        )

    @pytest.mark.asyncio
    async def test_fetch_site_distances(self):
        """Test fetching site distances."""
        coordinate = {"lat": 59.3293, "lon": 18.0686}
        site_ids = [1, 2, 3]
        
        mock_rows = [
            {"site_id": 1, "distance_km": 1.2},
            {"site_id": 2, "distance_km": 5.7},
            {"site_id": 3, "distance_km": 12.3}
        ]
        self.mock_cursor.fetchall.return_value = mock_rows

        result = await self.proxy.fetch_site_distances(coordinate, site_ids)

        # Verify SQL execution with proper parameters
        expected_params = {
            "lat": 59.3293,
            "lon": 18.0686,
            "site_ids": [1, 2, 3]
        }
        self.mock_cursor.execute.assert_called_once()
        args, kwargs = self.mock_cursor.execute.call_args
        assert args[1] == expected_params
        
        self.mock_cursor.fetchall.assert_called_once()
        expected_result = {1: 1.2, 2: 5.7, 3: 12.3}
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_get_site_details_valid_id(self):
        """Test getting site details with valid ID."""
        mock_row = {
            "ID": 123,
            "Name": "Test Site",
            "Description": "A test site",
            "National ID": "TEST123",
            "Latitude": 59.3293,
            "Longitude": 18.0686
        }
        self.mock_cursor.fetchone.return_value = mock_row

        result = await self.proxy.get_site_details("123")

        expected_sql = """
                SELECT 
                    site_id as "ID", 
                    label as "Name", 
                    site_description as "Description", 
                    national_site_identifier as "National ID", 
                    latitude_dd as "Latitude", 
                    longitude_dd as "Longitude"
                FROM authority.sites 
                WHERE site_id = %(id)s
                """
        self.mock_cursor.execute.assert_called_once_with(expected_sql, {"id": 123})
        assert result == mock_row

    @pytest.mark.asyncio
    async def test_get_site_details_invalid_id(self):
        """Test getting site details with invalid ID."""
        result = await self.proxy.get_site_details("not_a_number")
        assert result is None
        self.mock_cursor.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_site_details_not_found(self):
        """Test getting site details when site doesn't exist."""
        self.mock_cursor.fetchone.return_value = None

        result = await self.proxy.get_site_details("999")

        assert result is None
        self.mock_cursor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_site_details_database_error(self):
        """Test getting site details when database error occurs."""
        self.mock_cursor.execute.side_effect = psycopg.Error("Database error")

        result = await self.proxy.get_site_details("123")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_site_location_similarity(self):
        """Test fetching site location similarity."""
        candidates = [
            {"site_id": 1, "label": "Site 1"},
            {"site_id": 2, "label": "Site 2"}
        ]
        
        mock_rows = [
            {"site_id": 1, "place_sim": 0.8},
            {"site_id": 2, "place_sim": 0.6}
        ]
        self.mock_cursor.fetchall.return_value = mock_rows

        result = await self.proxy.fetch_site_location_similarity(candidates, "Stockholm")

        expected_sql = """
            select site_id, max(similarity(location_name, %(place)s)) as place_sim
            from public.tbl_site_locations
            join public.tbl_locations using(location_id)
            where site_id = any(%(site_ids)s) 
              and location_name is not null
            group by site_id
        """
        self.mock_cursor.execute.assert_called_once_with(
            expected_sql,
            {"place": "Stockholm", "site_ids": [1, 2]}
        )
        
        expected_result = {1: 0.8, 2: 0.6}
        assert result == expected_result


class TestSiteReconciliationStrategy:
    """Tests for SiteReconciliationStrategy class."""

    def setup_method(self, cfg):
        """Set up test fixtures."""
        ConfigStore.configure_context(source="./tests/config.yml")
        self.strategy = SiteReconciliationStrategy()
        self.mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)

    def test_get_entity_id_field(self):
        """Test getting entity ID field name."""
        assert self.strategy.get_entity_id_field() == "site_id"

    def test_get_label_field(self):
        """Test getting label field name."""
        assert self.strategy.get_label_field() == "label"

    def test_get_id_path(self):
        """Test getting ID path."""
        assert self.strategy.get_id_path() == "site"

    @pytest.mark.asyncio
    @patch('src.strategies.site.QueryProxy')
    async def test_find_candidates_by_national_id(self, mock_query_proxy_class):
        """Test finding candidates by national ID."""
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy
        
        # Mock national ID search returns results
        mock_sites = [
            {"site_id": 1, "label": "Test Site", "name_sim": 1.0}
        ]
        mock_proxy.fetch_site_by_national_id.return_value = mock_sites
        
        properties = {"national_id": "TEST123"}
        result = await self.strategy.find_candidates(
            self.mock_cursor, "test query", properties, limit=10
        )

        mock_proxy.fetch_site_by_national_id.assert_called_once_with("TEST123")
        mock_proxy.fetch_by_fuzzy_name_search.assert_not_called()
        assert result == mock_sites

    @pytest.mark.asyncio
    @patch('src.strategies.site.QueryProxy')
    async def test_find_candidates_by_fuzzy_search(self, mock_query_proxy_class):
        """Test finding candidates by fuzzy search when no national ID."""
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy
        
        mock_proxy.fetch_site_by_national_id.return_value = []
        mock_sites = [
            {"site_id": 1, "label": "Test Site", "name_sim": 0.9},
            {"site_id": 2, "label": "Another Site", "name_sim": 0.7}
        ]
        mock_proxy.fetch_by_fuzzy_name_search.return_value = mock_sites

        result = await self.strategy.find_candidates(
            self.mock_cursor, "test site", {}, limit=5
        )

        mock_proxy.fetch_by_fuzzy_name_search.assert_called_once_with("test site", 5)
        # Results should be sorted by name_sim in descending order
        assert result[0]["name_sim"] >= result[1]["name_sim"]

    @pytest.mark.asyncio
    @patch('src.strategies.site.QueryProxy')
    async def test_find_candidates_with_geographic_scoring(self, mock_query_proxy_class):
        """Test finding candidates with geographic scoring."""
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy
        
        mock_proxy.fetch_site_by_national_id.return_value = []
        mock_sites = [
            {"site_id": 1, "label": "Near Site", "name_sim": 0.8},
            {"site_id": 2, "label": "Far Site", "name_sim": 0.9}
        ]
        mock_proxy.fetch_by_fuzzy_name_search.return_value = mock_sites

        # Mock the geographic scoring method
        with patch.object(self.strategy, '_apply_geographic_scoring', new_callable=AsyncMock) as mock_geo_scoring:
            mock_geo_scoring.return_value = mock_sites
            
            properties = {"latitude": 59.3293, "longitude": 18.0686}
            result = await self.strategy.find_candidates(
                self.mock_cursor, "test site", properties, limit=10
            )

            mock_geo_scoring.assert_called_once_with(
                mock_sites, 
                {"lat": 59.3293, "lon": 18.0686}, 
                mock_proxy
            )

    @pytest.mark.asyncio
    @patch('src.strategies.site.QueryProxy')
    async def test_find_candidates_with_place_context_scoring(self, mock_query_proxy_class):
        """Test finding candidates with place context scoring."""
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy
        
        mock_proxy.fetch_site_by_national_id.return_value = []
        mock_sites = [{"site_id": 1, "label": "Test Site", "name_sim": 0.8}]
        mock_proxy.fetch_by_fuzzy_name_search.return_value = mock_sites

        with patch.object(self.strategy, '_apply_place_context_scoring', new_callable=AsyncMock) as mock_place_scoring:
            mock_place_scoring.return_value = mock_sites
            
            properties = {"place": "Stockholm"}
            result = await self.strategy.find_candidates(
                self.mock_cursor, "test site", properties, limit=10
            )

            mock_place_scoring.assert_called_once_with(mock_sites, "Stockholm", mock_proxy)

    @pytest.mark.asyncio
    @patch('src.configuration.inject.ConfigValue')
    async def test_apply_geographic_scoring(self, mock_config_value):
        """Test geographic scoring application."""
        # Mock configuration values
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.2, 10.0]  # very_near_distance_km, to_far_distance_km
        mock_config_value.return_value = mock_config_instance

        candidates = [
            {"site_id": 1, "label": "Near Site", "name_sim": 0.7},
            {"site_id": 2, "label": "Far Site", "name_sim": 0.8}
        ]
        
        coordinate = {"lat": 59.3293, "lon": 18.0686}
        distances = {1: 0.5, 2: 15.0}  # 0.5km and 15km away
        
        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_distances.return_value = distances

        result = await self.strategy._apply_geographic_scoring(candidates, coordinate, mock_proxy)

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
    async def test_apply_geographic_scoring_no_coordinates(self):
        """Test geographic scoring with no coordinates."""
        candidates = [{"site_id": 1, "label": "Site", "name_sim": 0.8}]
        mock_proxy = AsyncMock()

        result = await self.strategy._apply_geographic_scoring(candidates, {}, mock_proxy)

        assert result == candidates
        mock_proxy.fetch_site_distances.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_geographic_scoring_no_candidates(self):
        """Test geographic scoring with no candidates."""
        coordinate = {"lat": 59.3293, "lon": 18.0686}
        mock_proxy = AsyncMock()

        result = await self.strategy._apply_geographic_scoring([], coordinate, mock_proxy)

        assert result == []
        mock_proxy.fetch_site_distances.assert_not_called()

    @pytest.mark.asyncio
    @patch('src.configuration.inject.ConfigValue')
    async def test_apply_place_context_scoring(self, mock_config_value):
        """Test place context scoring application."""
        # Mock configuration values
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.3, 0.1]  # similarity_threshold, max_boost
        mock_config_value.return_value = mock_config_instance

        candidates = [
            {"site_id": 1, "label": "Stockholm Site", "name_sim": 0.7},
            {"site_id": 2, "label": "Other Site", "name_sim": 0.8}
        ]
        
        place_results = {1: 0.9, 2: 0.2}  # High similarity for site 1, low for site 2
        
        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_location_similarity.return_value = place_results

        result = await self.strategy._apply_place_context_scoring(candidates, "Stockholm", mock_proxy)

        mock_proxy.fetch_site_location_similarity.assert_called_once_with(candidates, "Stockholm")
        
        # Site 1 should get place boost (similarity 0.9 > threshold 0.3)
        # Site 2 should not get boost (similarity 0.2 < threshold 0.3)
        assert result[0]["name_sim"] > 0.7  # Got place boost
        assert result[1]["name_sim"] == 0.8  # No boost

    @pytest.mark.asyncio
    @patch('src.strategies.site.QueryProxy')
    async def test_get_details(self, mock_query_proxy_class):
        """Test getting site details."""
        mock_proxy = AsyncMock()
        mock_query_proxy_class.return_value = mock_proxy
        
        expected_details = {
            "ID": 123,
            "Name": "Test Site",
            "Description": "A test site"
        }
        mock_proxy.get_site_details.return_value = expected_details

        result = await self.strategy.get_details("123", self.mock_cursor)

        mock_query_proxy_class.assert_called_once_with(self.mock_cursor)
        mock_proxy.get_site_details.assert_called_once_with("123")
        assert result == expected_details

    @pytest.mark.asyncio
    async def test_find_candidates_empty_properties(self):
        """Test finding candidates with empty properties."""
        with patch('src.strategies.site.QueryProxy') as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy
            
            mock_proxy.fetch_site_by_national_id.return_value = []
            mock_sites = [{"site_id": 1, "label": "Test Site", "name_sim": 0.8}]
            mock_proxy.fetch_by_fuzzy_name_search.return_value = mock_sites

            result = await self.strategy.find_candidates(
                self.mock_cursor, "test query", None, limit=10
            )

            # Should not call national_id search
            mock_proxy.fetch_site_by_national_id.assert_not_called()
            mock_proxy.fetch_by_fuzzy_name_search.assert_called_once_with("test query", 10)
            assert result == mock_sites

    @pytest.mark.asyncio
    async def test_find_candidates_sorting(self):
        """Test that candidates are sorted by name_sim in descending order."""
        with patch('src.strategies.site.QueryProxy') as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy
            
            mock_proxy.fetch_site_by_national_id.return_value = []
            # Unsorted candidates
            mock_sites = [
                {"site_id": 1, "label": "Low Score", "name_sim": 0.3},
                {"site_id": 2, "label": "High Score", "name_sim": 0.9},
                {"site_id": 3, "label": "Medium Score", "name_sim": 0.6}
            ]
            mock_proxy.fetch_by_fuzzy_name_search.return_value = mock_sites

            result = await self.strategy.find_candidates(
                self.mock_cursor, "test query", {}, limit=10
            )

            # Should be sorted by name_sim descending
            assert result[0]["name_sim"] == 0.9
            assert result[1]["name_sim"] == 0.6
            assert result[2]["name_sim"] == 0.3

    @pytest.mark.asyncio
    async def test_find_candidates_limit_applied(self):
        """Test that limit is properly applied to results."""
        with patch('src.strategies.site.QueryProxy') as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy
            
            mock_proxy.fetch_site_by_national_id.return_value = []
            # More candidates than limit
            mock_sites = [
                {"site_id": i, "label": f"Site {i}", "name_sim": 1.0 - i * 0.1}
                for i in range(15)  # 15 candidates
            ]
            mock_proxy.fetch_by_fuzzy_name_search.return_value = mock_sites

            result = await self.strategy.find_candidates(
                self.mock_cursor, "test query", {}, limit=5  # Limit to 5
            )

            assert len(result) == 5
            # Should be the top 5 by score
            for i in range(5):
                assert result[i]["site_id"] == i


# Integration tests
class TestSiteStrategyIntegration:
    """Integration tests for the complete site reconciliation workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        ConfigStore.configure_context(source="./tests/config.yml")
        self.strategy = SiteReconciliationStrategy()
        self.mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)

    @pytest.mark.asyncio
    @patch('src.configuration.inject.ConfigValue')
    async def test_complete_reconciliation_workflow(self, mock_config_value):
        """Test the complete reconciliation workflow."""
        # Mock configuration values
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.2, 10.0, 0.3, 0.1]
        mock_config_value.return_value = mock_config_instance

        with patch('src.strategies.site.QueryProxy') as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy
            
            # No national ID match
            mock_proxy.fetch_site_by_national_id.return_value = []
            
            # Fuzzy search results
            candidates = [
                {"site_id": 1, "label": "Stockholm Archaeological Site", "name_sim": 0.8},
                {"site_id": 2, "label": "Uppsala Site", "name_sim": 0.7}
            ]
            mock_proxy.fetch_by_fuzzy_name_search.return_value = candidates
            
            # Geographic distances
            distances = {1: 0.1, 2: 5.0}  # Very close and moderately close
            mock_proxy.fetch_site_distances.return_value = distances
            
            # Place similarity
            place_results = {1: 0.9, 2: 0.2}  # High similarity for Stockholm site
            mock_proxy.fetch_site_location_similarity.return_value = place_results

            properties = {
                "latitude": 59.3293,
                "longitude": 18.0686,
                "place": "Stockholm"
            }

            result = await self.strategy.find_candidates(
                self.mock_cursor, "archaeological site", properties, limit=10
            )

            # Verify all methods were called
            mock_proxy.fetch_by_fuzzy_name_search.assert_called_once()
            mock_proxy.fetch_site_distances.assert_called_once()
            mock_proxy.fetch_site_location_similarity.assert_called_once()
            
            # Results should be enhanced with distance and boosted scores
            assert len(result) == 2
            assert all("distance_km" in candidate for candidate in result)
            
            # Stockholm site should have higher score due to proximity and place match
            stockholm_site = next(c for c in result if c["site_id"] == 1)
            uppsala_site = next(c for c in result if c["site_id"] == 2)
            
            assert stockholm_site["name_sim"] > 0.8  # Original score + boosts
            assert uppsala_site["name_sim"] >= 0.7   # May have some geographic boost

    @pytest.mark.asyncio
    async def test_error_handling_in_geographic_scoring(self):
        """Test error handling when geographic scoring fails."""
        candidates = [{"site_id": 1, "label": "Test Site", "name_sim": 0.8}]
        coordinate = {"lat": 59.3293, "lon": 18.0686}
        
        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_distances.side_effect = Exception("Database error")

        with pytest.raises(Exception) as _:
            _ = await self.strategy._apply_geographic_scoring(candidates, coordinate, mock_proxy)


class TestSiteStrategyEdgeCases:
    """Edge case tests for SiteReconciliationStrategy."""

    def setup_method(self):
        """Set up test fixtures."""
        ConfigStore.configure_context(source="./tests/config.yml")
        self.strategy = SiteReconciliationStrategy()
        self.mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)

    @pytest.mark.asyncio
    @patch('src.configuration.inject.ConfigValue')
    async def test_geographic_scoring_with_missing_site_distances(self, mock_config_value):
        """Test geographic scoring when some sites don't have distance data."""
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.2, 10.0]
        mock_config_value.return_value = mock_config_instance

        candidates = [
            {"site_id": 1, "label": "Site 1", "name_sim": 0.8},
            {"site_id": 2, "label": "Site 2", "name_sim": 0.7},
            {"site_id": 3, "label": "Site 3", "name_sim": 0.6}
        ]
        
        coordinate = {"lat": 59.3293, "lon": 18.0686}
        # Only distances for sites 1 and 3
        distances = {1: 0.5, 3: 15.0}
        
        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_distances.return_value = distances

        result = await self.strategy._apply_geographic_scoring(candidates, coordinate, mock_proxy)

        # Sites with distances should have distance_km field
        site_1 = next(c for c in result if c["site_id"] == 1)
        site_2 = next(c for c in result if c["site_id"] == 2)
        site_3 = next(c for c in result if c["site_id"] == 3)
        
        assert "distance_km" in site_1
        assert "distance_km" not in site_2  # No distance data
        assert "distance_km" in site_3

    @pytest.mark.asyncio
    @patch('src.configuration.inject.ConfigValue')
    async def test_place_scoring_with_no_matches(self, mock_config_value):
        """Test place context scoring when no sites match the place."""
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.3, 0.1]
        mock_config_value.return_value = mock_config_instance

        candidates = [
            {"site_id": 1, "label": "Site 1", "name_sim": 0.8},
            {"site_id": 2, "label": "Site 2", "name_sim": 0.7}
        ]
        
        # No place similarity results
        place_results = {}
        
        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_location_similarity.return_value = place_results

        result = await self.strategy._apply_place_context_scoring(candidates, "Unknown Place", mock_proxy)

        # Scores should remain unchanged
        assert result[0]["name_sim"] == 0.8
        assert result[1]["name_sim"] == 0.7

    @pytest.mark.asyncio
    @patch('src.configuration.inject.ConfigValue')
    async def test_place_scoring_below_threshold(self, mock_config_value):
        """Test place context scoring with similarities below threshold."""
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.5, 0.1]  # High threshold
        mock_config_value.return_value = mock_config_instance

        candidates = [
            {"site_id": 1, "label": "Site 1", "name_sim": 0.8}
        ]
        
        # Similarity below threshold
        place_results = {1: 0.3}
        
        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_location_similarity.return_value = place_results

        result = await self.strategy._apply_place_context_scoring(candidates, "Place", mock_proxy)

        # Score should remain unchanged (below threshold)
        assert result[0]["name_sim"] == 0.8

    @pytest.mark.asyncio
    @patch('src.configuration.inject.ConfigValue')
    async def test_geographic_scoring_max_score_cap(self, mock_config_value):
        """Test that geographic scoring doesn't exceed maximum score of 1.0."""
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.5, 10.0]  # High boost
        mock_config_value.return_value = mock_config_instance

        candidates = [
            {"site_id": 1, "label": "Site 1", "name_sim": 0.9}  # Already high score
        ]
        
        coordinate = {"lat": 59.3293, "lon": 18.0686}
        distances = {1: 0.1}  # Very close - should get max boost
        
        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_distances.return_value = distances

        result = await self.strategy._apply_geographic_scoring(candidates, coordinate, mock_proxy)

        # Score should be capped at 1.0
        assert result[0]["name_sim"] == 1.0

    @pytest.mark.asyncio
    @patch('src.configuration.inject.ConfigValue')
    async def test_place_scoring_max_score_cap(self, mock_config_value):
        """Test that place context scoring doesn't exceed maximum score of 1.0."""
        mock_config_instance = MagicMock()
        mock_config_instance.resolve.side_effect = [0.3, 0.5]  # High boost
        mock_config_value.return_value = mock_config_instance

        candidates = [
            {"site_id": 1, "label": "Site 1", "name_sim": 0.8}
        ]
        
        place_results = {1: 1.0}  # Perfect place match
        
        mock_proxy = AsyncMock()
        mock_proxy.fetch_site_location_similarity.return_value = place_results

        result = await self.strategy._apply_place_context_scoring(candidates, "Place", mock_proxy)

        # Score should be capped at 1.0
        assert result[0]["name_sim"] <= 1.0

    @pytest.mark.asyncio
    async def test_find_candidates_all_enhancements_applied(self):
        """Test that all enhancements are applied in the correct order."""
        with patch('src.strategies.site.QueryProxy') as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy
            
            # No national_id provided, so fuzzy search will be used
            mock_proxy.fetch_site_by_national_id.return_value = []
            mock_sites = [{"site_id": 1, "label": "Test Site", "name_sim": 0.5}]
            mock_proxy.fetch_by_fuzzy_name_search.return_value = mock_sites

            # Mock both enhancement methods
            with patch.object(self.strategy, '_apply_geographic_scoring', new_callable=AsyncMock) as mock_geo, \
                 patch.object(self.strategy, '_apply_place_context_scoring', new_callable=AsyncMock) as mock_place:
                
                enhanced_sites_geo = [{"site_id": 1, "label": "Test Site", "name_sim": 0.7, "distance_km": 1.5}]
                enhanced_sites_place = [{"site_id": 1, "label": "Test Site", "name_sim": 0.8, "distance_km": 1.5}]
                
                mock_geo.return_value = enhanced_sites_geo
                mock_place.return_value = enhanced_sites_place

                properties = {
                    "latitude": 59.0,
                    "longitude": 18.0,
                    "place": "Stockholm"
                }

                result = await self.strategy.find_candidates(
                    self.mock_cursor, "test site", properties, limit=10
                )

                # Verify methods were called in correct order
                mock_geo.assert_called_once()
                mock_place.assert_called_once()
                
                # Final result should have both enhancements
                assert result == enhanced_sites_place

    @pytest.mark.asyncio 
    async def test_empty_query_string(self):
        """Test behavior with empty query string."""
        with patch('src.strategies.site.QueryProxy') as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy
            
            mock_proxy.fetch_site_by_national_id.return_value = []
            mock_proxy.fetch_by_fuzzy_name_search.return_value = []

            result = await self.strategy.find_candidates(
                self.mock_cursor, "", {}, limit=10
            )

            mock_proxy.fetch_by_fuzzy_name_search.assert_called_once_with("", 10)
            assert result == []

    @pytest.mark.asyncio
    async def test_zero_limit(self):
        """Test behavior with zero limit."""
        with patch('src.strategies.site.QueryProxy') as mock_query_proxy_class:
            mock_proxy = AsyncMock()
            mock_query_proxy_class.return_value = mock_proxy
            
            mock_proxy.fetch_site_by_national_id.return_value = []
            mock_sites = [{"site_id": 1, "label": "Site", "name_sim": 0.8}]
            mock_proxy.fetch_by_fuzzy_name_search.return_value = mock_sites

            result = await self.strategy.find_candidates(
                self.mock_cursor, "test", {}, limit=0
            )

            # Should return empty list due to limit=0
            assert result == []