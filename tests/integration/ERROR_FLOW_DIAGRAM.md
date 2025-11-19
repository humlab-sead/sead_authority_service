# Error Flow Diagram

## Current Behavior (WITH BUG) ❌

```
┌─────────────────────────────────────────────────────────────────┐
│ OpenRefine sends multiple reconciliation queries                │
│ {"q1": {...}, "q2": {...}, "q3": {...}}                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/reconcile.py::reconcile_queries()                           │
│ - Loops through each query                                      │
│ - Creates strategy for each                                     │
│ - Calls strategy.find_candidates()                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
         ┌───────────────────┴───────────────────┐
         │                                       │
         ▼                                       ▼
┌─────────────────┐                    ┌─────────────────┐
│  Query 1: "A"   │                    │  Query 2: "B"   │
│   SUCCEEDS      │                    │     FAILS       │
└────────┬────────┘                    └────────┬────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐
│ SiteStrategy.find_candidates│       │ SiteStrategy.find_candidates│
└────────┬────────────────────┘       └────────┬────────────────────┘
         │                                      │
         ▼                                      ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐
│ SiteQueryProxy.find()       │       │ SiteQueryProxy.find()       │
└────────┬────────────────────┘       └────────┬────────────────────┘
         │                                     │
         ▼                                     ▼
┌─────────────────────────────┐       ┌─────────────────────────────┐
│ DatabaseQueryProxy.fetch_all│       │ DatabaseQueryProxy.fetch_all│
│                             │       │                             │
│ async with cursor:          │       │ async with cursor:          │
│   cursor.execute(sql)       │       │   cursor.execute(sql) ❌    │
│   rows = cursor.fetchall()  │       │   # SQL ERROR!              │
│   return rows ✅            │       │   # Exception raised        │
│                             │       │   # NO ROLLBACK! ⚠️        │
└────────┬────────────────────┘       └────────┬────────────────────┘
         │                                      │
         │                                      │ Exception propagates
         │                                      │ Transaction in ERROR state
         │                                      ▼
         │                             ┌─────────────────────────────┐
         │                             │ Back to reconcile_queries() │
         │                             │ Exception caught/logged     │
         │                             │ Loop continues to Query 3   │
         │                             └────────┬────────────────────┘
         │                                      │
         │                                      ▼
         └──────────────────────────────────────┴──────────────┐
                                                                │
                                                                ▼
                                                      ┌─────────────────┐
                                                      │  Query 3: "C"   │
                                                      │  ❌ FAILS       │
                                                      └────────┬────────┘
                                                               │
                                                               ▼
                                              ┌─────────────────────────────────┐
                                              │ DatabaseQueryProxy.fetch_all    │
                                              │                                 │
                                              │ async with cursor:              │
                                              │   cursor.execute(sql) ❌        │
                                              │   # Transaction already broken! │
                                              │   # PostgreSQL rejects command  │
                                              │   # Error: "transaction aborted"│
                                              └────────┬────────────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────────────────────┐
                                              │ ERROR MESSAGE:                  │
                                              │ "current transaction is aborted,│
                                              │  commands ignored until end of  │
                                              │  transaction block"             │
                                              └─────────────────────────────────┘
```

## Expected Behavior (WITH FIX) ✅

```
┌─────────────────────────────────────────────────────────────────┐
│ OpenRefine sends multiple reconciliation queries                │
│ {"q1": {...}, "q2": {...}, "q3": {...}}                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│ src/reconcile.py::reconcile_queries()                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
         ┌───────────────────┴───────────────────┬──────────────────┐
         │                                       │                  │
         ▼                                       ▼                  ▼
┌─────────────────┐                    ┌─────────────────┐  ┌─────────────────┐
│  Query 1: "A"   │                    │  Query 2: "B"   │  │  Query 3: "C"   │
│  ✅ SUCCEEDS    │                    │  ❌ FAILS       │  │  ✅ SUCCEEDS    │
└────────┬────────┘                    └────────┬────────┘  └────────┬────────┘
         │                                       │                    │
         ▼                                       ▼                    ▼
┌───────────────────┐              ┌─────────────────────────┐ ┌────────────────┐
│ fetch_all():      │              │ fetch_all():            │ │ fetch_all():   │
│   try:            │              │   try:                  │ │   try:         │
│     execute() ✅  │              │     execute() ❌        │ │     execute()✅│
│     return rows   │              │   except Exception:     │ │     return rows│
│                   │              │     rollback() ✅       │ │                │
└───────────────────┘              │     logger.error()      │ └────────────────┘
                                   │     raise               │
                                   └────────┬────────────────┘
                                            │
                                            ▼
                                   ┌─────────────────────────────┐
                                   │ Transaction ROLLED BACK ✅  │
                                   │ Connection is CLEAN         │
                                   │ Ready for next query        │
                                   └─────────────────────────────┘
```

