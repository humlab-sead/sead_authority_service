import os
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from src.configuration import Config, ConfigFactory, ConfigProvider, ConfigStore, ConfigValue, MockConfigProvider, set_config_provider
from src.configuration.utility import replace_references
from src.utility import replace_env_vars
from tests.decorators import with_test_config

# pylint: disable=unused-argument


class TestConfigProvider:
    """Test edge cases and error conditions"""

    @with_test_config
    def test_simple_test(self, test_provider: MockConfigProvider) -> None:
        """A simple test to ensure pytest is working"""
        value = ConfigValue("llm.options.max_tokens").resolve()
        assert value == 10000
        value = ConfigValue("llm.ollama.options.max_tokens").resolve()
        assert value is None
        value = ConfigValue("llm.num_predict,llm.ollama.options.num_predict").resolve()
        assert value == 4096
        value = ConfigValue("llm.ollama.options.num_predict,llm.num_predict").resolve()
        assert value == 4096
        value = ConfigValue("llm.dummy.options.num_predict,llm.num_predict").resolve()
        assert value is None

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
        store: ConfigStore = ConfigStore.get_instance()
        store.store["default"] = config

        # Get another instance - should be the same
        store2: ConfigStore = ConfigStore.get_instance()
        assert store is store2
        assert store2 is not None
        assert store2.config().get("test") == "singleton_value"  # type: ignore

        # Reset and verify it's clean
        ConfigStore.reset_instance()
        store3 = ConfigStore.get_instance()
        assert store3 is not store
        assert store3.store["default"] is None


class TestConfigFactorySubConfigs:
    """Test sub-config loading feature using @include: notation"""

    def test_simple_sub_config_loading(self, tmp_path: Path):
        """Test loading a simple sub-config referenced with @include: notation"""
        # Create sub-config file
        sub_config = tmp_path / "sub_config.yml"
        sub_config.write_text(
            """
database:
  host: localhost
  port: 5432
  name: testdb
"""
        )

        # Create main config that references sub-config
        main_config = tmp_path / "main_config.yml"
        main_config.write_text(
            f"""
app_name: "Test Application"
db_config: "@include:{sub_config}"
"""
        )

        # Load main config
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        # Verify main config values
        assert config.get("app_name") == "Test Application"

        # Verify sub-config was loaded and merged
        assert config.get("db_config:database:host") == "localhost"
        assert config.get("db_config:database:port") == 5432
        assert config.get("db_config:database:name") == "testdb"

    def test_relative_path_sub_config(self, tmp_path: Path):
        """Test loading sub-config with relative path"""
        # Create directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Create sub-config in same directory
        sub_config = config_dir / "database.yml"
        sub_config.write_text(
            """
connection:
  host: db.example.com
  port: 5433
"""
        )

        # Create main config with relative reference
        main_config = config_dir / "main.yml"
        main_config.write_text(
            """
app:
  name: "My App"
  database: "@include:database.yml"
"""
        )

        # Load main config
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        # Verify values
        assert config.get("app:name") == "My App"
        assert config.get("app:database:connection:host") == "db.example.com"
        assert config.get("app:database:connection:port") == 5433

    def test_nested_sub_configs(self, tmp_path: Path):
        """Test loading nested sub-configs (sub-config references another sub-config)"""
        # Create innermost config
        credentials_config = tmp_path / "credentials.yml"
        credentials_config.write_text(
            """
username: admin
password: secret123
"""
        )

        # Create middle config that references credentials
        db_config = tmp_path / "database.yml"
        db_config.write_text(
            f"""
host: localhost
port: 5432
credentials: "@include:{credentials_config}"
"""
        )

        # Create main config that references database
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
application: "Test App"
database: "@include:{db_config}"
"""
        )

        # Load main config
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        # Verify all levels loaded correctly
        assert config.get("application") == "Test App"
        assert config.get("database:host") == "localhost"
        assert config.get("database:port") == 5432
        assert config.get("database:credentials:username") == "admin"
        assert config.get("database:credentials:password") == "secret123"

    def test_multiple_sub_configs(self, tmp_path: Path):
        """Test loading multiple sub-configs in the same main config"""
        # Create multiple sub-configs
        db_config = tmp_path / "database.yml"
        db_config.write_text(
            """
host: localhost
port: 5432
"""
        )

        api_config = tmp_path / "api.yml"
        api_config.write_text(
            """
base_url: "https://api.example.com"
timeout: 30
"""
        )

        logging_config = tmp_path / "logging.yml"
        logging_config.write_text(
            """
level: DEBUG
format: "%(asctime)s - %(message)s"
"""
        )

        # Create main config referencing all three
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
app_name: "Multi-Config App"
database: "@include:{db_config}"
api: "@include:{api_config}"
logging: "@include:{logging_config}"
"""
        )

        # Load main config
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        # Verify all sub-configs loaded
        assert config.get("app_name") == "Multi-Config App"
        assert config.get("database:host") == "localhost"
        assert config.get("api:base_url") == "https://api.example.com"
        assert config.get("logging:level") == "DEBUG"

    def test_sub_config_with_list(self, tmp_path: Path):
        """Test sub-config containing lists"""
        # Create sub-config with list
        servers_config = tmp_path / "servers.yml"
        servers_config.write_text(
            """
servers:
  - name: server1
    host: 192.168.1.1
    port: 8080
  - name: server2
    host: 192.168.1.2
    port: 8081
"""
        )

        # Create main config
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
environment: production
backend: "@include:{servers_config}"
"""
        )

        # Load and verify
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        assert config.get("environment") == "production"
        servers = config.get("backend:servers")
        assert len(servers) == 2
        assert servers[0]["name"] == "server1"
        assert servers[1]["host"] == "192.168.1.2"

    def test_sub_config_within_list(self, tmp_path: Path):
        """Test sub-config reference within a list"""
        # Create sub-config
        prod_db = tmp_path / "prod_db.yml"
        prod_db.write_text(
            """
