# Code Fix: Add Transaction Rollback

## File to Modify

**Path:** `src/strategies/query.py`

## Changes Needed

You need to update **TWO methods** in the `DatabaseQueryProxy` class:
1. `fetch_all()`
2. `fetch_one()`

---

## Change 1: Update `fetch_all()` method

### Current Code (Lines ~68-75):

```python
async def fetch_all(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> list[dict[str, Any]]:
    connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
    async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
        await cursor.execute(sql, params)  # type: ignore
        rows: list[dict[str, Any]] = await cursor.fetchall()
        return [d if isinstance(d, dict) else dict(d) for d in rows]
```

### Updated Code (WITH FIX):

```python
async def fetch_all(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> list[dict[str, Any]]:
    connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
    async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
        try:
            await cursor.execute(sql, params)  # type: ignore
            rows: list[dict[str, Any]] = await cursor.fetchall()
            return [d if isinstance(d, dict) else dict(d) for d in rows]
        except Exception as e:
            # Rollback the transaction on error to prevent "transaction aborted" errors
            await connection.rollback()
            logger.error(f"Database query failed, transaction rolled back: {e}")
            raise
```

**What Changed:**
- Wrapped the `cursor.execute()` and `cursor.fetchall()` in a `try` block
- Added `except Exception as e:` to catch any database errors
- Call `await connection.rollback()` to clean up the failed transaction
- Log the error with context
- Re-raise the exception so it propagates properly

---

## Change 2: Update `fetch_one()` method

### Current Code (Lines ~77-82):

```python
async def fetch_one(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> dict[str, Any] | None:
    connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
    async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
        await cursor.execute(sql, params)  # type: ignore
        row: dict[str, Any] | None = await cursor.fetchone()
        return dict(row) if row else None
```

### Updated Code (WITH FIX):

```python
async def fetch_one(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> dict[str, Any] | None:
    connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
    async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
        try:
            await cursor.execute(sql, params)  # type: ignore
            row: dict[str, Any] | None = await cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            # Rollback the transaction on error to prevent "transaction aborted" errors
            await connection.rollback()
            logger.error(f"Database query failed, transaction rolled back: {e}")
            raise
```

**What Changed:**
- Same pattern as `fetch_all()`
- Added try/except block
- Rollback on error
- Log and re-raise

---

## Complete Updated Class (For Reference)

Here's the full `DatabaseQueryProxy` class with both fixes applied:

```python
class DatabaseQueryProxy(QueryProxy):
    def __init__(self, specification: StrategySpecification, **kwargs) -> None:
        super().__init__(specification, **kwargs)
        self.connection: psycopg.AsyncConnection | None = kwargs.get("connection")
        self.row_factories: dict[str, Any] = {
            "dict": dict_row,
            "tuple": tuple_row,
        }

    async def get_connection(self) -> psycopg.AsyncConnection:
        if not self.connection:
            self.connection = await get_connection()
        return self.connection

    async def fetch_all(self, sql: str, params: Params | None = None, *, row_factory: Literal["dict", "tuple"] = "dict") -> list[dict[str, Any]]:
        connection: psycopg.AsyncConnection[Tuple[Any, ...]] = await self.get_connection()
        async with connection.cursor(row_factory=self.row_factories[row_factory]) as cursor:
            try:
                await cursor.execute(sql, params)  # type: ignore
                rows: list[dict[str, Any]] = await cursor.fetchall()
                return [d if isinstance(d, dict) else dict(d) for d in rows]
            except Exception as e:
                # Rollback the transaction on error to prevent "transaction aborted" errors
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
                # Rollback the transaction on error to prevent "transaction aborted" errors
                await connection.rollback()
                logger.error(f"Database query failed, transaction rolled back: {e}")
                raise

    def get_sql_queries(self) -> dict[str, str]:
        """Return the SQL queries defined in the specification"""
        return self.specification.get("sql_queries", {})

    def get_sql_query(self, key: str) -> str:
        """Return the SQL query defined in the specification for a given key."""
        return self.get_sql_queries().get(key, "")

    def get_details_sql(self) -> str:
        """Return the SQL query for fetching detailed information for a given entity ID."""
        return self.get_sql_query("details_sql")

    async def get_details(self, entity_id: str, **kwargs) -> dict[str, Any] | None:
        """Fetch details for a specific location."""
        try:
            return await self.fetch_one(self.get_details_sql(), {"id": int(entity_id)})
        except (ValueError, psycopg.Error) as e:
            logger.error(f"Error fetching details for entity_id {entity_id}: {e}")
            return None

    async def find(self, name: str, limit: int = 10, **kwargs) -> list[dict[str, Any]]:
        """Perform fuzzy name search"""
        return await self.fetch_all(self.get_sql_query("fuzzy_find_sql"), {"q": name, "n": limit})

    async def fetch_by_alternate_identity(self, alternate_identity: str, **kwargs) -> list[dict[str, Any]]:
        """Fetch entity by alternate identity"""
        sql: str = self.get_sql_query("alternate_identity_sql")
        if not sql:
            return []
        return await self.fetch_all(sql, {"alternate_identity": alternate_identity})
```

