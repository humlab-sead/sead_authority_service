import pytest

from src.configuration import Config, ConfigProvider, ConfigStore, ConfigValue, MockConfigProvider, set_config_provider
from tests.decorators import with_test_config

# pylint: disable=unused-argument


class TestConfigProvider:
    """Test edge cases and error conditions"""

    @with_test_config
    def test_simple_test(self, test_provider: MockConfigProvider) -> None:
        """A simple test to ensure pytest is working"""
        value = ConfigValue("llm.max_tokens").resolve()
        assert value == 1000
        value = ConfigValue("llm.ollama.options.max_tokens").resolve()
        assert value == 9999
        value = ConfigValue("llm.max_tokens,llm.ollama.options.max_tokens").resolve()
        assert value == 1000
        value = ConfigValue("llm.ollama.options.max_tokens,llm.max_tokens").resolve()
        assert value == 9999
        value = ConfigValue("llm.dummy.options.max_tokens,llm.max_tokens").resolve()
        assert value == 1000

    @pytest.mark.asyncio
    @with_test_config
    async def test_config_value_resolution(self, test_provider: MockConfigProvider):
        """Test that ConfigValue works with the new provider system"""
        # Test ConfigValue resolution
        id_base_config = ConfigValue("options:id_base")

        # This will use the test_provider's configuration
        assert id_base_config.resolve() == "https://w3id.org/sead/id/"

    def test_config_provider_switching(self) -> None:
        """Test that we can switch between providers"""
        # Create two different configs
        config1 = Config(data={"test": {"value": "config1"}})
        config2 = Config(data={"test": {"value": "config2"}})

        provider1 = MockConfigProvider(config1)
        provider2 = MockConfigProvider(config2)

        # Test switching providers
        original: ConfigProvider = set_config_provider(provider1)

        try:
            config_value = ConfigValue("test:value")
            assert config_value.resolve() == "config1"

            # Switch to second provider
            set_config_provider(provider2)
            assert config_value.resolve() == "config2"

            # Switch back
            set_config_provider(provider1)
            assert config_value.resolve() == "config1"

        finally:
            set_config_provider(original)

    def test_singleton_persistence(self):
        """Test that singleton ConfigStore persists across calls"""
        # Configure the singleton
        config = Config(data={"test": "singleton_value"})
        store = ConfigStore.get_instance()
        store.store["default"] = config

        # Get another instance - should be the same
        store2 = ConfigStore.get_instance()
        assert store is store2
        assert store2.config().get("test") == "singleton_value"

        # Reset and verify it's clean
        ConfigStore.reset_instance()
        store3 = ConfigStore.get_instance()
        assert store3 is not store
        assert store3.store["default"] is None