host: prod.example.com
port: 5432
replicas: 3
"""
        )

        # Create main config with sub-config reference in list
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
databases:
  - name: development
    host: localhost
    port: 5432
  - "@include:{prod_db}"
"""
        )

        # Load and verify
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        databases = config.get("databases")
        assert len(databases) == 2
        assert databases[0]["name"] == "development"
        assert databases[1]["host"] == "prod.example.com"
        assert databases[1]["replicas"] == 3

    def test_sub_config_not_found(self, tmp_path: Path):
        """Test error handling when sub-config file doesn't exist"""
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            """
app: test
database: "@include:nonexistent.yml"
"""
        )

        factory = ConfigFactory()
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            factory.load(source=str(main_config))

    def test_sub_config_with_environment_variables(self, tmp_path: Path, monkeypatch):
        """Test sub-config with environment variable substitution"""
        # Set environment variable
        monkeypatch.setenv("DB_HOST", "env-db-host.example.com")
        monkeypatch.setenv("DB_PORT", "5433")

        # Create sub-config with env vars
        db_config = tmp_path / "database.yml"
        db_config.write_text(
            """
host: "${DB_HOST}"
port: ${DB_PORT}
"""
        )

        # Create main config
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
app: test
database: "@include:{db_config}"
"""
        )

        # Load and verify env vars were replaced
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        assert config.get("database:host") == "env-db-host.example.com"
        assert config.get("database:port") == "5433"

    def test_sub_config_with_yaml_constructors(self, tmp_path: Path):
        """Test sub-config with custom YAML constructors like !join and !path_join"""
        # Create sub-config using constructors
        paths_config = tmp_path / "paths.yml"
        paths_config.write_text(
            """
base_dir: /var/app
log_file: !path_join [/var/app, logs, app.log]
message: !join ["Hello", " ", "World"]
"""
        )

        # Create main config
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
app: test
paths: "@include:{paths_config}"
"""
        )

        # Load and verify
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        assert config.get("paths:base_dir") == "/var/app"
        # Note: path_join behavior depends on OS
        assert "logs" in config.get("paths:log_file")
        assert config.get("paths:message") == "Hello World"

    def test_sub_config_absolute_path(self, tmp_path: Path):
        """Test loading sub-config with absolute path"""
        # Create sub-config
        sub_config = tmp_path / "absolute_sub.yml"
        sub_config.write_text(
            """
setting: "absolute path test"
value: 42
"""
        )

        # Create main config with absolute path reference
        main_config = tmp_path / "main.yml"
        absolute_path = str(sub_config.absolute())
        main_config.write_text(
            f"""
app: test
config: "@include:{absolute_path}"
"""
        )

        # Load and verify
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        assert config.get("config:setting") == "absolute path test"
        assert config.get("config:value") == 42

    def test_sub_config_override_behavior(self, tmp_path: Path):
        """Test that sub-config completely replaces the key value"""
        # Create sub-config
        sub_config = tmp_path / "override.yml"
        sub_config.write_text(
            """
new_key: "from sub-config"
another: 123
"""
        )

        # Create main config
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
target:
  old_key: "will be replaced"
  target: "@include:{sub_config}"
"""
        )

        # Load and verify
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        # The sub-config should completely replace the value
        assert config.get("target:target:new_key") == "from sub-config"
        assert config.get("target:target:another") == 123

    def test_sub_config_empty_file(self, tmp_path: Path):
        """Test loading an empty sub-config file"""
        # Create empty sub-config
        sub_config = tmp_path / "empty.yml"
        sub_config.write_text("")

        # Create main config
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
app: test
empty_config: "@include:{sub_config}"
"""
        )

        # Load and verify
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        assert config.get("app") == "test"
        # Empty YAML file loads as empty dict
        assert config.get("empty_config") == {}

    def test_sub_config_circular_reference_protection(self, tmp_path: Path):
        """Test that circular references are handled (Python recursion limit will catch this)"""
        # Create two configs that reference each other
        config_a = tmp_path / "config_a.yml"
        config_b = tmp_path / "config_b.yml"

        config_a.write_text(
            f"""
name: config_a
ref: "@include:{config_b}"
"""
        )

        config_b.write_text(
            f"""
name: config_b
ref: "@include:{config_a}"
"""
        )

        # This should raise a RecursionError
        factory = ConfigFactory()
        with pytest.raises(RecursionError):
            factory.load(source=str(config_a))

    def test_sub_config_with_env_prefix(self, tmp_path: Path, monkeypatch):
        """Test sub-config loading with env_prefix parameter"""
        # Set environment variables with prefix
        monkeypatch.setenv("MYAPP_CONFIG_DATABASE_HOST", "prefix-host.example.com")

        # Create sub-config
        db_config = tmp_path / "database.yml"
        db_config.write_text(
            """
database:
  host: default-host
  port: 5432
"""
        )

        # Create main config
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
app: test
config: "@include:{db_config}"
"""
        )

        # Load with env_prefix
        factory = ConfigFactory()
        config = factory.load(source=str(main_config), env_prefix="MYAPP")

        # Env variable should override the sub-config value
        assert config.get("config:database:host") == "prefix-host.example.com"
        assert config.get("config:database:port") == 5432

    def test_sub_config_preserves_structure(self, tmp_path: Path):
        """Test that complex nested structure in sub-config is preserved"""
        # Create complex sub-config
        complex_config = tmp_path / "complex.yml"
        complex_config.write_text(
            """
