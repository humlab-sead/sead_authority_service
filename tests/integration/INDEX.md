# Integration Testing Documentation Index

This directory contains comprehensive testing and debugging resources for the PostgreSQL transaction error.

## 📋 Quick Navigation

### 🚀 Getting Started
- **[SETUP_COMPLETE.md](SETUP_COMPLETE.md)** - Overview of everything created
- **[QUICKSTART_DEBUG.md](QUICKSTART_DEBUG.md)** - Fast start guide (3 ways to debug)

### 📖 Understanding the Problem  
- **[ERROR_FLOW_DIAGRAM.md](ERROR_FLOW_DIAGRAM.md)** - Visual explanation of the bug
- **[README_INTEGRATION_TESTING.md](README_INTEGRATION_TESTING.md)** - Complete documentation

### 🔧 Implementing the Fix
- **[CODE_FIX.md](CODE_FIX.md)** - Exact code changes needed (copy-paste ready)

### 🧪 Test Files
- **[test_reconcile_integration.py](test_reconcile_integration.py)** - The integration test suite
- **[conftest.py](conftest.py)** - Test fixtures and utilities

## 📚 Documentation Files

### 1. SETUP_COMPLETE.md
**Purpose:** Summary of what was created  
**Read if:** You want an overview of the entire setup  
**Contains:**
- List of all files created
- What each test does
- Verification that tests work
- Next steps

### 2. QUICKSTART_DEBUG.md
**Purpose:** Fast reference for debugging  
**Read if:** You want to start debugging immediately  
**Contains:**
- 3 debugging methods (VS Code, CLI, Real DB)
- The exact fix needed
- Verification commands
- Alternative solutions

### 3. ERROR_FLOW_DIAGRAM.md
**Purpose:** Visual explanation of the problem  
**Read if:** You want to understand what's happening  
**Contains:**
- Flow diagrams (current vs. fixed behavior)
- Transaction state diagrams
- Real-world examples
- Key differences explained

### 4. README_INTEGRATION_TESTING.md
**Purpose:** Comprehensive testing guide  
**Read if:** You want complete details  
**Contains:**
- Detailed problem explanation
- Test structure breakdown
- Step-by-step debugging instructions
- Multiple fix approaches
- Troubleshooting section
- VS Code configuration

### 5. CODE_FIX.md
**Purpose:** Exact code changes  
**Read if:** You're ready to implement the fix  
**Contains:**
- Current code (broken)
- Fixed code (with changes highlighted)
- Complete updated class
- Verification steps
- Why it works

## 🧪 Test Files

### test_reconcile_integration.py
**Purpose:** Integration tests for debugging  
**Contains 9 tests in 5 classes:**

1. **TestReconcileIntegration**
   - `test_reconcile_single_query_with_mocked_connection` - Basic test
   - `test_reconcile_multiple_queries_simulating_transaction_error` - Simulate error
   - `test_reconcile_with_connection_error_recovery` - Test rollback behavior

2. **TestDatabaseQueryProxyTransactionHandling** ⭐
   - `test_fetch_all_with_error_and_rollback` - KEY TEST for the bug
   - `test_fetch_one_with_error_and_rollback` - Test fetch_one rollback

3. **TestSiteReconciliationStrategyErrorHandling**
   - `test_find_candidates_database_error_propagation` - Error propagation

4. **TestReconcileWithDebugger** ⭐
   - `test_debug_transaction_error` - INTERACTIVE debugging test

5. **TestManualDatabaseTesting**
   - `test_real_database_single_query` - Test with real DB
   - `test_real_database_multiple_queries` - Multiple queries with real DB

### conftest.py
**Purpose:** Test fixtures and utilities  
**Already existed, not modified**

## 🎯 Usage Scenarios

### Scenario 1: "I want to understand the problem"
1. Read [ERROR_FLOW_DIAGRAM.md](ERROR_FLOW_DIAGRAM.md)
2. Look at the visual diagrams
3. Read the real-world example

### Scenario 2: "I want to debug interactively"
1. Read [QUICKSTART_DEBUG.md](QUICKSTART_DEBUG.md) - "Quick Debug" section
2. Open VS Code Debug panel
3. Set breakpoints
4. Run "Debug: Integration Test (Transaction Error)"

### Scenario 3: "I want to understand the tests"
1. Read [README_INTEGRATION_TESTING.md](README_INTEGRATION_TESTING.md)
2. Check the "Test Structure" section
3. Read about each test class

### Scenario 4: "I want to implement the fix"
1. Read [CODE_FIX.md](CODE_FIX.md)
2. Copy the updated code
3. Apply to `src/strategies/query.py`
4. Run verification commands

### Scenario 5: "I want to test with my database"
1. Read [README_INTEGRATION_TESTING.md](README_INTEGRATION_TESTING.md) - "Testing with Real Database"
2. Ensure DB credentials in `config/config.yml`
3. Run: `pytest -m manual tests/test_reconcile_integration.py -v`

## 🔍 Key Commands

