# Sub-Configuration Feature

## Overview

The configuration system supports loading external configuration files using the `@include:` notation. This allows you to split large configuration files into smaller, manageable pieces and reuse common configuration across multiple projects.

## Syntax

Use the `@include:` prefix followed by a file path to reference another configuration file:

```yaml
# main.yml
app_name: "My Application"
database: "@include:config/database.yml"
api: "@include:config/api.yml"
```

## Features

### 1. Basic Sub-Config Loading
Reference external YAML files that get loaded and merged into the main configuration:

```yaml
# main.yml
app: "MyApp"
database: "@include:database.yml"
```

```yaml
# database.yml
host: localhost
port: 5432
username: admin
```

Result: `config.get("database:host")` returns `"localhost"`

### 2. Relative Paths
Relative paths are resolved relative to the directory containing the referencing file:

```yaml
# config/main.yml
database: "@include:database.yml"  # Resolves to config/database.yml
api: "@include:../shared/api.yml"  # Resolves to shared/api.yml
```

### 3. Absolute Paths
Absolute paths are supported:

```yaml
settings: "@include:/etc/myapp/settings.yml"
```

### 4. Nested Sub-Configs
Sub-configs can reference other sub-configs (recursive loading):

```yaml
# main.yml
database: "@include:database.yml"
```

```yaml
# database.yml
connection: "@include:connection.yml"
credentials: "@include:credentials.yml"
```

### 5. Multiple Sub-Configs
Load multiple sub-configs in a single file:

```yaml
# main.yml
database: "@include:database.yml"
api: "@include:api.yml"
cache: "@include:cache.yml"
logging: "@include:logging.yml"
```

### 6. Sub-Configs in Lists
Reference sub-configs within list structures:

```yaml
databases:
  - name: development
    host: localhost
  - "@include:production_db.yml"
```

### 7. Environment Variable Support
Sub-configs support environment variable substitution:

```yaml
# database.yml
host: "${DB_HOST}"
port: ${DB_PORT}
```

### 8. YAML Constructors
Sub-configs can use custom YAML constructors:

```yaml
# paths.yml
base_dir: /var/app
log_file: !path_join [/var/app, logs, app.log]
message: !join ["Hello", " ", "World"]
```

### 9. Mixed with Regular Values
Sub-configs can be mixed with regular configuration values:

```yaml
app_name: "MyApp"
version: "1.0.0"
database: "@include:database.yml"
features:
  auth: true
  cache: false
```

## Implementation Details

### How It Works

1. The `ConfigFactory.load()` method reads the main configuration file
2. The `_resolve_sub_configs()` method recursively scans all values
3. Any string value starting with `@include:` triggers sub-config loading
4. The path after `@include:` is extracted and resolved (relative or absolute)
5. The referenced file is loaded recursively (supporting nested sub-configs)
6. The loaded data replaces the `@include:...` string in the configuration tree
7. Environment variable substitution happens after all sub-configs are loaded

### Circular Reference Protection

Circular references (config A includes config B which includes config A) will raise a `RecursionError` when Python's recursion limit is reached.

### Empty Files

Empty YAML files load as empty dictionaries (`{}`), not `None`.

### Error Handling

- Missing sub-config files raise `FileNotFoundError` with a descriptive message
- Invalid YAML syntax in sub-configs raises standard YAML parsing errors
- Type mismatches raise `TypeError` with details about the expected vs actual type

## Examples

### Example 1: Database Configuration

```yaml
# main.yml
app: "MyApp"
database: "@include:config/database.yml"
```

```yaml
# config/database.yml
host: localhost
port: 5432
name: myapp_db
pool:
  min_size: 5
  max_size: 20
```

### Example 2: Multi-Environment Setup

```yaml
# main.yml
app: "MyApp"
environment: production
config: "@include:environments/${ENVIRONMENT}.yml"
```

```yaml
# environments/production.yml
database:
  host: prod-db.example.com
  port: 5432
  ssl: true
api:
  base_url: "https://api.prod.example.com"
  timeout: 30
```

### Example 3: Shared Configuration

```yaml
# project1/config.yml
app: "Project1"
common: "@include:../shared/common.yml"
```

```yaml
# project2/config.yml
app: "Project2"
common: "@include:../shared/common.yml"
```

```yaml
# shared/common.yml
logging:
  level: INFO
  format: "%(asctime)s - %(message)s"
monitoring:
  enabled: true
  interval: 60
```

## Best Practices

1. **Organize by Purpose**: Split configs by logical purpose (database, API, logging, etc.)
2. **Use Relative Paths**: Prefer relative paths for portability
3. **Avoid Deep Nesting**: Limit sub-config nesting to 2-3 levels for maintainability
4. **Document References**: Comment why certain configs are external
5. **Version Control**: Keep all sub-configs in version control
6. **Test Thoroughly**: Test with missing files and circular references
7. **Use Environment Variables**: Combine with env vars for environment-specific values

## Testing

The feature includes comprehensive unit tests in `tests/test_config.py` under the `TestConfigFactorySubConfigs` class, covering:

- Simple sub-config loading
- Relative and absolute paths
- Nested sub-configs
- Multiple sub-configs
- Sub-configs in lists
- Environment variable substitution
- YAML constructors in sub-configs
- Error handling (missing files, circular references)
- Mixed configuration values
- Empty files
- Complex nested structures

## Migration from `!` Notation

If you were using an earlier version with `!` notation, update your configs:

**Old (not recommended):**
```yaml
database: "!database.yml"
```

**New (recommended):**
```yaml
database: "@include:database.yml"
```

The `@include:` notation is:
- More explicit and self-documenting
- Won't conflict with YAML tags
- Common in other configuration systems
- Easier to search and identify in large codebases