level1:
  level2:
    level3:
      level4:
        deep_value: "found me!"
      items:
        - item1
        - item2
  siblings:
    - name: first
      value: 1
    - name: second
      value: 2
"""
        )

        # Create main config
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
data: "@include:{complex_config}"
"""
        )

        # Load and verify structure
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        assert config.get("data:level1:level2:level3:level4:deep_value") == "found me!"
        assert len(config.get("data:level1:level2:level3:items")) == 2
        assert config.get("data:level1:siblings")[1]["name"] == "second"

    def test_sub_config_mixed_with_regular_values(self, tmp_path: Path):
        """Test that sub-configs can be mixed with regular configuration values"""
        # Create sub-config
        db_config = tmp_path / "database.yml"
        db_config.write_text(
            """
connection_string: "postgresql://localhost:5432/mydb"
pool_size: 10
"""
        )

        # Create main config with both sub-config and regular values
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
app_name: "MyApp"
version: "1.0.0"
database: "@include:{db_config}"
features:
  auth: true
  cache: false
"""
        )

        # Load and verify
        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        assert config.get("app_name") == "MyApp"
        assert config.get("version") == "1.0.0"
        assert config.get("database:connection_string") == "postgresql://localhost:5432/mydb"
        assert config.get("database:pool_size") == 10
        assert config.get("features:auth") is True

    def test_sub_config_without_at_include_prefix(self, tmp_path: Path):
        """Test that strings not starting with @include: are treated as regular values"""
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            """
app: test
database: "some/path/that/looks/like/file.yml"
message: "@value:something"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        # These should be treated as regular string values, not file references
        assert config.get("database") == "some/path/that/looks/like/file.yml"
        # Note: "@value:something" will be treated as a reference by replace_references
        # Since "something" doesn't exist in the config, it will remain as the original string
        assert config.get("message") == "@value:something"


class TestConfigFactoryReferences:
    """Test internal reference replacement feature using @value: notation"""

    def test_simple_internal_reference(self, tmp_path: Path):
        """Test simple internal reference replacement."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
base_url: "https://api.example.com"
api_endpoint: "@value:base_url"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("base_url") == "https://api.example.com"
        assert config.get("api_endpoint") == "https://api.example.com"

    def test_nested_path_reference(self, tmp_path: Path):
        """Test reference to nested configuration path."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
database:
  primary:
    host: db.example.com
    port: 5432
  replica:
    host: replica.example.com
    port: 5433
    
connection:
  primary_host: "@value:database.primary.host"
  primary_port: "@value:database.primary.port"
  replica_host: "@value:database.replica.host"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("connection:primary_host") == "db.example.com"
        assert config.get("connection:primary_port") == 5432
        assert config.get("connection:replica_host") == "replica.example.com"

    def test_reference_with_colon_notation(self, tmp_path: Path):
        """Test reference using colon notation in path."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
app:
  settings:
    timeout: 30
    retries: 3
    
timeout_value: "@value:app:settings:timeout"
retry_count: "@value:app:settings:retries"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("timeout_value") == 30
        assert config.get("retry_count") == 3

    def test_reference_to_entire_dict(self, tmp_path: Path):
        """Test reference pointing to entire dictionary."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
defaults:
  timeout: 30
  retries: 3
  cache: true
  
service_a:
  config: "@value:defaults"
  
service_b:
  config: "@value:defaults"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("service_a:config:timeout") == 30
        assert config.get("service_a:config:retries") == 3
        assert config.get("service_b:config:cache") is True

    def test_reference_to_list(self, tmp_path: Path):
        """Test reference pointing to list."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
allowed_hosts:
  - localhost
  - example.com
  - api.example.com
  
cors_origins: "@value:allowed_hosts"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        allowed = config.get("allowed_hosts")
        cors = config.get("cors_origins")
        assert cors == allowed
        assert cors == ["localhost", "example.com", "api.example.com"]

    def test_references_in_list(self, tmp_path: Path):
        """Test references within a list."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
primary_db: "db1.example.com"
backup_db: "db2.example.com"

database_hosts:
  - "@value:primary_db"
  - "@value:backup_db"
  - "static.example.com"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        hosts = config.get("database_hosts")
        assert hosts == ["db1.example.com", "db2.example.com", "static.example.com"]

    def test_recursive_reference_resolution(self, tmp_path: Path):
        """Test that references pointing to other references are resolved."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
base_value: "final_value"
level1: "@value:base_value"
level2: "@value:level1"
level3: "@value:level2"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("base_value") == "final_value"
        assert config.get("level1") == "final_value"
        assert config.get("level2") == "final_value"
        assert config.get("level3") == "final_value"

    def test_missing_reference_path(self, tmp_path: Path):
        """Test that missing reference paths remain as original strings."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
value: "test"
missing_ref: "@value:nonexistent.path"
another_ref: "@value:value"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("value") == "test"
        assert config.get("missing_ref") == "@value:nonexistent.path"
        assert config.get("another_ref") == "test"

    def test_reference_with_environment_variables(self, tmp_path: Path, monkeypatch):
        """Test that references work after environment variable replacement."""
        monkeypatch.setenv("DB_HOST", "env-db.example.com")
        monkeypatch.setenv("DB_PORT", "5432")

        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
database:
  host: "${DB_HOST}"
  port: ${DB_PORT}
  
