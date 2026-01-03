# Connection Pooling Implementation

## Summary

Implemented PostgreSQL connection pooling using `psycopg-pool` to fix the "current transaction is aborted" error that occurred when database queries failed. The previous singleton connection pattern meant that when any query failed, all subsequent requests would fail until the service was restarted.

## Changes Made

### 1. Dependencies (`pyproject.toml`)
- Added `psycopg-pool>=3.2.0` dependency

### 2. Configuration (`config/config.yml`, `tests/config/config.yml`)
Added pool configuration options:
```yaml
options:
  database:
    pool_min_size: 2      # Minimum connections in pool
    pool_max_size: 10     # Maximum connections in pool
    pool_timeout: 30.0    # Connection timeout in seconds
```

### 3. Connection Pool Setup (`src/configuration/setup.py`)

**Before:** Singleton connection created once
```python
async def connection_factory(cfg: ConfigLike, db_opts_path: str) -> psycopg.AsyncConnection:
    if cfg.get("runtime:connection") is None:
        con = await psycopg.AsyncConnection.connect(dsn)
        cfg.update({"runtime:connection": con})
        return con
    return cfg.get("runtime:connection")
```

**After:** Connection pool with automatic transaction management
```python
async def _setup_connection_pool(cfg: ConfigLike, db_opts_path: str) -> None:
    pool = AsyncConnectionPool(
        conninfo=dsn,
        min_size=pool_min_size,
        max_size=pool_max_size,
        timeout=pool_timeout,
        open=False,
    )
    await pool.open()
    await pool.wait()
    cfg.update({"runtime:connection_pool": pool})
```

**New:** Context manager with automatic commit/rollback
```python
@asynccontextmanager
async def get_connection() -> AsyncIterator[psycopg.AsyncConnection]:
    pool: AsyncConnectionPool = cfg.get("runtime:connection_pool")
    async with pool.connection() as conn:
        try:
            yield conn
            await conn.commit()  # Auto-commit on success
        except Exception as e:
            await conn.rollback()  # Auto-rollback on error
            logger.error(f"Database transaction error, rolled back: {e}")
            raise
```

### 4. Query Methods (`src/strategies/query.py`)

**Before:** Reused singleton connection
```python
async def fetch_all(self, sql: str, params: Params | None = None) -> list[DictRow]:
    connection = await self.get_connection()  # Singleton
    async with connection.cursor() as cursor:
        await cursor.execute(sql, params)
        return await cursor.fetchall()
```

**After:** Get fresh connection from pool with automatic transaction management
```python
async def fetch_all(self, sql: str, params: Params | None = None) -> list[DictRow]:
    async with get_connection() as connection:  # From pool
        async with connection.cursor() as cursor:
            await cursor.execute(sql, params)
            rows = await cursor.fetchall()
            # Transaction auto-commits on success, rolls back on exception
            return [dict(row) for row in rows]
```

### 5. Application Shutdown (`main.py`)

**Added:** Graceful pool shutdown
```python
async def shutdown_connection_pool() -> None:
    pool = cfg.get("runtime:connection_pool")
    if pool:
        logger.info("Closing database connection pool...")
        await pool.close()
        logger.info("Database connection pool closed")
```

### 6. Test Fixtures (`tests/conftest.py`)

**Updated:** Mock connection pool for tests
```python
class ExtendedMockConfigProvider(MockConfigProvider):
    def create_connection_mock(self, **kwargs) -> None:
        connection = create_connection_mock(**kwargs)
        mock_pool = AsyncMock()
        mock_pool.connection.return_value.__aenter__.return_value = connection
        self.get_config().update({"runtime:connection_pool": mock_pool})
```

## Benefits

### 1. **Transaction Isolation**
Each request gets its own connection from the pool, preventing one failed query from breaking all subsequent requests.

### 2. **Automatic Error Recovery**
- Successful queries: Auto-commit
- Failed queries: Auto-rollback
- Connection automatically returned to pool

### 3. **Better Resource Management**
- Connections are reused efficiently
- Pool size limits prevent resource exhaustion
- Idle connections can be recycled

### 4. **Improved Reliability**
- No more "transaction is aborted" cascade failures
- Failed queries don't poison the entire service
- Service remains operational even after database errors

## How It Works

### Request Flow

```
1. Request arrives → GET /reconcile
   ↓
2. async with get_connection() as conn:
   ├─ Pool provides available connection
   ├─ If none available, waits (up to pool_timeout)
   └─ If timeout, raises error
   ↓
3. Execute query
   ├─ Success: conn.commit() → Connection returns to pool
   └─ Error: conn.rollback() → Connection returns to pool (clean state)
```

### Error Handling

**Old Behavior:**
```
Query 1 fails → Connection in error state
Query 2 → "transaction is aborted" error
Query 3 → "transaction is aborted" error
... (all subsequent queries fail until restart)
```

**New Behavior:**
```
Query 1 fails → Rollback → Connection returns to pool
Query 2 → Gets fresh connection → Works normally
Query 3 → Gets fresh connection → Works normally
```

## Configuration Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `pool_min_size` | 2 | Minimum number of connections kept open |
| `pool_max_size` | 10 | Maximum number of connections allowed |
| `pool_timeout` | 30.0 | Max seconds to wait for available connection |

### Tuning Guidelines

**Development:**
```yaml
pool_min_size: 1
pool_max_size: 5
pool_timeout: 10.0
```

**Production:**
```yaml
pool_min_size: 2
pool_max_size: 20
pool_timeout: 30.0
```

**High Traffic:**
```yaml
pool_min_size: 5
pool_max_size: 50
pool_timeout: 60.0
```

## Testing

All existing tests pass with the new connection pooling:
```bash
uv run pytest tests/test_reconcile.py -v
# 6 passed in 1.00s
```

## Rollback Instructions

If needed, revert these commits:
1. Restore `src/configuration/setup.py` to use singleton connection
2. Remove `psycopg-pool` from `pyproject.toml`
3. Remove pool configuration from `config/config.yml`
4. Restore `src/strategies/query.py` to use `get_connection()` method
5. Restore `main.py` shutdown handler

## Related Issues

Fixes: "current transaction is aborted, commands ignored until end of transaction block"

See also: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment guidance.
