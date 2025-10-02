"""
Example usage of the new ConfigStore with Provider Pattern

This demonstrates how to use the enhanced configuration system that combines:
- Option 1: Singleton Pattern (ConfigStore)  
- Option 3: Provider Layer (ConfigProvider abstraction)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.configuration.config import Config
from src.configuration.inject import (
    ConfigStore,
    ConfigValue, 
    TestConfigProvider,
    SingletonConfigProvider,
    set_config_provider,
    reset_config_provider,
    get_config_provider
)


def production_example():
    """Example of production usage - uses singleton ConfigStore"""
    print("=== Production Example ===")
    
    # In production, configure the singleton once at startup
    store = ConfigStore.get_instance()
    config = Config(data={
        "database": {"host": "prod-server", "port": 5432},
        "options": {"id_base": "https://w3id.org/sead/id/"}
    })
    store.store["default"] = config
    
    # Now ConfigValue works anywhere in your code
    db_host = ConfigValue("database:host")
    id_base = ConfigValue("options:id_base")
    
    print(f"Database host: {db_host.resolve()}")
    print(f"ID base: {id_base.resolve()}")
    
    # The provider layer uses the singleton by default
    provider = get_config_provider()
    print(f"Current provider: {type(provider).__name__}")
    print(f"Provider config: {provider.get_config().get('database:host')}")


def testing_example():
    """Example of testing usage - uses TestConfigProvider"""
    print("\n=== Testing Example ===")
    
    # Create test configuration
    test_config = Config(data={
        "database": {"host": "test-server", "port": 5433},
        "options": {"id_base": "https://test.example.com/sead/id/"}
    })
    
    # Swap to test provider
    test_provider = TestConfigProvider(test_config)
    original_provider = set_config_provider(test_provider)
    
    try:
        # Same ConfigValue code, but now uses test config
        db_host = ConfigValue("database:host")
        id_base = ConfigValue("options:id_base")
        
        print(f"Test database host: {db_host.resolve()}")
        print(f"Test ID base: {id_base.resolve()}")
        
        provider = get_config_provider()
        print(f"Current provider: {type(provider).__name__}")
        
    finally:
        # Always restore original provider
        set_config_provider(original_provider)


def context_manager_example():
    """Example using context manager for cleaner testing"""
    print("\n=== Context Manager Example ===")
    
    from contextlib import contextmanager
    
    @contextmanager
    def test_config_context(config_data):
        """Context manager for temporary test configuration"""
        config = Config(data=config_data)
        provider = TestConfigProvider(config)
        original = set_config_provider(provider)
        try:
            yield config
        finally:
            set_config_provider(original)
    
    # Usage in tests
    test_data = {
        "database": {"host": "context-test-server"},
        "options": {"id_base": "https://context.test.com/sead/id/"}
    }
    
    with test_config_context(test_data):
        db_host = ConfigValue("database:host")
        print(f"Context test host: {db_host.resolve()}")


def pytest_fixture_example():
    """Example of pytest fixtures using the provider system"""
    print("\n=== Pytest Fixture Pattern ===")
    
    # This is what your test fixtures would look like:
    """
    @pytest.fixture(autouse=True)
    def reset_config():
        ConfigStore.reset_instance()
        reset_config_provider()
        yield
        ConfigStore.reset_instance()
        reset_config_provider()
    
    @pytest.fixture
    def test_config():
        return Config(data={
            "options": {"id_base": "https://test.example.com/"},
            "database": {"host": "test-db"}
        })
    
    @pytest.fixture 
    def test_provider(test_config):
        return TestConfigProvider(test_config)
    
    def test_something(test_provider):
        original = set_config_provider(test_provider)
        try:
            # Your test code here
            config_val = ConfigValue("database:host")
            assert config_val.resolve() == "test-db"
        finally:
            set_config_provider(original)
    """
    print("See commented code above for pytest fixture patterns")


def migration_guide():
    """Guide for migrating from old to new system"""
    print("\n=== Migration Guide ===")
    print("OLD way (problematic in tests):")
    print("  ConfigValue('key').resolve()  # Used singleton directly")
    print()
    print("NEW way (works in tests):")
    print("  ConfigValue('key').resolve()  # Uses provider layer")
    print()
    print("For production: No changes needed!")
    print("For testing: Use TestConfigProvider instead of complex setup")
    print()
    print("Benefits:")
    print("- Cleaner test isolation")
    print("- No more import path issues") 
    print("- Easy configuration swapping")
    print("- Thread-safe singleton")
    print("- Backward compatible")


if __name__ == "__main__":
    # Reset everything first
    ConfigStore.reset_instance()
    reset_config_provider()
    
    # Run examples
    production_example()
    testing_example()
    context_manager_example()
    pytest_fixture_example()
    migration_guide()
    
    print("\n=== Summary ===")
    print("✅ Singleton pattern implemented")
    print("✅ Provider abstraction layer added") 
    print("✅ Clean testing support")
    print("✅ Backward compatibility maintained")
    print("✅ Thread-safe configuration management")