connection_string: "@value:database.host"
connection_port: "@value:database.port"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        # Env vars should be replaced first, then references resolved
        assert config.get("database:host") == "env-db.example.com"
        assert config.get("database:port") == "5432"
        assert config.get("connection_string") == "env-db.example.com"
        assert config.get("connection_port") == "5432"

    def test_references_with_sub_configs(self, tmp_path: Path):
        """Test that references work with @include: sub-config loading."""
        # Create sub-config
        db_config = tmp_path / "database.yml"
        db_config.write_text(
            """
host: localhost
port: 5432
name: mydb
"""
        )

        # Create main config with both @include: and @value: references
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
database: "@include:{db_config}"
app:
  db_host: "@value:database.host"
  db_name: "@value:database.name"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        # Sub-config should load first, then references resolve
        assert config.get("database:host") == "localhost"
        assert config.get("app:db_host") == "localhost"
        assert config.get("app:db_name") == "mydb"

    def test_complex_nested_references(self, tmp_path: Path):
        """Test complex nested structure with multiple references."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
defaults:
  timeout: 30
  retries: 3
  
services:
  api:
    name: "API Service"
    settings: "@value:defaults"
  worker:
    name: "Worker Service"
    settings: "@value:defaults"
    
monitoring:
  # Direct references to values that exist in the original structure
  default_timeout: "@value:defaults.timeout"
  api_name: "@value:services.api.name"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        # Services should have their settings resolved from defaults
        assert config.get("services:api:settings:timeout") == 30
        assert config.get("services:worker:settings:retries") == 3
        # Monitoring should reference values that exist in original structure
        assert config.get("monitoring:default_timeout") == 30
        assert config.get("monitoring:api_name") == "API Service"

    def test_reference_with_underscore_fallback(self, tmp_path: Path):
        """Test that references support underscore notation fallback."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
app_config_value: 42
reference: "@value:app:config:value"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("app_config_value") == 42
        assert config.get("reference") == 42

    def test_reference_does_not_affect_yaml_constructors(self, tmp_path: Path):
        """Test that references work alongside YAML constructors."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
base_dir: /var/app
log_path: !path_join [/var/app, logs, app.log]
message: !join ["Hello", " ", "World"]

app:
  directory: "@value:base_dir"
  greeting: "@value:message"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("base_dir") == "/var/app"
        assert config.get("message") == "Hello World"
        assert config.get("app:directory") == "/var/app"
        assert config.get("app:greeting") == "Hello World"

    def test_mixed_references_and_regular_values(self, tmp_path: Path):
        """Test that references can be mixed with regular configuration values."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
base_url: "https://api.example.com"
version: "v1"

