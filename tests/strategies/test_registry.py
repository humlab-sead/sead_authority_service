"""Unit tests for StrategyRegistry"""

import pytest

from src.strategies.query import BaseRepository
from src.strategies.strategy import (
    ReconciliationStrategy,
    Strategies,
    StrategyRegistry,
    StrategySpecification,
)
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config


class TestStrategyRegistry:
    """Test suite for StrategyRegistry"""

    def setup_method(self):
        """Set up clean registry state before each test"""
        # Store original items
        self.original_items = Strategies.items.copy()
        
    def teardown_method(self):
        """Restore original registry state after each test"""
        # Clear test registrations and restore originals
        Strategies.items = self.original_items

    def test_registry_inheritance(self):
        """Test that StrategyRegistry inherits from Registry"""
        assert hasattr(StrategyRegistry, "items")
        assert isinstance(Strategies, StrategyRegistry)
        assert isinstance(Strategies.items, dict)

    def test_registry_class_attributes(self):
        """Test that StrategyRegistry has correct class attributes"""
        assert hasattr(StrategyRegistry, "items")
        assert hasattr(StrategyRegistry, "get")
        assert hasattr(StrategyRegistry, "register")
        assert hasattr(StrategyRegistry, "is_registered")
        assert hasattr(StrategyRegistry, "registered_class_hook")

    def test_register_strategy_basic(self):
        """Test registering a basic strategy class"""

        strategies = StrategyRegistry()
    
        @strategies.register(key="test_strategy")
        class TestStrategy(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "test_strategy",
                    "id_field": "test_id",
                    "label_field": "test_label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        assert strategies.is_registered("test_strategy")
        assert "test_strategy" in strategies.items
        assert strategies.items["test_strategy"] == TestStrategy

    def test_register_strategy_with_key_property(self):
        """Test that registered strategy has _registry_key attribute"""
        strategies = StrategyRegistry()
    
        @strategies.register(key="keyed_strategy")
        class KeyedStrategy(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "keyed_strategy",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        assert hasattr(KeyedStrategy, "_registry_key")
        assert KeyedStrategy._registry_key == "keyed_strategy"

    def test_register_strategy_without_explicit_key(self):
        """Test registering strategy without explicit key uses class name"""
        strategies = StrategyRegistry()
        @strategies.register()
        class AutoNamedStrategy(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "AutoNamedStrategy",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        assert strategies.is_registered("AutoNamedStrategy")
        assert "AutoNamedStrategy" in strategies.items

    def test_get_registered_strategy(self):
        """Test retrieving a registered strategy"""
        strategies = StrategyRegistry()
    
        @strategies.register(key="retrievable_strategy")
        class RetrievableStrategy(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "retrievable_strategy",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        retrieved = strategies.get("retrievable_strategy")
        assert retrieved == RetrievableStrategy

    def test_get_unregistered_strategy_raises(self):
        """Test that getting unregistered strategy raises KeyError"""
        with pytest.raises(KeyError) as exc_info:
            Strategies.get("nonexistent_strategy")
        
        assert "nonexistent_strategy" in str(exc_info.value)

    def test_is_registered_true(self):
        """Test is_registered returns True for registered strategy"""
        strategies = StrategyRegistry()

        @strategies.register(key="registered_check")
        class RegisteredCheck(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "registered_check",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        assert strategies.is_registered("registered_check") is True

    def test_is_registered_false(self):
        """Test is_registered returns False for unregistered strategy"""
        assert Strategies.is_registered("definitely_not_registered") is False

    def test_registered_class_hook_basic(self):
        """Test that registered_class_hook is called during registration"""
        
        # Create a custom registry to test the hook
        class TestRegistry(StrategyRegistry):
            hook_called = False
            hook_args = None
            
            @classmethod
            def registered_class_hook(cls, fn_or_class, **args):
                cls.hook_called = True
                cls.hook_args = args
                return super().registered_class_hook(fn_or_class, **args)
        
        test_registry = TestRegistry()
        
        @test_registry.register(key="hook_test", custom_arg="test_value")
        class HookTest(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "hook_test",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)
        
        assert TestRegistry.hook_called is True
        assert TestRegistry.hook_args is not None
        assert "custom_arg" in TestRegistry.hook_args
        assert TestRegistry.hook_args["custom_arg"] == "test_value"

    def test_register_with_repository_cls(self):
        """Test registration with repository_cls argument"""

        class CustomRepository(BaseRepository):
            """Custom repository for testing"""
            pass

        @Strategies.register(key="custom_repo_strategy", repository_cls=CustomRepository)
        class CustomRepoStrategy(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "custom_repo_strategy",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec)

        # Check that repository_cls is set
        assert hasattr(CustomRepoStrategy, "repository_cls")

    def test_multiple_registrations_same_key_overwrites(self):
        """Test that registering with same key overwrites previous registration"""

        @Strategies.register(key="duplicate_key")
        class FirstStrategy(ReconciliationStrategy):
            value = "first"
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "duplicate_key",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        @Strategies.register(key="duplicate_key")
        class SecondStrategy(ReconciliationStrategy):
            value = "second"
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "duplicate_key",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        retrieved = Strategies.get("duplicate_key")
        assert retrieved == SecondStrategy
        assert hasattr(retrieved, "value")
        # Type guard for mypy
        if hasattr(retrieved, "value"):
            assert retrieved.value == "second"  # type: ignore

    def test_registry_items_isolated(self):
        """Test that registry items are properly isolated"""
        strategies = StrategyRegistry()
        initial_count = len(strategies.items)

        @strategies.register(key="isolated_test")
        class IsolatedTest(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "isolated_test",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        assert len(strategies.items) == initial_count + 1
        assert "isolated_test" in strategies.items

    @with_test_config
    def test_registered_strategy_has_key_property(self, test_provider: ExtendedMockConfigProvider):
        """Test that registered strategy instances have key property"""
        strategies = StrategyRegistry()

        @strategies.register(key="property_test")
        class PropertyTest(ReconciliationStrategy):
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "property_test",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        instance = PropertyTest()
        assert hasattr(instance, "key")
        assert instance.key == "property_test"

    def test_register_function_type(self):
        """Test registering with type='function' (though not typical for strategies)"""
        
        class FunctionRegistry(StrategyRegistry):
            items = {}
        
        function_registry = FunctionRegistry()
        
        # Functions with type='function' are called during registration
        @function_registry.register(key="test_function", type="function")
        def test_function():
            return "function_result"
        
        # The function should be called and result stored
        assert function_registry.is_registered("test_function")
        assert function_registry.items["test_function"] == "function_result"

    def test_registry_hook_preserves_class(self):
        """Test that registered_class_hook preserves the original class"""
        strategies = StrategyRegistry()
    
        @strategies.register(key="preserved_class")
        class PreservedClass(ReconciliationStrategy):
            custom_attr = "preserved"
            
            def __init__(self, specification=None):
                spec = specification or {
                    "key": "preserved_class",
                    "id_field": "id",
                    "label_field": "label",
                    "properties": [],
                    "property_settings": {},
                    "sql_queries": {},
                }
                super().__init__(spec, BaseRepository)

        retrieved = strategies.get("preserved_class")
        assert hasattr(retrieved, "custom_attr")
        if hasattr(retrieved, "custom_attr"):
            assert retrieved.custom_attr == "preserved"  # type: ignore

    @with_test_config
    def test_specification_passed_to_strategy(self, test_provider: ExtendedMockConfigProvider):
        """Test that specification from registry is used by strategy"""
        strategies = StrategyRegistry()

        test_spec: StrategySpecification = {
            "key": "spec_test",
            "id_field": "custom_id",
            "label_field": "custom_label",
            "properties": [{"id": "prop1", "name": "Property 1"}],
            "property_settings": {"prop1": {"type": "text"}},
            "sql_queries": {"test": "SELECT * FROM test"},
        }

        @strategies.register(key="spec_test")
        class SpecTest(ReconciliationStrategy):
            def __init__(self, specification=None):
                super().__init__(specification or test_spec, BaseRepository)

        instance = SpecTest()
        assert instance.specification["key"] == "spec_test"
        assert instance.specification["id_field"] == "custom_id"
        assert instance.specification["label_field"] == "custom_label"
