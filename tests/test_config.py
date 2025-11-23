from pathlib import Path

import pytest

from src.configuration import Config, ConfigFactory, ConfigProvider, ConfigStore, ConfigValue, MockConfigProvider, set_config_provider
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
message: "include:something"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(main_config))

        # These should be treated as regular string values, not file references
        assert config.get("database") == "some/path/that/looks/like/file.yml"
        # Note: "include:something" will be treated as a reference by replace_references
        # Since "something" doesn't exist in the config, it will remain as the original string
        assert config.get("message") == "include:something"


class TestConfigFactoryReferences:
    """Test internal reference replacement feature using include: notation"""

    def test_simple_internal_reference(self, tmp_path: Path):
        """Test simple internal reference replacement."""
        config_file = tmp_path / "config.yml"
        config_file.write_text(
            """
base_url: "https://api.example.com"
api_endpoint: "include:base_url"
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
  primary_host: "include:database.primary.host"
  primary_port: "include:database.primary.port"
  replica_host: "include:database.replica.host"
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
    
timeout_value: "include:app:settings:timeout"
retry_count: "include:app:settings:retries"
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
  config: "include:defaults"
  
service_b:
  config: "include:defaults"
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
  
cors_origins: "include:allowed_hosts"
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
  - "include:primary_db"
  - "include:backup_db"
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
level1: "include:base_value"
level2: "include:level1"
level3: "include:level2"
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
missing_ref: "include:nonexistent.path"
another_ref: "include:value"
"""
        )

        factory = ConfigFactory()
        config = factory.load(source=str(config_file))

        assert config.get("value") == "test"
        assert config.get("missing_ref") == "include:nonexistent.path"
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
  
connection_string: "include:database.host"
connection_port: "include:database.port"
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

        # Create main config with both @include: and include: references
        main_config = tmp_path / "main.yml"
        main_config.write_text(
            f"""
database: "@include:{db_config}"
app:
  db_host: "include:database.host"
  db_name: "include:database.name"
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
    settings: "include:defaults"
  worker:
    name: "Worker Service"
    settings: "include:defaults"
    
monitoring:
  # Direct references to values that exist in the original structure
  default_timeout: "include:defaults.timeout"
  api_name: "include:services.api.name"
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
reference: "include:app:config:value"
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
  directory: "include:base_dir"
  greeting: "include:message"
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
  users: "include:base_url"
  posts: "include:base_url"
  static_endpoint: "https://static.example.com"
  version: "include:version"
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
early_ref: "include:late_value"

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
