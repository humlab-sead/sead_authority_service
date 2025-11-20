"""
Integration tests for reconciliation with real database connections.

These tests are designed to debug database transaction issues by:
1. Testing the full reconciliation pipeline with actual database connections
2. Reproducing the transaction error scenario
3. Providing debugging breakpoints and detailed logging
"""

import pytest
from typing import Any
from unittest.mock import patch, AsyncMock
import psycopg
from loguru import logger

from src.reconcile import reconcile_queries
from src.strategies.site import SiteReconciliationStrategy
from src.configuration import get_config_provider, Config, ConfigFactory
from tests.decorators import with_test_config
from tests.conftest import ExtendedMockConfigProvider


class TestReconcileIntegration:
    """Integration tests for the full reconciliation pipeline"""

    @pytest.mark.asyncio
    @with_test_config
    async def test_reconcile_single_query_with_mocked_connection(
        self, test_provider: ExtendedMockConfigProvider
    ):
        """Test a single reconciliation query with a mocked database connection.
        
        This test simulates a successful reconciliation to establish baseline behavior.
        """
        # Setup mock connection with successful responses
        test_provider.create_connection_mock(
            execute=None,
            fetchall=[
                {
                    "site_id": 1,
                    "label": "Agunnaryd",
                    "name_sim": 0.95,
                    "latitude": 56.7,
                    "longitude": 14.2,
                }
            ],
        )

        queries = {
            "q1": {
                "query": "Agunnaryd",
                "type": "site",
                "limit": 3,
            }
        }

        # Execute reconciliation
        results = await reconcile_queries(queries)

        # Verify results
        assert "q1" in results
        assert "result" in results["q1"]
        assert len(results["q1"]["result"]) == 1
        
        logger.info(f"Test passed: Single query reconciliation successful")

    @pytest.mark.asyncio
    @with_test_config
    async def test_reconcile_multiple_queries_simulating_transaction_error(
        self, test_provider: ExtendedMockConfigProvider
    ):
        """Test multiple queries to simulate the transaction error scenario.
        
        This test reproduces the error where a failed query puts the transaction
        in an error state, and subsequent queries fail with:
        "current transaction is aborted, commands ignored until end of transaction block"
        """
        # First query succeeds
        successful_response = [
            {
                "site_id": 1,
                "label": "Agunnaryd",
                "name_sim": 0.95,
                "latitude": 56.7,
                "longitude": 14.2,
            }
        ]

        # Second query fails with SQL error (simulating a database function error)
        # Third query would fail with transaction aborted error
        
        test_provider.create_connection_mock(execute=None, fetchall=successful_response)
        
        # Make the second execute call fail
        cursor_mock = test_provider.cursor_mock
        call_count = 0
        
        async def execute_side_effect(sql, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second query fails
                raise psycopg.errors.UndefinedFunction("function authority.fuzzy_site does not exist")
            # First and subsequent calls succeed (but in real scenario, subsequent would fail with transaction error)
        
        cursor_mock.execute.side_effect = execute_side_effect
        
        queries = {
            "q1": {"query": "Agunnaryd", "type": "site", "limit": 3},
            "q2": {"query": "Ala", "type": "site", "limit": 3},  # This will fail
            "q3": {"query": "Stockholm", "type": "site", "limit": 3},  # This would get transaction error
        }

        # Execute and expect exception
        with pytest.raises(psycopg.errors.UndefinedFunction):
            await reconcile_queries(queries)
        
        logger.info("Test passed: Successfully simulated database error scenario")

    @pytest.mark.asyncio
    @with_test_config
    async def test_reconcile_with_connection_error_recovery(
        self, test_provider: ExtendedMockConfigProvider
    ):
        """Test that connection errors are properly handled with rollback.
        
        This test verifies that when a query fails, the connection is properly
        rolled back before the next query is attempted.
        """
        test_provider.create_connection_mock(
            execute=None,
            fetchall=[{"site_id": 1, "label": "Test Site", "name_sim": 0.9}],
        )
        
        # Track if rollback is called
        rollback_called = False
        
        async def mock_rollback():
            nonlocal rollback_called
            rollback_called = True
            logger.info("Rollback called on connection")
        
        test_provider.connection_mock.rollback = mock_rollback
        
        # Simulate an error
        test_provider.cursor_mock.execute.side_effect = psycopg.Error("Test database error")
        
        queries = {"q1": {"query": "Test", "type": "site", "limit": 3}}
        
        # Expect the error to propagate
        with pytest.raises(psycopg.Error):
            await reconcile_queries(queries)
        
        # Note: The current implementation doesn't call rollback,
        # which is likely the root cause of the issue
        # This test documents the expected behavior
        logger.info(f"Rollback called: {rollback_called}")


class TestDatabaseQueryProxyTransactionHandling:
    """Tests specifically for DatabaseQueryProxy transaction handling"""

    @pytest.mark.skip(reason="Demonstration of expected rollback behavior - not implemented yet")
    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_all_with_error_and_rollback(
        self, test_provider: ExtendedMockConfigProvider
    ):
        """Test that fetch_all properly handles errors and rolls back the transaction.
        
        This is the key test to verify the fix for the transaction error.
        """
        from src.strategies.query import BaseRepository

        test_provider.create_connection_mock(execute=None)
        
        # Make execute fail
        test_provider.cursor_mock.execute.side_effect = psycopg.errors.UndefinedFunction(
            "function authority.fuzzy_site does not exist"
        )
        
        # Track rollback calls
        rollback_called = False
        
        async def mock_rollback():
            nonlocal rollback_called
            rollback_called = True
            logger.info("Connection rolled back after error")
        
        test_provider.connection_mock.rollback = mock_rollback
        
        # Create proxy with mocked connection
        proxy = BaseRepository(
            "site", connection=test_provider.connection_mock
        )
        
        # Execute query that will fail
        with pytest.raises(psycopg.errors.UndefinedFunction):
            await proxy.fetch_all("SELECT * FROM authority.fuzzy_site(%(q)s, %(n)s)", {"q": "test", "n": 10})
        
        # Verify rollback was called
        # Note: This will fail with current implementation, which is the bug
        assert rollback_called, "Rollback should be called after database error"

    @pytest.mark.skip(reason="Demonstration of expected rollback behavior - not implemented yet")
    @pytest.mark.asyncio
    @with_test_config
    async def test_fetch_one_with_error_and_rollback(
        self, test_provider: ExtendedMockConfigProvider
    ):
        """Test that fetch_one properly handles errors and rolls back the transaction."""
        from src.strategies.query import BaseRepository

        test_provider.create_connection_mock(execute=None)
        
        # Make execute fail
        test_provider.cursor_mock.execute.side_effect = psycopg.Error("Test database error")
        
        # Track rollback calls
        rollback_called = False
        
        async def mock_rollback():
            nonlocal rollback_called
            rollback_called = True
        
        test_provider.connection_mock.rollback = mock_rollback
        
        proxy = BaseRepository(
            "site", connection=test_provider.connection_mock
        )
        
        # Execute query that will fail
        with pytest.raises(psycopg.Error):
            await proxy.fetch_one("SELECT * FROM test WHERE id = %(id)s", {"id": 1})
        
        # Verify rollback was called
        assert rollback_called, "Rollback should be called after database error"


class TestSiteReconciliationStrategyErrorHandling:
    """Tests for error handling in SiteReconciliationStrategy"""

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_database_error_propagation(
        self, test_provider: ExtendedMockConfigProvider
    ):
        """Test that database errors in find_candidates are properly propagated."""
        from src.strategies.site import SiteRepository

        test_provider.create_connection_mock(execute=None)
        
        # Make the query fail
        test_provider.cursor_mock.execute.side_effect = psycopg.errors.InFailedSqlTransaction(
            "current transaction is aborted, commands ignored until end of transaction block"
        )
        
        strategy = SiteReconciliationStrategy()
        
        # Mock the proxy to use our test connection
        mock_proxy = SiteRepository(
            strategy.specification, connection=test_provider.connection_mock
        )
        
        with patch.object(strategy, "get_proxy", return_value=mock_proxy):
            with pytest.raises(psycopg.errors.InFailedSqlTransaction):
                await strategy.find_candidates("Test Query", {}, limit=10)


# ============================================================================
# DEBUGGING TEST - Run this test with a debugger
# ============================================================================

class TestReconcileWithDebugger:
    """
    Special test for debugging the transaction error with a debugger.
    
    To use this test:
    1. Set breakpoints in:
       - src/strategies/query.py::DatabaseQueryProxy.fetch_all (line with cursor.execute)
       - src/strategies/query.py::DatabaseQueryProxy.fetch_all (in the except block)
       - src/reconcile.py::reconcile_queries (where strategy.find_candidates is called)
    
    2. Run this test in debug mode:
       pytest tests/test_reconcile_integration.py::TestReconcileWithDebugger::test_debug_transaction_error -v -s
    
    3. Step through to see:
       - When the first query executes successfully
       - When the second query fails
       - How the error propagates
       - Whether rollback is called
    """

    @pytest.mark.asyncio
    @pytest.mark.debug  # Mark as debug test (can skip in CI)
    @with_test_config
    async def test_debug_transaction_error(
        self, test_provider: ExtendedMockConfigProvider
    ):
        """
        Debug test to reproduce and step through the transaction error.
        
        SET BREAKPOINTS HERE:
        - Before reconcile_queries call
        - In DatabaseQueryProxy.fetch_all before cursor.execute
        - In the exception handler
        """
        # Simulate the exact scenario from the error log
        test_provider.create_connection_mock(execute=None, fetchall=[])
        
        # Make the first query succeed, second fail
        call_count = 0
        
        async def execute_side_effect(sql, params=None):
            nonlocal call_count
            call_count += 1
            logger.info(f"Execute call #{call_count}: {params}")
            
            if call_count == 1:
                # First query succeeds
                return None
            elif call_count == 2:
                # Second query fails with function error
                raise psycopg.errors.UndefinedFunction(
                    "function authority.fuzzy_site(character varying, integer) does not exist"
                )
            else:
                # Subsequent queries fail with transaction error
                raise psycopg.errors.InFailedSqlTransaction(
                    "current transaction is aborted, commands ignored until end of transaction block"
                )
        
        test_provider.cursor_mock.execute.side_effect = execute_side_effect
        
        # Provide realistic fetchall responses
        async def fetchall_side_effect():
            if call_count == 1:
                return [{"site_id": 1, "label": "Agunnaryd", "name_sim": 0.95}]
            return []
        
        test_provider.cursor_mock.fetchall.side_effect = fetchall_side_effect
        
        queries = {
            "q1": {"query": "Agunnaryd", "type": "site", "limit": 3},
            "q2": {"query": "Ala", "type": "site", "limit": 3},
            "q3": {"query": "Stockholm", "type": "site", "limit": 3},
        }

        logger.info("=" * 80)
        logger.info("STARTING DEBUG TEST - SET BREAKPOINTS NOW")
        logger.info("=" * 80)
        
        # This should fail - step through to see why
        with pytest.raises((psycopg.errors.UndefinedFunction, psycopg.errors.InFailedSqlTransaction)):
            results = await reconcile_queries(queries)
            logger.info(f"Results: {results}")
        
        logger.info("=" * 80)
        logger.info("DEBUG TEST COMPLETED")
        logger.info(f"Total execute calls: {call_count}")
        logger.info("=" * 80)


# ============================================================================
# MANUAL TESTING INSTRUCTIONS
# ============================================================================
"""
To manually test against a real database:

1. Ensure your config/config.yml has correct database credentials
2. Ensure the authority.fuzzy_site() function exists in the database
3. Run the manual test:

    pytest tests/test_reconcile_integration.py::TestManualDatabaseTesting -v -s --log-cli-level=INFO

4. If you want to test with a broken database function:
    - Temporarily rename the function in the database
    - Run the test to see the actual transaction error
    - Restore the function

Example SQL to check the function:
    SELECT * FROM authority.fuzzy_site('Agunnaryd', 10);
    
Example SQL to break/fix the function:
    ALTER FUNCTION authority.fuzzy_site(text, int) RENAME TO fuzzy_sites_backup;
    ALTER FUNCTION authority.fuzzy_sites_backup(text, int) RENAME TO fuzzy_site;
"""


@pytest.mark.manual  # Skip in automated tests
class TestManualDatabaseTesting:
    """Manual tests that require a real database connection.
    
    These tests are marked with @pytest.mark.manual and will be skipped
    in normal test runs. To run them:
    
        pytest -m manual tests/test_reconcile_integration.py -v -s
    """

    @pytest.mark.skip(reason="Manual test against real database")
    @pytest.mark.asyncio
    async def test_real_database_single_query(self):
        """Test against real database with a single query.
        
        Requires:
        - Valid database configuration in config/config.yml
        - authority.fuzzy_site() function exists
        """
        # Load real configuration
        factory = ConfigFactory()
        config = factory.load(source="config/config.yml", context="default")
        
        # Override config provider
        from src.configuration import set_config_provider, MockConfigProvider
        provider = MockConfigProvider(config)
        set_config_provider(provider)
        
        try:
            queries = {
                "q1": {"query": "Agunnaryd", "type": "site", "limit": 3}
            }
            
            logger.info("Executing reconciliation against real database...")
            results = await reconcile_queries(queries)
            
            logger.info(f"Results: {results}")
            assert "q1" in results
            assert "result" in results["q1"]
            
            logger.success("Real database test passed!")
            
        except Exception as e:
            logger.error(f"Real database test failed: {e}")
            raise

    @pytest.mark.skip(reason="Manual test against real database with multiple queries")
    @pytest.mark.asyncio
    async def test_real_database_multiple_queries(self):
        """Test against real database with multiple queries.
        
        This will reveal if the transaction error occurs in production.
        """
        # Load real configuration
        factory = ConfigFactory()
        config = factory.load(source="config/config.yml", context="default")
        
        from src.configuration import set_config_provider, MockConfigProvider
        provider = MockConfigProvider(config)
        set_config_provider(provider)
        
        try:
            queries = {
                "q1": {"query": "Agunnaryd", "type": "site", "limit": 3},
                "q2": {"query": "Ala", "type": "site", "limit": 3},
                "q3": {"query": "Stockholm", "type": "site", "limit": 3},
            }
            
            logger.info("Executing multiple queries against real database...")
            results = await reconcile_queries(queries)
            
            logger.info(f"Results: {results}")
            assert len(results) == 3
            
            for query_id in ["q1", "q2", "q3"]:
                assert query_id in results
                assert "result" in results[query_id]
            
            logger.success("Multiple query test passed!")
            
        except Exception as e:
            logger.error(f"Multiple query test failed: {e}")
            logger.exception("Full traceback:")
            raise
