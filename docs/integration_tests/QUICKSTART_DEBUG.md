# Quick Start: Debugging the Transaction Error

## What You Have Now

I've created a comprehensive integration testing setup to help you debug the PostgreSQL transaction error:

```
current transaction is aborted, commands ignored until end of transaction block
```

## Files Created/Updated

1. **`tests/test_reconcile_integration.py`** - Complete integration test suite
2. **`tests/README_INTEGRATION_TESTING.md`** - Detailed documentation
3. **`pyproject.toml`** - Updated with pytest configuration and markers
4. **`.vscode/launch.json`** - Debug configurations for VS Code

## Quick Debug Steps

### Option 1: Interactive Debugging (Recommended)

1. **Open VS Code Debug Panel** (Ctrl+Shift+D or Cmd+Shift+D)

2. **Set Breakpoints:**
   - `src/strategies/query.py` - Line 73 (inside `fetch_all`, before `cursor.execute`)
   - `src/reconcile.py` - Line 43 (where `strategy.find_candidates` is called)

3. **Select debug configuration:** "Debug: Integration Test (Transaction Error)"

4. **Press F5** to start debugging

5. **Step through** and observe:
   - First query executes
   - Second query fails
   - **Check:** Is `connection.rollback()` called? (It shouldn't be - that's the bug!)

### Option 2: Command Line Testing

```bash
# Run all integration tests
pytest tests/test_reconcile_integration.py -v

# Run with detailed output
pytest tests/test_reconcile_integration.py -v -s --log-cli-level=INFO

# Run only the debug test
pytest tests/test_reconcile_integration.py::TestReconcileWithDebugger -v -s
```

### Option 3: Test with Real Database

```bash
# Ensure config/config.yml has correct DB credentials
pytest -m manual tests/test_reconcile_integration.py -v -s
```

## The Root Cause

The error occurs in `DatabaseQueryProxy` (`src/strategies/query.py`):

**Current Code (BROKEN):**
```python
async def fetch_all(self, sql: str, params: Params | None = None, ...):
    connection = await self.get_connection()
    async with connection.cursor(...) as cursor:
        await cursor.execute(sql, params)  # ← If this fails...
        rows = await cursor.fetchall()
        return [d if isinstance(d, dict) else dict(d) for d in rows]
    # ← Transaction stays in error state, no rollback!
```

**Problem:** When `cursor.execute()` fails, the exception propagates but the transaction is **not rolled back**. The next query attempt fails with the "transaction aborted" error.

## The Fix

Add proper error handling with rollback:

```python
async def fetch_all(self, sql: str, params: Params | None = None, ...):
    connection = await self.get_connection()
    async with connection.cursor(...) as cursor:
        try:
            await cursor.execute(sql, params)
            rows = await cursor.fetchall()
            return [d if isinstance(d, dict) else dict(d) for d in rows]
        except Exception as e:
            # CRITICAL: Rollback the failed transaction
            await connection.rollback()
            logger.error(f"Database query failed, transaction rolled back: {e}")
            raise
```

**Apply the same fix to `fetch_one()`** method.

## Verify the Fix

After implementing the fix, run this test:

```bash
pytest tests/test_reconcile_integration.py::TestDatabaseQueryProxyTransactionHandling::test_fetch_all_with_error_and_rollback -v
```

**Before fix:** Test FAILS ❌  
**After fix:** Test PASSES ✅

## Alternative Solutions

### Option 1: Connection Pool with Auto-Rollback
Configure psycopg connection pool to automatically rollback on error:

```python
# In src/configuration/setup.py or wherever you create connections
connection = await psycopg.AsyncConnection.connect(
    conninfo=connection_string,
    autocommit=False,  # Keep transactions
    # Add connection options
)
```

### Option 2: Context Manager for Transactions
Use proper transaction context managers:

```python
async def fetch_all(self, sql: str, params: Params | None = None, ...):
    connection = await self.get_connection()
    async with connection.transaction():  # ← Automatic rollback on exception
        async with connection.cursor(...) as cursor:
            await cursor.execute(sql, params)
            rows = await cursor.fetchall()
            return [d if isinstance(d, dict) else dict(d) for d in rows]
```

### Option 3: One Connection Per Query
Instead of reusing connections, create a fresh connection for each query (less efficient but safer):

```python
async def fetch_all(self, sql: str, params: Params | None = None, ...):
    async with await psycopg.AsyncConnection.connect(...) as connection:
        async with connection.cursor(...) as cursor:
            await cursor.execute(sql, params)
            return await cursor.fetchall()
```

## Testing Checklist

- [ ] Run basic integration tests
- [ ] Use debugger to step through error scenario
- [ ] Implement rollback fix in `DatabaseQueryProxy`
- [ ] Verify test_fetch_all_with_error_and_rollback passes
- [ ] Test with real database using manual tests
- [ ] Test full reconciliation workflow in production

## Additional Resources

- **Full Documentation:** `tests/README_INTEGRATION_TESTING.md`
- **Test File:** `tests/test_reconcile_integration.py`
- **Psycopg Docs:** https://www.psycopg.org/psycopg3/docs/basic/transactions.html

## Need Help?

The integration tests are extensively commented. Each test class has a docstring explaining its purpose and how to use it.

**Key Test for Debugging:**
```python
TestReconcileWithDebugger.test_debug_transaction_error
```

This test is specifically designed for stepping through with a debugger and has detailed logging.
