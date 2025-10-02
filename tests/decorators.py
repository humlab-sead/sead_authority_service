"""Test decorators for configuration management"""

import functools
from typing import Callable, Any
from src.configuration.inject import set_config_provider, MockConfigProvider


def with_test_config(func: Callable) -> Callable:
    """Decorator to automatically set up and tear down test configuration provider.
    
    This decorator expects the test function to have a 'test_provider' parameter
    and automatically handles the provider setup/teardown pattern.
    
    Usage:
        @pytest.mark.asyncio
        @with_test_config
        async def test_something(self, test_provider):
            # Your test code here - provider is already set up
            result = await some_function_that_uses_config()
            assert result == expected
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Find test_provider in the arguments
        test_provider = None
        
        # Check if test_provider is in kwargs
        if 'test_provider' in kwargs:
            test_provider = kwargs['test_provider']
        else:
            # Look for test_provider in args (typically args[1] for class methods)
            for arg in args:
                if isinstance(arg, MockConfigProvider):
                    test_provider = arg
                    break
        
        if test_provider is None:
            raise ValueError("test_provider not found in function arguments. Make sure your test function has a test_provider parameter.")
        
        # Set up the provider
        original_provider = set_config_provider(test_provider)
        
        try:
            # Call the original function
            return await func(*args, **kwargs)
        finally:
            # Always restore the original provider
            set_config_provider(original_provider)
    
    return wrapper


def with_config_context(test_provider_arg_name: str = 'test_provider'):
    """Parameterized decorator for configuration context management.
    
    This version allows you to specify the parameter name if it's different from 'test_provider'.
    
    Usage:
        @pytest.mark.asyncio
        @with_config_context('my_provider')
        async def test_something(self, my_provider):
            # Provider is automatically set up
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get the test provider from the specified argument
            test_provider = kwargs.get(test_provider_arg_name)
            
            if test_provider is None:
                raise ValueError(f"Argument '{test_provider_arg_name}' not found in function parameters.")
            
            # Set up the provider
            original_provider = set_config_provider(test_provider)
            
            try:
                return await func(*args, **kwargs)
            finally:
                set_config_provider(original_provider)
        
        return wrapper
    return decorator