endpoints:
  users: "@value:base_url"
  posts: "@value:base_url"
  static_endpoint: "https://static.example.com"
  version: "@value:version"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("endpoints:users") == "https://api.example.com"
        assert config.get("endpoints:posts") == "https://api.example.com"
        assert config.get("endpoints:static_endpoint") == "https://static.example.com"
        assert config.get("endpoints:version") == "v1"

    def test_reference_order_independence(self, tmp_path: Path):
        """Test that references work regardless of definition order."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
# Reference defined before the target
early_ref: "@value:late_value"

# Other config
app_name: "Test App"

# Target defined after the reference
late_value: "this was defined later"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("late_value") == "this was defined later"
        assert config.get("early_ref") == "this was defined later"


# Integration tests
class TestReplaceReferences:
    """Tests for replace_references and _replace_references functions."""

    def test_replace_references_simple_string_reference(self):
        """Test replace_references with simple string reference."""
        data = {"target": "value123", "ref": "@value:target"}
        result = replace_references(data)
        assert result == {"target": "value123", "ref": "value123"}

    def test_replace_references_nested_path_reference(self):
        """Test replace_references with nested dotpath reference."""
        data = {
            "config": {"database": {"host": "localhost", "port": 5432}},
            "db_host": "@value:config.database.host",
            "db_port": "@value:config.database.port",
        }
        result = replace_references(data)
        assert result == {"config": {"database": {"host": "localhost", "port": 5432}}, "db_host": "localhost", "db_port": 5432}

    def test_replace_references_colon_notation(self):
        """Test replace_references with colon notation in path."""
        data = {"app": {"settings": {"timeout": 30}}, "ref": "@value:app:settings:timeout"}
        result = replace_references(data)
        assert result == {"app": {"settings": {"timeout": 30}}, "ref": 30}

    def test_replace_references_missing_path(self):
        """Test replace_references with nonexistent path (returns original string)."""
        data = {"value": "test", "ref": "@value:nonexistent.path"}
        result = replace_references(data)
        assert result == {"value": "test", "ref": "@value:nonexistent.path"}

    def test_replace_references_non_reference_string(self):
        """Test replace_references leaves non-reference strings unchanged."""
        data = {"regular": "just a string", "not_ref": "something:include", "also_not": "includetest"}
        result = replace_references(data)
        assert result == {"regular": "just a string", "not_ref": "something:include", "also_not": "includetest"}

    def test_replace_references_dict_structure(self):
        """Test replace_references with nested dict structure."""
        data = {"base": {"value": "original"}, "nested": {"config": {"ref": "@value:base.value"}}}
        result = replace_references(data)
        assert result == {"base": {"value": "original"}, "nested": {"config": {"ref": "original"}}}

    def test_replace_references_list_structure(self):
        """Test replace_references with list containing references."""
        # Note: dotget doesn't support numeric indices, so list item references won't resolve
        data = {"values": ["a", "b", "c"], "whole_list": "@value:values", "refs": ["@value:whole_list", "static"]}
        result = replace_references(data)
        assert result == {"values": ["a", "b", "c"], "whole_list": ["a", "b", "c"], "refs": [["a", "b", "c"], "static"]}

    def test_replace_references_mixed_list_and_dict(self):
        """Test replace_references with mixed list and dict structures."""
        # dotget doesn't support numeric indices, so we reference the whole list instead
        data = {
            "primary_server": {"name": "server1", "host": "host1.com"},
            "servers": [{"name": "server1", "host": "host1.com"}, {"name": "server2", "host": "host2.com"}],
            "primary_host": "@value:primary_server.host",
        }
        result = replace_references(data)
        assert result == {
            "primary_server": {"name": "server1", "host": "host1.com"},
            "servers": [{"name": "server1", "host": "host1.com"}, {"name": "server2", "host": "host2.com"}],
            "primary_host": "host1.com",
        }

    def test_replace_references_recursive_resolution(self):
        """Test replace_references with reference pointing to another reference."""
        data = {"value": "final_value", "ref1": "@value:value", "ref2": "@value:ref1"}
        result = replace_references(data)
        # ref2 should resolve to ref1's value, which resolves to "final_value"
        assert result == {"value": "final_value", "ref1": "final_value", "ref2": "final_value"}

    def test_replace_references_reference_to_dict(self):
        """Test replace_references with reference pointing to dict."""
        data = {"settings": {"timeout": 30, "retries": 3}, "copied": "@value:settings"}
        result = replace_references(data)
        assert result == {"settings": {"timeout": 30, "retries": 3}, "copied": {"timeout": 30, "retries": 3}}

    def test_replace_references_reference_to_list(self):
        """Test replace_references with reference pointing to list."""
        data = {"items": [1, 2, 3], "copied_items": "@value:items"}
        result = replace_references(data)
        assert result == {"items": [1, 2, 3], "copied_items": [1, 2, 3]}

    def test_replace_references_multiple_refs_to_same_path(self):
        """Test replace_references with multiple references to same path."""
        data = {"source": "shared_value", "ref1": "@value:source", "ref2": "@value:source", "ref3": "@value:source"}
        result = replace_references(data)
        assert result == {"source": "shared_value", "ref1": "shared_value", "ref2": "shared_value", "ref3": "shared_value"}

    def test_replace_references_empty_structures(self):
        """Test replace_references with empty dict and list."""
        result = replace_references({})
        assert result == {}

        result = replace_references([])
        assert result == []

        data = {"empty_dict": {}, "empty_list": [], "ref_to_empty": "@value:empty_dict"}
        result = replace_references(data)
        assert result == {"empty_dict": {}, "empty_list": [], "ref_to_empty": {}}

    def test_replace_references_complex_nested_structure(self):
        """Test replace_references with complex nested structure."""
        data = {
            "database": {"primary": {"host": "db1.example.com", "port": 5432}, "replica": {"host": "db2.example.com", "port": 5433}},
            "app": {"db_config": {"main": "@value:database.primary", "backup": "@value:database.replica.host"}},
            "monitoring": {"targets": ["@value:database.primary.host", "@value:database.replica.host"]},
        }
        result = replace_references(data)
        expected = {
            "database": {"primary": {"host": "db1.example.com", "port": 5432}, "replica": {"host": "db2.example.com", "port": 5433}},
            "app": {"db_config": {"main": {"host": "db1.example.com", "port": 5432}, "backup": "db2.example.com"}},
            "monitoring": {"targets": ["db1.example.com", "db2.example.com"]},
        }
        assert result == expected

    def test_replace_references_deep_nesting(self):
        """Test replace_references with deeply nested path."""
        data = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}, "ref": "@value:level1.level2.level3.level4.value"}
        result = replace_references(data)
        assert result == {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}, "ref": "deep"}

    def test_replace_references_underscore_fallback(self):
        """Test replace_references with underscore notation fallback."""
        data = {"app_config_value": 42, "ref": "@value:app:config:value"}
        result = replace_references(data)
        assert result == {"app_config_value": 42, "ref": 42}

    def test_replace_references_mixed_data_types(self):
        """Test replace_references with various data types."""
        data = {
            "string": "text",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "none_value": None,
            "ref_string": "@value:string",
            "ref_number": "@value:number",
            "ref_float": "@value:float",
            "ref_boolean": "@value:boolean",
            "ref_none": "@value:none_value",
        }
        result = replace_references(data)
        expected = {
            "string": "text",
            "number": 123,
            "float": 45.67,
            "boolean": True,
            "none_value": None,
            "ref_string": "text",
            "ref_number": 123,
            "ref_float": 45.67,
            "ref_boolean": True,
            # Note: When the referenced value is None, dotget returns None as default,
            # and _replace_references returns the original string if ref_value is None
            "ref_none": "@value:none_value",
        }
        assert result == expected

    def test_replace_references_does_not_modify_original(self):
        """Test that replace_references doesn't modify the original data."""
        original_data = {"value": "original", "ref": "@value:value"}
        original_copy = {"value": "original", "ref": "@value:value"}

        result = replace_references(original_data)

        # Original data should be unchanged
        assert original_data == original_copy

        # Result should have replacements
        assert result == {"value": "original", "ref": "original"}


