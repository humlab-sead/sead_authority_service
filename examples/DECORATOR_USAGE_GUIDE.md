"""
Example of how to refactor your tests with the @with_test_config decorator

BEFORE (manual provider management):
```python
@pytest.mark.asyncio
async def test_something(self, test_provider):
    \"\"\"Test description\"\"\"
    original_provider = set_config_provider(test_provider)
    try:
        # Your test logic here
        result = await some_function()
        assert result == expected
    finally:
        set_config_provider(original_provider)
```

AFTER (with decorator):
```python
@pytest.mark.asyncio
@with_test_config
async def test_something(self, test_provider):
    \"\"\"Test description\"\"\"
    # Your test logic here - provider setup/teardown is automatic!
    result = await some_function()
    assert result == expected
```

BENEFITS:
✅ Eliminates boilerplate try/finally blocks
✅ Ensures provider is always restored (even if test fails)  
✅ Makes tests more readable and focused on logic
✅ Reduces chances of forgetting provider cleanup
✅ Consistent pattern across all tests

USAGE PATTERNS:

1. Basic usage (most common):
   @pytest.mark.asyncio
   @with_test_config
   async def test_name(self, test_provider): ...

2. For functions with different parameter names:
   @pytest.mark.asyncio
   @with_config_context('my_provider')  
   async def test_name(self, my_provider): ...

3. Can be combined with other decorators:
   @pytest.mark.asyncio
   @patch('some.module')
   @with_test_config
   async def test_name(self, mock_obj, test_provider): ...

WHAT TO REFACTOR:
- All tests that have the pattern: set_config_provider() ... try/finally
- Any test that uses MockConfigProvider
- Tests that call render_preview() or other functions using ConfigValue

WHAT NOT TO REFACTOR:
- Tests that don't use configuration (like pure unit tests)
- Tests that manually create their own providers for specific testing
- Tests in TestRenderPreviewEdgeCases that test the provider system itself
"""