---

## How to Apply

### Option 1: Manual Edit
1. Open `src/strategies/query.py`
2. Find the `fetch_all()` method (around line 68)
3. Replace with the updated version above
4. Find the `fetch_one()` method (around line 77)
5. Replace with the updated version above
6. Save the file

### Option 2: Use the Test Tool
Use the `multi_replace_string_in_file` tool to apply both changes at once.

---

## Verification Steps

### 1. Run the specific test that checks for rollback:
```bash
pytest tests/test_reconcile_integration.py::TestDatabaseQueryProxyTransactionHandling::test_fetch_all_with_error_and_rollback -v
```

**Expected result after fix:** ✅ PASSED

### 2. Run all database proxy tests:
```bash
pytest tests/test_reconcile_integration.py::TestDatabaseQueryProxyTransactionHandling -v
```

**Expected result after fix:** ✅ Both tests PASSED

### 3. Run the full integration test suite:
```bash
pytest tests/test_reconcile_integration.py -v
```

**Expected result after fix:** ✅ Most/all tests PASSED (manual tests will be skipped)

### 4. Test in your development environment:
Restart your server and try the reconciliation that was failing:
```bash
# Stop existing server
kill $(cat uvicorn.pid)

# Start server
uvicorn main:app --host 0.0.0.0 --port 8000

# Try your reconciliation request
```

---

## Why This Works

**Before Fix:**
```
Query 1 → Success → Transaction OK
Query 2 → Fails → Transaction BROKEN → No cleanup
Query 3 → Tries to execute → PostgreSQL rejects it → ERROR
```

**After Fix:**
```
Query 1 → Success → Transaction OK
Query 2 → Fails → ROLLBACK called → Transaction cleaned → Connection ready
Query 3 → Tries to execute → PostgreSQL accepts it → SUCCESS
```

---

## Additional Considerations

### Connection Pooling
If you're using connection pooling, you might want to also ensure connections are properly returned to the pool:

```python
async def fetch_all(...):
    connection = await self.get_connection()
    try:
        async with connection.cursor(...) as cursor:
            try:
                await cursor.execute(sql, params)
                rows = await cursor.fetchall()
                return rows
            except Exception as e:
                await connection.rollback()
                logger.error(f"Query failed: {e}")
                raise
    finally:
        # If you're managing connection lifecycle here
        # await connection.close()  # Only if not using a connection pool
        pass
```

### Alternative: Use Transaction Context Manager
Another approach is to use psycopg's transaction context manager:

```python
async def fetch_all(...):
    connection = await self.get_connection()
    async with connection.transaction():  # Auto-rollback on exception
        async with connection.cursor(...) as cursor:
            await cursor.execute(sql, params)
            rows = await cursor.fetchall()
            return rows
```

However, this might conflict with how you're managing transactions elsewhere, so the explicit rollback approach is safer.

---

## Summary

- **Files to modify:** `src/strategies/query.py`
- **Methods to update:** `fetch_all()`, `fetch_one()`
- **Change:** Add try/except with `await connection.rollback()`
- **Verification:** Run the integration tests
- **Impact:** Fixes the "transaction aborted" error

After applying this fix, multiple queries in a single reconciliation request will work correctly even if one of them fails.