class TestListOperations:
    """Tests for list operations with include directives."""

    def test_simple_include_still_works(self):
        """Test that simple include directive still works as before."""
        data = {"source": ["a", "b", "c"], "target": "@value: source"}

        result = replace_references(data)

        assert result["target"] == ["a", "b", "c"]  # type: ignore[call-arg]

    def test_prepend_items_to_included_list(self):
        """Test prepending items to an included list."""
        data = {"source": ["b", "c"], "target": "['a'] + @value: source"}

        result = replace_references(data)

        assert result["target"] == ["a", "b", "c"]  # type: ignore[call-arg]

    def test_append_items_to_included_list(self):
        """Test appending items to an included list."""
        data = {"source": ["a", "b"], "target": "@value: source + ['c']"}

        result = replace_references(data)

        assert result["target"] == ["a", "b", "c"]  # type: ignore[call-arg]

    def test_prepend_and_append(self):
        """Test prepending and appending items to an included list."""
        data = {"source": ["b", "c"], "target": "['a'] + @value: source + ['d']"}

        result = replace_references(data)

        assert result["target"] == ["a", "b", "c", "d"]  # type: ignore[call-arg]

    def test_multiple_includes(self):
        """Test concatenating multiple included lists."""
        data = {"list1": ["a", "b"], "list2": ["c", "d"], "target": "@value: list1 + @value: list2"}

        result = replace_references(data)

        assert result["target"] == ["a", "b", "c", "d"]  # type: ignore[call-arg]

    def test_multiple_includes_with_literals(self):
        """Test complex expression with multiple includes and literals."""
        data = {"list1": ["b"], "list2": ["d"], "target": "['a'] + @value: list1 + ['c'] + @value: list2 + ['e']"}

        result = replace_references(data)

        assert result["target"] == ["a", "b", "c", "d", "e"]  # type: ignore[call-arg]

    def test_nested_path_reference(self):
        """Test include with nested path."""
        data = {"entities": {"sample": {"columns": ["col1", "col2", "col3"]}}, "target": "@value: entities.sample.columns"}

        result = replace_references(data)

        assert result["target"] == ["col1", "col2", "col3"]  # type: ignore[call-arg]

    def test_nested_path_with_operations(self):
        """Test list operations with nested path references."""
        data = {"entities": {"sample": {"columns": ["col2", "col3"]}}, "target": "['col1'] + @value: entities.sample.columns"}

        result = replace_references(data)

        assert result["target"] == ["col1", "col2", "col3"]  # type: ignore[call-arg]

    def test_list_with_strings(self):
        """Test list operations with string values."""
        data = {"source": ["value1", "value2"], "target": "['prefix'] + @value: source + ['suffix']"}

        result = replace_references(data)

        assert result["target"] == ["prefix", "value1", "value2", "suffix"]  # type: ignore[call-arg]

    def test_list_with_numbers(self):
        """Test list operations with numeric values."""
        data = {"source": [2, 3], "target": "[1] + @value: source + [4]"}

        result = replace_references(data)

        assert result["target"] == [1, 2, 3, 4]  # type: ignore[call-arg]

    def test_multiple_list_literals(self):
        """Test multiple list literals without include."""
        data = {"target": "['a', 'b'] + ['c', 'd']"}

        result = replace_references(data)

        assert result["target"] == ["a", "b", "c", "d"]  # type: ignore[call-arg]

    def test_empty_list_operations(self):
        """Test operations with empty lists."""
        data = {"source": [], "target": "['a'] + @value: source + ['b']"}

        result = replace_references(data)

        assert result["target"] == ["a", "b"]  # type: ignore[call-arg]

    def test_whitespace_handling(self):
        """Test that whitespace in expressions is handled correctly."""
        data = {"source": ["b"], "target": "  ['a']   +   @value: source   +   ['c']  "}

        result = replace_references(data)

        assert result["target"] == ["a", "b", "c"]  # type: ignore[call-arg]

    def test_recursive_includes(self):
        """Test that included lists can themselves contain include directives."""
        data = {"base": ["a", "b"], "extended": "@value: base", "target": "['x'] + @value: extended + ['y']"}

        result = replace_references(data)

        assert result["target"] == ["x", "a", "b", "y"]  # type: ignore[call-arg]

    def test_nonexistent_path_in_operation(self):
        """Test handling of nonexistent paths in list operations."""
        data = {"target": "['a'] + @value: nonexistent.path + ['b']"}

        result = replace_references(data)

        # Should skip the nonexistent reference and concatenate what exists
        assert result["target"] == ["a", "b"]  # type: ignore[call-arg]

    def test_non_list_value_in_include(self):
        """Test including a non-list value in a list operation."""
        data = {"source": "single_value", "target": "['a'] + @value: source + ['b']"}

        result = replace_references(data)

        assert result["target"] == ["a", "single_value", "b"]  # type: ignore[call-arg]

    def test_nested_dict_values_unaffected(self):
        """Test that non-string values in dicts are not affected."""
        data = {"source": ["a", "b"], "nested": {"list": ["x", "y"], "ref": "@value: source"}}

        result = replace_references(data)

        assert result["nested"]["list"] == ["x", "y"]  # type: ignore[call-arg]
        assert result["nested"]["ref"] == ["a", "b"]  # type: ignore[call-arg]

    def test_list_within_list_not_processed(self):
        """Test that list items themselves aren't treated as expressions."""
        data = {"source": ["a", "b"], "target": ["@value: source", "literal_string"]}  # This should be replaced

        result = replace_references(data)

        assert result["target"][0] == ["a", "b"]  # type: ignore[call-arg]
        assert result["target"][1] == "literal_string"  # type: ignore[call-arg]

    def test_complex_nested_structure(self):
        """Test complex nested configuration structure."""
        data = {
            "entities": {
                "location": {"keys": ["Ort", "Kreis", "Land"]},
                "site": {"keys": ["ProjektNr", "Fustel"], "columns": "@value: entities.site.keys"},
                "site_location": {"keys": [], "columns": "['extra_col'] + @value: entities.site.columns + @value: entities.location.keys"},
            }
        }

        result = replace_references(data)

        # site.columns should resolve to site.keys
        assert result["entities"]["site"]["columns"] == ["ProjektNr", "Fustel"]  # type: ignore[call-arg]

        # site_location.columns should concatenate all parts
        assert result["entities"]["site_location"]["columns"] == ["extra_col", "ProjektNr", "Fustel", "Ort", "Kreis", "Land"]  # type: ignore[call-arg]

    def test_real_world_example(self):
        """Test a real-world configuration scenario."""
        data = {
            "entities": {
                "sample": {
                    "surrogate_id": "sample_id",
                    "keys": ["ProjektNr", "Befu", "ProbNr"],
                    "columns": ["ProjektNr", "Befu", "ProbNr", "EDatProb", "Strat"],
                },
                "sample_taxa": {"keys": [], "columns": "['PCODE', 'RTyp'] + @value: entities.sample.keys + ['Anmerkung']"},
            }
        }

        result = replace_references(data)

        assert result["entities"]["sample_taxa"]["columns"] == ["PCODE", "RTyp", "ProjektNr", "Befu", "ProbNr", "Anmerkung"]  # type: ignore[call-arg]


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_malformed_list_literal(self):
        """Test handling of malformed list literal."""
        data = {"target": "['a', 'b' + @value: source"}  # Missing closing bracket

        # Should not crash, return original or best effort
        result = replace_references(data)
        assert result["target"] is not None  # type: ignore[call-arg]

    def test_empty_include_path(self):
        """Test handling of empty include path."""
        data = {"target": "@value: "}

        result = replace_references(data)
        # Should return original string if path is empty/invalid
        assert result["target"] == "@value: "  # type: ignore[call-arg]

    def test_only_plus_operators(self):
        """Test string with plus operators but no lists or includes."""
        data = {"target": "a + b + c"}

        result = replace_references(data)

        # Should remain unchanged as it's not a valid list operation
        assert result["target"] == "a + b + c"  # type: ignore[call-arg]

    def test_plus_in_string_values(self):
        """Test that plus signs within list values don't break parsing."""
        data = {"source": ["value+with+plus"], "target": "@value: source"}

        result = replace_references(data)

        assert result["target"] == ["value+with+plus"]  # type: ignore[call-arg]


