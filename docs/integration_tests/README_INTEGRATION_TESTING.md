# Integration Testing Guide

This guide explains how to use the integration tests in `test_reconcile_integration.py` to debug the database transaction error.

## The Problem

The error you're experiencing:
```
psycopg.errors.InFailedSqlTransaction: current transaction is aborted, commands ignored until end of transaction block
```

This occurs when:
1. A SQL query fails within a PostgreSQL transaction
2. The transaction enters a "failed" state
3. Subsequent queries are attempted without rolling back the transaction first
4. PostgreSQL rejects all further commands until the transaction is resolved

## Test Structure

The integration test file contains several test classes:

### 1. `TestReconcileIntegration`
Basic integration tests with mocked connections to establish baseline behavior.

### 2. `TestDatabaseQueryProxyTransactionHandling`
Tests specifically for the `DatabaseQueryProxy` class to verify rollback behavior.

**Key Test:** `test_fetch_all_with_error_and_rollback`
- This test will **FAIL** with the current implementation
- It demonstrates that `rollback()` is not being called after errors
- Once you fix the code, this test should pass

### 3. `TestSiteReconciliationStrategyErrorHandling`
Tests for error propagation in the reconciliation strategy.

### 4. `TestReconcileWithDebugger` (⭐ Most Important)
Special test designed for interactive debugging.

### 5. `TestManualDatabaseTesting`
Tests that require a real database connection (marked with `@pytest.mark.manual`).

## How to Debug

### Step 1: Run the Basic Tests

```bash
# Run all integration tests
pytest tests/test_reconcile_integration.py -v

# Run with detailed logging
pytest tests/test_reconcile_integration.py -v -s --log-cli-level=INFO
```

**Expected Result:** Some tests will fail, specifically the ones checking for rollback behavior. This confirms the bug.

### Step 2: Use the Debugger Test

The most powerful test is `test_debug_transaction_error`. To use it:

1. **Set breakpoints** in VS Code or your debugger:
   - `src/strategies/query.py` line 73 (before `cursor.execute`)
   - `src/strategies/query.py` in the exception handler (if it exists)
   - `src/reconcile.py` line 43 (where `strategy.find_candidates` is called)

2. **Run the test in debug mode:**
   ```bash
   # Using pytest with VS Code debugger
   pytest tests/test_reconcile_integration.py::TestReconcileWithDebugger::test_debug_transaction_error -v -s
   
   # Or use VS Code's Test Explorer and click "Debug Test"
   ```

3. **Step through the code** and observe:
   - First query executes successfully
   - Second query fails with a database error
   - **IMPORTANT:** Check if `connection.rollback()` is called
   - Third query would fail with the transaction error

### Step 3: Verify the Fix

After implementing the fix (adding rollback), run:

```bash
# This test should now pass
pytest tests/test_reconcile_integration.py::TestDatabaseQueryProxyTransactionHandling::test_fetch_all_with_error_and_rollback -v
```

## Testing with Real Database

If you want to test against your actual database:

```bash
# Run manual tests (requires real DB)
pytest -m manual tests/test_reconcile_integration.py -v -s
```

**Prerequisites:**
- Valid database configuration in `config/config.yml`
- Database function `authority.fuzzy_site()` must exist

**To simulate the error in production:**
1. Temporarily rename the database function:
   ```sql
   ALTER FUNCTION authority.fuzzy_site(text, int) RENAME TO fuzzy_sites_backup;
   ```

2. Run the manual test - you'll see the exact error from production

3. Restore the function:
   ```sql
   ALTER FUNCTION authority.fuzzy_sites_backup(text, int) RENAME TO fuzzy_sites;
   ```

## The Fix

Based on the tests, you need to add proper error handling to `DatabaseQueryProxy`:

```python
# In src/strategies/query.py

async def fetch_all(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> list[dict[str, Any]]:
    connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
    async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
        try:
            await cursor.execute(sql, params)  # type: ignore
            rows: list[dict[str, Any]] = await cursor.fetchall()
            return [d if isinstance(d, dict) else dict(d) for d in rows]
        except Exception as e:
            # Rollback the transaction on error
            await connection.rollback()
            logger.error(f"Database query failed, transaction rolled back: {e}")
            raise

async def fetch_one(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> dict[str, Any] | None:
    connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
    async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
        try:
            await cursor.execute(sql, params)  # type: ignore
            row: dict[str, Any] | None = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            # Rollback the transaction on error
            await connection.rollback()
            logger.error(f"Database query failed, transaction rolled back: {e}")
            raise
```

## Test Markers

Tests are marked for selective running:

- `@pytest.mark.asyncio` - Async tests (handled automatically with `asyncio_mode = "auto"`)
- `@pytest.mark.debug` - Debug-specific tests
- `@pytest.mark.manual` - Tests requiring manual setup

**Run specific marker groups:**
```bash
pytest -m debug tests/test_reconcile_integration.py
pytest -m manual tests/test_reconcile_integration.py
```

**Skip specific markers:**
```bash
pytest -m "not manual" tests/
```

## VS Code Launch Configuration

Add this to `.vscode/launch.json` for easy debugging:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Debug Integration Test",
            "type": "debugpy",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/test_reconcile_integration.py::TestReconcileWithDebugger::test_debug_transaction_error",
                "-v",
                "-s",
                "--log-cli-level=INFO"
            ],
            "console": "integratedTerminal",
            "justMyCode": false
        }
    ]
}
```

## Troubleshooting

### Test fails with "async def functions are not natively supported"
- **Solution:** The `pyproject.toml` has been updated with `asyncio_mode = "auto"`
- If still failing: `pip install pytest-asyncio`

### Cannot connect to database
- **Solution:** Check `config/config.yml` has correct database credentials
- Verify database is running: `psql -h <host> -U <user> -d <database>`

### Tests pass but production still fails
- **Solution:** The mocks might not accurately reflect production
- Run the manual tests against real database to confirm the fix

## Next Steps

1. Run the basic tests to confirm the bug
2. Use the debug test to step through the code
3. Implement the rollback fix in `src/strategies/query.py`
4. Re-run tests to verify the fix
5. Test in production environment

## Additional Resources

- [Psycopg3 Documentation - Transaction Management](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
- [PostgreSQL Error Codes](https://www.postgresql.org/docs/current/errcodes-appendix.html)
- PostgreSQL error code `25P02` = `in_failed_sql_transaction`