### Run Tests
```bash
# All integration tests
pytest tests/test_reconcile_integration.py -v

# Key bug-demonstrating test
pytest tests/test_reconcile_integration.py::TestDatabaseQueryProxyTransactionHandling::test_fetch_all_with_error_and_rollback -v

# Debug test (for interactive debugging)
pytest tests/test_reconcile_integration.py::TestReconcileWithDebugger -v -s

# Manual tests (requires real DB)
pytest -m manual tests/test_reconcile_integration.py -v
```

### Verify Fix
```bash
# After implementing the fix, this should pass
pytest tests/test_reconcile_integration.py::TestDatabaseQueryProxyTransactionHandling -v
```

## 🏗️ File Structure

```
tests/
├── INDEX.md                          ← You are here
├── SETUP_COMPLETE.md                 ← Overview
├── QUICKSTART_DEBUG.md               ← Fast start
├── ERROR_FLOW_DIAGRAM.md             ← Visual explanation
├── README_INTEGRATION_TESTING.md     ← Complete guide
├── CODE_FIX.md                       ← Exact code changes
├── test_reconcile_integration.py     ← Test suite
└── conftest.py                       ← Test fixtures
```

## 📊 Reading Order

### If you have 5 minutes:
1. [QUICKSTART_DEBUG.md](QUICKSTART_DEBUG.md)
2. Run the debug test

### If you have 15 minutes:
1. [SETUP_COMPLETE.md](SETUP_COMPLETE.md)
2. [ERROR_FLOW_DIAGRAM.md](ERROR_FLOW_DIAGRAM.md)
3. [CODE_FIX.md](CODE_FIX.md)
4. Implement the fix

### If you have 30 minutes:
1. [SETUP_COMPLETE.md](SETUP_COMPLETE.md)
2. [ERROR_FLOW_DIAGRAM.md](ERROR_FLOW_DIAGRAM.md)
3. [README_INTEGRATION_TESTING.md](README_INTEGRATION_TESTING.md)
4. [CODE_FIX.md](CODE_FIX.md)
5. Run tests and debug interactively
6. Implement and verify the fix

## ✅ Success Checklist

- [ ] Read relevant documentation
- [ ] Understand the problem (see ERROR_FLOW_DIAGRAM.md)
- [ ] Run the key test and see it fail (expected)
- [ ] Debug interactively with breakpoints
- [ ] Implement the fix from CODE_FIX.md
- [ ] Run tests and see them pass
- [ ] Test in development environment
- [ ] Deploy to production

## 🆘 Getting Help

### Tests not running?
- Check: `pyproject.toml` has `asyncio_mode = "auto"`
- Install: `pip install pytest-asyncio`
- See: [README_INTEGRATION_TESTING.md](README_INTEGRATION_TESTING.md) - Troubleshooting

### Don't understand the error?
- See: [ERROR_FLOW_DIAGRAM.md](ERROR_FLOW_DIAGRAM.md)
- Read the "Real-World Example" section

### Need to debug interactively?
- See: [QUICKSTART_DEBUG.md](QUICKSTART_DEBUG.md) - Option 1
- Use VS Code debug configuration: "Debug: Integration Test (Transaction Error)"

### Want to test with real database?
- See: [README_INTEGRATION_TESTING.md](README_INTEGRATION_TESTING.md) - "Testing with Real Database"
- Run: `pytest -m manual tests/test_reconcile_integration.py -v`

## 🎓 Learning Resources

### Understanding PostgreSQL Transactions
- [Psycopg3 Documentation](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
- [PostgreSQL Error Codes](https://www.postgresql.org/docs/current/errcodes-appendix.html)
- Error Code `25P02`: `in_failed_sql_transaction`

### Understanding Async Python
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)
- [Async context managers](https://docs.python.org/3/reference/datamodel.html#async-context-managers)

### Testing with pytest
- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)

## 📝 Notes

- All tests have extensive docstrings explaining their purpose
- Tests are marked with `@pytest.mark.debug` and `@pytest.mark.manual` for selective running
- The integration tests use mocked connections by default (safe to run)
- Manual tests require real database setup
- VS Code launch configurations are pre-configured in `.vscode/launch.json`

## 🔗 Related Files

### Configuration
- `pyproject.toml` - pytest configuration with `asyncio_mode = "auto"`
- `.vscode/launch.json` - VS Code debug configurations

### Source Files to Fix
- `src/strategies/query.py` - **PRIMARY FILE TO MODIFY**
- `src/reconcile.py` - Uses the query proxy
- `src/strategies/site.py` - Site-specific strategy

### Existing Tests
- `tests/test_site.py` - Unit tests for site strategy
- `tests/test_query_proxy.py` - Unit tests for query proxy
- `tests/test_router.py` - API endpoint tests

---

**Last Updated:** November 19, 2025  
**Status:** Setup complete and verified ✅  
**Next Action:** Start with [QUICKSTART_DEBUG.md](QUICKSTART_DEBUG.md)