class TestRealWorldIntegration:
    """Tests using real-world configuration patterns."""

    def test_arbodat_config_pattern(self):
        """Test the actual pattern from arbodat config.yml."""
        config = {
            "entities": {
                "location": {"surrogate_id": "location_id", "keys": ["Ort", "Kreis", "Land", "Staat", "FlurStr"], "columns": "@value: entities.location.keys"},
                "site": {
                    "surrogate_id": "site_id",
                    "keys": ["ProjektNr", "Fustel", "EVNr"],
                    "columns": [
                        "ProjektNr",
                        "Fustel",
                        "EVNr",
                        "FustelTyp?",
                        "okFustel",
                        "Limes",
                    ],
                },
                "site_location": {"keys": [], "columns": "@value: entities.site.columns + @value: entities.location.keys"},
            }
        }

        result = replace_references(config)

        # location.columns should resolve to its keys
        assert result["entities"]["location"]["columns"] == ["Ort", "Kreis", "Land", "Staat", "FlurStr"]  # type: ignore[call-arg]

        # site_location.columns should concatenate site columns + location keys
        expected = [
            "ProjektNr",
            "Fustel",
            "EVNr",
            "FustelTyp?",
            "okFustel",
            "Limes",  # site.columns
            "Ort",
            "Kreis",
            "Land",
            "Staat",
            "FlurStr",  # location.keys
        ]
        assert result["entities"]["site_location"]["columns"] == expected  # type: ignore[call-arg]

    def test_foreign_key_pattern(self):
        """Test foreign key configuration with include directives."""
        config = {
            "entities": {
                "sample": {
                    "surrogate_id": "sample_id",
                    "keys": ["ProjektNr", "Befu", "ProbNr"],
                    "columns": ["ProjektNr", "Befu", "ProbNr", "EDatProb", "Strat"],
                },
                "taxa": {"surrogate_id": "taxon_id", "keys": ["BNam", "TaxAut"], "columns": ["BNam", "TaxAut", "Familie"]},
                "sample_taxa": {
                    "keys": [],
                    "columns": "@value: entities.sample.keys + @value: entities.taxa.keys + ['SumFAnzahl', 'SumFGewicht']",
                    "foreign_keys": [
                        {"entity": "sample", "local_keys": "@value: entities.sample.keys", "remote_keys": "@value: entities.sample.keys"},
                        {"entity": "taxa", "local_keys": "@value: entities.taxa.keys", "remote_keys": "@value: entities.taxa.keys"},
                    ],
                },
            }
        }

        result = replace_references(config)

        # Check columns concatenation
        expected_columns = ["ProjektNr", "Befu", "ProbNr", "BNam", "TaxAut", "SumFAnzahl", "SumFGewicht"]  # sample.keys  # taxa.keys  # additional columns
        assert result["entities"]["sample_taxa"]["columns"] == expected_columns  # type: ignore[call-arg]

        # Check foreign key references
        assert result["entities"]["sample_taxa"]["foreign_keys"][0]["local_keys"] == ["ProjektNr", "Befu", "ProbNr"]  # type: ignore[call-arg]
        assert result["entities"]["sample_taxa"]["foreign_keys"][1]["local_keys"] == ["BNam", "TaxAut"]  # type: ignore[call-arg]

    def test_unnest_configuration_pattern(self):
        """Test unnest configuration with include directives."""
        config = {
            "entities": {
                "location": {
                    "surrogate_id": "location_id",
                    "keys": ["Ort", "Kreis", "Land"],
                    "unnest": {
                        "id_vars": "@value: entities.location.surrogate_id",
                        "value_vars": "@value: entities.location.keys",
                        "var_name": "location_type",
                        "value_name": "location_name",
                    },
                }
            }
        }

        result = replace_references(config)

        assert result["entities"]["location"]["unnest"]["id_vars"] == "location_id"  # type: ignore[call-arg]
        assert result["entities"]["location"]["unnest"]["value_vars"] == ["Ort", "Kreis", "Land"]  # type: ignore[call-arg]

    def test_prepend_surrogate_id_to_columns(self):
        """Test prepending surrogate_id to columns list."""
        config = {
            "entities": {
                "sample": {"surrogate_id": "sample_id", "keys": ["ProjektNr", "Befu", "ProbNr"], "all_columns": "['sample_id'] + @value: entities.sample.keys"}
            }
        }

        result = replace_references(config)

        assert result["entities"]["sample"]["all_columns"] == ["sample_id", "ProjektNr", "Befu", "ProbNr"]  # type: ignore[call-arg]

    def test_deeply_nested_references(self):
        """Test that references can chain through multiple levels."""
        config = {
            "base": {"common_fields": ["id", "created_at", "updated_at"]},
            "entities": {
                "sample": {
                    "keys": ["project_nr", "sample_nr"],
                    "base_columns": "@value: base.common_fields + @value: entities.sample.keys",
                    "extended_columns": "@value: entities.sample.base_columns + ['notes', 'status']",
                }
            },
        }

        result = replace_references(config)

        # base_columns should resolve first
        assert result["entities"]["sample"]["base_columns"] == [  # type: ignore[call-arg]
            "id",
            "created_at",
            "updated_at",  # from base.common_fields
            "project_nr",
            "sample_nr",  # from sample.keys
        ]

        # extended_columns should use the resolved base_columns
        assert result["entities"]["sample"]["extended_columns"] == [  # type: ignore[call-arg]
            "id",
            "created_at",
            "updated_at",
            "project_nr",
            "sample_nr",  # from base_columns
            "notes",
            "status",  # additional fields
        ]

    def test_complex_multi_entity_relationship(self):
        """Test complex configuration with multiple entity relationships."""
        config = {
            "entities": {
                "project": {"keys": ["ProjektNr"], "columns": "@value: entities.project.keys"},
                "site": {"keys": ["ProjektNr", "Fustel"], "columns": "@value: entities.site.keys + ['site_type']"},
                "feature": {"keys": ["ProjektNr", "Fustel", "Befu"], "columns": "@value: entities.feature.keys + ['feature_type']"},
                "sample": {"keys": "@value: entities.feature.keys + ['ProbNr']", "columns": "@value: entities.sample.keys + ['sample_date', 'depth']"},
            }
        }

        result = replace_references(config)

        # Check cascading keys
        assert result["entities"]["project"]["columns"] == ["ProjektNr"]  # type: ignore[call-arg]
        assert result["entities"]["site"]["columns"] == ["ProjektNr", "Fustel", "site_type"]  # type: ignore[call-arg]
        assert result["entities"]["feature"]["columns"] == ["ProjektNr", "Fustel", "Befu", "feature_type"]  # type: ignore[call-arg]
        assert result["entities"]["sample"]["keys"] == ["ProjektNr", "Fustel", "Befu", "ProbNr"]  # type: ignore[call-arg]
        assert result["entities"]["sample"]["columns"] == ["ProjektNr", "Fustel", "Befu", "ProbNr", "sample_date", "depth"]  # type: ignore[call-arg]

    def test_mixed_types_in_config(self):
        """Test that includes work alongside regular values."""
        config = {
            "defaults": {"system_columns": ["created_by", "modified_by"]},
            "entities": {
                "sample": {
                    "keys": ["id"],
                    "columns": "['name', 'type'] + @value: entities.sample.keys + @value: defaults.system_columns",
                    "static_value": "this is not processed",
                    "numeric_value": 42,
                    "bool_value": True,
                    "nested": {"also_processed": "@value: defaults.system_columns"},
                }
            },
        }

        result = replace_references(config)

        assert result["entities"]["sample"]["columns"] == ["name", "type", "id", "created_by", "modified_by"]  # type: ignore[call-arg]
        assert result["entities"]["sample"]["static_value"] == "this is not processed"  # type: ignore[call-arg]
        assert result["entities"]["sample"]["numeric_value"] == 42  # type: ignore[call-arg]
        assert result["entities"]["sample"]["bool_value"] is True  # type: ignore[call-arg]
        assert result["entities"]["sample"]["nested"]["also_processed"] == ["created_by", "modified_by"]  # type: ignore[call-arg]

    def test_replace_references_and_replace_env_vars_integration(self):
        """Test replace_references works after replace_env_vars."""
        with patch.dict(os.environ, {"DB_HOST": "env-host.example.com"}):
            # First replace env vars, then references
            data = {"env_value": "${DB_HOST}", "reference": "@value:env_value"}

            step1: dict[str, Any] | list[Any] | str = replace_env_vars(data)
            assert step1 == {"env_value": "env-host.example.com", "reference": "@value:env_value"}

            step2: dict[str, Any] | list[Any] | str = replace_references(step1)
            assert step2 == {"env_value": "env-host.example.com", "reference": "env-host.example.com"}