## Key Differences

### Without Fix ❌
1. Query fails
2. Exception propagates
3. **Transaction stays in error state**
4. Next query fails with "transaction aborted"

### With Fix ✅
1. Query fails
2. **Transaction is rolled back**
3. Connection is clean
4. Next query works normally

## The Critical Code Change

### Before (Broken):
```python
async def fetch_all(self, sql: str, params: Params | None = None, ...):
    connection = await self.get_connection()
    async with connection.cursor(...) as cursor:
        await cursor.execute(sql, params)  # ← Fails here
        rows = await cursor.fetchall()
        return rows
    # Exception propagates
    # Transaction stays broken ❌
```

### After (Fixed):
```python
async def fetch_all(self, sql: str, params: Params | None = None, ...):
    connection = await self.get_connection()
    async with connection.cursor(...) as cursor:
        try:
            await cursor.execute(sql, params)  # ← Fails here
            rows = await cursor.fetchall()
            return rows
        except Exception as e:
            await connection.rollback()  # ← CLEANUP! ✅
            logger.error(f"Query failed, rolled back: {e}")
            raise  # Re-raise for proper error handling
```

## PostgreSQL Transaction States

```
Normal Flow:
┌────────┐  BEGIN   ┌──────────┐  COMMIT  ┌────────┐
│ IDLE   │─────────▶│ IN TRANS │─────────▶│ IDLE   │
└────────┘          └──────────┘          └────────┘
                         │
                         │ Query executes
                         │ successfully
                         ▼
                    ┌──────────┐
                    │ IN TRANS │
                    └──────────┘

Error Flow (Without Fix):
┌────────┐  BEGIN   ┌──────────┐  ERROR!  ┌─────────────┐
│ IDLE   │─────────▶│ IN TRANS │─────────▶│ INERROR ❌ │
└────────┘          └──────────┘          └──────┬──────┘
                                                  │
                                         All commands rejected!
                                         Must ROLLBACK to recover
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │ Next command │
                                          │ REJECTED ❌ │
                                          └──────────────┘

Error Flow (With Fix):
┌────────┐  BEGIN   ┌──────────┐  ERROR!  ┌─────────────┐
│ IDLE   │─────────▶│ IN TRANS │─────────▶│ INERROR     │
└────────┘          └──────────┘          └──────┬──────┘
                                                  │
                                           ROLLBACK ✅
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │ IDLE ✅      │
                                          │ Ready!       │
                                          └──────────────┘
```

## Real-World Example

### Without Fix (What Happens Now):

```
Request: Reconcile ["Agunnaryd", "Ala", "Stockholm"]

Query 1: "Agunnaryd"
  ✅ SELECT * FROM authority.fuzzy_sites('Agunnaryd', 10)
  → Returns results

Query 2: "Ala"  
  ❌ SELECT * FROM authority.fuzzy_sites('Ala', 10)
  → Function error (maybe doesn't exist or has bug)
  → Exception thrown
  → Transaction enters ERROR state
  → NO ROLLBACK

Query 3: "Stockholm"
  ❌ SELECT * FROM authority.fuzzy_sites('Stockholm', 10)
  → PostgreSQL says: "Nope! Transaction is broken!"
  → Error: "current transaction is aborted"
  → User sees error in OpenRefine
```

### With Fix (What Should Happen):

```
Request: Reconcile ["Agunnaryd", "Ala", "Stockholm"]

Query 1: "Agunnaryd"
  ✅ SELECT * FROM authority.fuzzy_sites('Agunnaryd', 10)
  → Returns results

Query 2: "Ala"
  ❌ SELECT * FROM authority.fuzzy_sites('Ala', 10)
  → Function error
  → Exception caught
  → ROLLBACK executed ✅
  → Transaction cleaned up
  → Error logged

Query 3: "Stockholm"
  ✅ SELECT * FROM authority.fuzzy_sites('Stockholm', 10)
  → Works normally!
  → Returns results
  → User sees results for queries 1 and 3
  → Query 2 shows no results (which is correct)
```

## Testing the Fix

Run this test to see the bug:
```bash
pytest tests/test_reconcile_integration.py::TestDatabaseQueryProxyTransactionHandling::test_fetch_all_with_error_and_rollback -v
```

**Before fix:** Test FAILS - rollback not called  
**After fix:** Test PASSES - rollback called ✅

## Summary

**Root Cause:** Missing error handling with rollback in `DatabaseQueryProxy`  
**Impact:** Any database error breaks all subsequent queries  
**Fix:** Add try/except with `await connection.rollback()` on error  
**Verification:** Integration test confirms rollback is called  

**Files to modify:**
- `src/strategies/query.py` - Add rollback in `fetch_all()` and `fetch_one()`
