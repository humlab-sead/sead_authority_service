# Configuration File Reference

This document explains the structure and usage of the YAML configuration files (like `arbodat.yml`) that drive the data normalization process.

## Table of Contents

- [Overview](#overview)
- [File Structure](#file-structure)
- [Entity Configuration](#entity-configuration)
- [Field Reference](#field-reference)
- [Special Features](#special-features)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Validation](#validation)

## Overview

The configuration file defines how a large "denormalized" spreadsheet should be normalized into multiple related tables. Each table (called an "entity") is extracted from the source data, with relationships established through foreign keys.

### Key Concepts

1. **Entities**: Individual tables to be created from the source data
2. **Dependencies**: Order of processing based on foreign key relationships
3. **Extraction**: Selecting and transforming columns from source data
4. **Linking**: Establishing foreign key relationships between entities
5. **Unnesting**: Converting wide format data into long format (melt/pivot)
6. **Fixed Data**: Hardcoded lookup tables or SQL-sourced reference data

## File Structure

```yaml
entities:
  entity_name:
    # Configuration for this entity
    surrogate_id: unique_id
    columns: [...]
    # ... other fields

translation:
  # Optional: column name translations
  SourceColumnName: target_column_name
```

### Top-Level Sections

#### `entities`
**Required.** Contains all entity definitions as key-value pairs.

```yaml
entities:
  cultural_group:
    # cultural_group entity configuration
  
  epoch:
    # epoch entity configuration
```

#### `translation`
**Optional.** Maps source column names to target column names for final output.

```yaml
translation:
  ProjektNr: project_number
  Befu: feature_number
  ProbNr: sample_number
```

## Entity Configuration

Each entity is configured with various fields that control how data is extracted, transformed, and linked.

### Minimal Entity Example

```yaml
entities:
  simple_table:
    surrogate_id: simple_table_id
    columns: ["column1", "column2"]
    drop_duplicates: true
    depends_on: []
```

### Complete Entity Example

```yaml
entities:
  sample:
    # Identity
    surrogate_id: sample_id
    keys: ["ProjektNr", "Befu", "ProbNr"]
    
    # Data extraction
    columns: ["ProjektNr", "Befu", "ProbNr", "EDatProb"]
    source: null  # or name of another entity
    
    # Column transformation
    extra_columns:
      sample_name: "Befu"
      date_sampled: "EDatProb"
      alt_ref_type_id: null
    
    # Deduplication
    drop_duplicates: ["ProjektNr", "Befu", "ProbNr"]
    check_functional_dependency: true
    
    # Relationships
    foreign_keys:
      - entity: feature
        local_keys: ["ProjektNr", "Befu"]
        remote_keys: ["ProjektNr", "Befu"]
    
    # Processing order
    depends_on: ["feature", "sample_type"]
```

## Field Reference

### Core Identity Fields

#### `surrogate_id`
**Type:** String  
**Required:** Recommended for all entities  
**Description:** Name of the auto-generated primary key column.

```yaml
surrogate_id: cultural_group_id
```

**Convention:** Should end with `_id`

#### `keys`
**Type:** List of strings  
**Required:** No (but required if `columns` is empty)  
**Description:** Columns that uniquely identify a row. Used for deduplication and as natural keys.

```yaml
keys: ["ProjektNr", "Befu", "ProbNr"]
```

#### `columns`
**Type:** List of strings  
**Required:** No (but required if `keys` is empty)  
**Description:** All columns to extract from the source data.

```yaml
columns: ["id", "name", "description", "created_date"]
```

**Note:** `keys` are automatically included in the final output even if not in `columns`.

### Data Source Fields

#### `source`
**Type:** String or `null`  
**Default:** `null` (uses main survey data)  
**Description:** Specifies which entity to use as the data source instead of the main survey.

```yaml
# Extract from main survey
source: null

# Extract from another entity
source: sample_property_sheet
```

**Use case:** Creating derived tables from previously extracted entities.

#### `type`
**Type:** String (`"data"` or `"fixed"`)  
**Default:** `"data"`  
**Description:** Indicates whether this is a regular data table or a fixed lookup table.

```yaml
type: fixed  # For lookup tables
type: data   # For regular tables (default)
```

### Fixed Data Fields

For entities with `type: fixed`:

#### `surrogate_name`
**Type:** String  
**Description:** Column name used as the natural key in fixed data tables.

```yaml
surrogate_name: location_type
```

#### `values`
**Type:** List or SQL string  
**Required:** Yes (for fixed data entities)  
**Description:** Defines the data for fixed lookup tables.

**Simple list format:**
```yaml
type: fixed
surrogate_id: location_type_id
surrogate_name: location_type
columns: ["location_type"]
values:
  - Ort
  - Kreis
  - Land
  - Staat
```

**Multi-column format:**
```yaml
type: fixed
surrogate_id: sample_description_type_id
columns: ["type_name", "type_description", "arbodat_code"]
values:
  - ["Is mass find?", "Indicates if sample is a mass find.", "Vorfu"]
  - ["Wet/dry?", "Wet or dry sample indicator", "AblaBdgProb"]
  - ["Sampling date", "Date when sample was collected", "EDatProb"]
```

**SQL format:**
```yaml
type: fixed
surrogate_id: system_id
columns: ["dimension_id", "dimension_name"]
values: |
  sql: 
  select dimension_id, dimension_name
  from public.tbl_dimensions
```

### Transformation Fields

#### `extra_columns`
**Type:** Dictionary  
**Description:** Add or rename columns in the output.

**Two modes:**

1. **Rename mode** (source column → target column name):
```yaml
extra_columns:
  sample_name: "Befu"          # Rename "Befu" to "sample_name"
  date_sampled: "EDatProb"     # Rename "EDatProb" to "date_sampled"
```

2. **Constant mode** (new column → constant value):
```yaml
extra_columns:
  alt_ref_type_id: null        # Add column with null value
  project_type_id: 0           # Add column with constant value
  status: "active"             # Add column with string constant
```

#### `unnest`
**Type:** Dictionary  
**Description:** Convert wide format to long format (pandas melt operation).

```yaml
unnest:
  id_vars: ["sample_id", "ProjektNr", "Befu", "ProbNr"]
  value_vars: ["KoordX", "KoordY", "KoordZ"]
  var_name: coordinate_type
  value_name: coordinate_value
```

**Before unnesting:**
| sample_id | KoordX | KoordY | KoordZ |
|-----------|--------|--------|--------|
| 1         | 100    | 200    | 50     |

**After unnesting:**
| sample_id | coordinate_type | coordinate_value |
|-----------|-----------------|------------------|
| 1         | KoordX          | 100              |
| 1         | KoordY          | 200              |
| 1         | KoordZ          | 50               |

**Fields:**
- `id_vars`: Columns to keep as identifiers
- `value_vars`: Columns to unpivot
- `var_name`: Name for the new category column
- `value_name`: Name for the new value column

### Deduplication Fields

#### `drop_duplicates`
**Type:** Boolean, list of strings, or include directive  
**Default:** `false`  
**Description:** Control duplicate row removal.

```yaml
# Remove all duplicate rows
drop_duplicates: true

# Remove duplicates based on specific columns
drop_duplicates: ["column1", "column2"]

# Use keys from entity definition
drop_duplicates: "@value: entities.sample.keys"
```

#### `check_functional_dependency`
**Type:** Boolean  
**Default:** `false`  
**Description:** Validate that non-key columns are functionally dependent on keys before deduplication.

```yaml
keys: ["id"]
columns: ["id", "name", "value"]
drop_duplicates: ["id"]
check_functional_dependency: true  # Ensures all rows with same id have same name/value
```

### Relationship Fields

#### `foreign_keys`
**Type:** List of foreign key definitions  
**Description:** Define relationships to other entities.

```yaml
foreign_keys:
  - entity: parent_table
    local_keys: ["parent_id"]
    remote_keys: ["id"]
    extra_columns:
      parent_name: "name"
      parent_type: "type"
    drop_remote_id: false
```

**Foreign Key Fields:**

##### `entity`
**Required:** Yes  
**Description:** Name of the referenced entity.

##### `local_keys`
**Required:** Yes  
**Type:** List of strings or include directive  
**Description:** Columns in this entity used for matching.

```yaml
local_keys: ["parent_id", "parent_type"]
# Or reference another entity's keys:
local_keys: "@value: entities.site.keys"
```

##### `remote_keys`
**Required:** Yes  
**Type:** List of strings or include directive  
**Description:** Columns in the referenced entity used for matching.

```yaml
remote_keys: ["id", "type"]
# Or reference another entity's keys:
remote_keys: "@value: entities.site.keys"
```

##### `extra_columns`
**Type:** Dictionary, list, or string  
**Description:** Additional columns to copy from the remote entity.

```yaml
# Dictionary: remote_column → local_column_name
extra_columns:
  coordinate_system: "Koordinatensystem"
  easting: "Easting"
  elevation: "Höhe"

# List: copy columns with same names
extra_columns: ["name", "description"]

# String: copy single column
extra_columns: "name"
```

##### `drop_remote_id`
**Type:** Boolean  
**Default:** `false`  
**Description:** Whether to drop the remote surrogate ID after linking when using `extra_columns`.

```yaml
drop_remote_id: true  # Don't keep the foreign key ID
```

#### `depends_on`
**Type:** List of strings  
**Required:** Recommended  
**Description:** Entities that must be processed before this one.

```yaml
depends_on: ["parent_entity", "lookup_table"]
```

**Note:** Dependencies are also automatically inferred from `foreign_keys` and `source`.

## Special Features

### Include Directives

Reference values from other parts of the configuration:

```yaml
# Reference another entity's keys
local_keys: "@value: entities.site.keys"

# Reference another entity's values
value_vars: "@value: entities.location_type.values"

# Reference surrogate_id
id_vars: ["@value: entities.sample.surrogate_id"]

# Complex reference
drop_duplicates: "@value: entities.natural_region.keys + @value: entities.site.keys"
```

### Pending Columns

Columns created by unnesting are considered "pending" until the unnest operation completes. This affects foreign key linking order.

```yaml
location:
  columns: ["Ort", "Kreis", "Land"]
  unnest:
    value_vars: ["Ort", "Kreis", "Land"]
    var_name: location_type      # This becomes a "pending" column
    value_name: location_name

  foreign_keys:
    - entity: location_type
      local_keys: ["location_type"]  # Can't link until after unnesting
      remote_keys: ["location_type"]
```

### Column Ordering

Final column order in output:
1. Surrogate ID (primary key)
2. Foreign key IDs
3. Extra columns (from `extra_columns`)
4. Other columns (from `columns`)

This is automatically handled by the `move_keys_to_front()` method.

## Examples

### Simple Lookup Table

```yaml
cultural_group:
  surrogate_id: cultural_group_id
  keys: ["KultGr"]
  columns: ["KultGr"]
  drop_duplicates: true
  depends_on: []
```

### Hierarchical Relationship

```yaml
remain_type_group:
  surrogate_id: remain_type_group_id
  keys: ["RTypGrup"]
  columns: ["RTypGrup"]
  drop_duplicates: true
  depends_on: []

remain_type:
  surrogate_id: remain_type_id
  keys: ["RTyp", "RTypGrup"]
  columns: ["RTyp", "RTypGrup"]
  foreign_keys:
    - entity: remain_type_group
      local_keys: ["RTypGrup"]
      remote_keys: ["RTypGrup"]
  drop_duplicates: "@value: entities.remain_type.keys"
  depends_on: ["remain_type_group"]
```

### Many-to-Many Junction Table

```yaml
site_site_type:
  surrogate_id: site_site_type_id
  keys: []
  columns: []  # Gets columns from foreign keys
  foreign_keys:
    - entity: site_type
      local_keys: "@value: entities.site_type.keys"
      remote_keys: "@value: entities.site_type.keys"
    - entity: site
      local_keys: "@value: entities.site.keys"
      remote_keys: "@value: entities.site.keys"
  drop_duplicates: true
  depends_on: ["site", "site_type"]
```

### Fixed Data from SQL

```yaml
dimensions:
  surrogate_id: system_id
  type: fixed
  columns: ["dimension_id", "dimension_name"]
  drop_duplicates: true
  depends_on: []
  values: |
    sql: 
    select dimension_id, dimension_name
    from public.tbl_dimensions
```

### Unnesting with Foreign Keys

```yaml
sample_coordinate:
  surrogate_id: sample_coordinate_id
  keys: []
  columns: ["KoordX", "KoordY", "KoordZ", "TiefeBis", "TiefeVon"]
  
  # First unnest the data
  unnest:
    id_vars: ["@value: entities.sample.surrogate_id"]
    value_vars: ["KoordX", "KoordY", "KoordZ", "TiefeBis", "TiefeVon"]
    var_name: coordinate_type
    value_name: coordinate_value
  
  # Then link to related entities
  foreign_keys:
    - entity: sample
      local_keys: "@value: entities.sample.keys"
      remote_keys: "@value: entities.sample.keys"
    - entity: coordinate_method_dimensions
      local_keys: ["coordinate_type"]
      remote_keys: ["coordinate_type"]
  
  drop_duplicates: true
  depends_on: ["sample", "coordinate_method_dimensions"]
```

### Extra Columns with Foreign Key

```yaml
site:
  surrogate_id: site_id
  keys: ["ProjektNr", "Fustel", "EVNr"]
  columns: ["ProjektNr", "Fustel", "EVNr"]
  
  # Add renamed columns
  extra_columns:
    site_name: "Fustel"
    national_site_identifier: "EVNr"
  
  # Link to coordinates and copy extra fields
  foreign_keys:
    - entity: site_coordinate
      local_keys: "@value: entities.site.keys"
      remote_keys: "@value: entities.site.keys"
      extra_columns:
        coordinate_system: "Koordinatensystem"
        easting: "Easting"
        northing: "Northing"
        elevation: "Höhe"
      drop_remote_id: true  # Don't keep site_coordinate_id
  
  drop_duplicates: "@value: entities.site.keys"
  depends_on: ["site_coordinate"]
```

## Best Practices

### Naming Conventions

1. **Entity names**: Use snake_case, descriptive names
   ```yaml
   sample_group:        # Good
   sampleGroup:         # Avoid
   sg:                  # Avoid (too cryptic)
   ```

2. **Surrogate IDs**: End with `_id`, match entity name
   ```yaml
   sample_group_id:     # Good
   id:                  # Avoid (not specific)
   sampleGroupId:       # Avoid (camelCase)
   ```

3. **Column names**: Use snake_case for translated names
   ```yaml
   translation:
     ProjektNr: project_number     # Good
     ProjektNr: ProjectNumber      # Avoid (camelCase)
   ```

### Dependency Management

1. **Always specify `depends_on`** even if inferred from foreign keys
   ```yaml
   # Explicit is better than implicit
   depends_on: ["parent_table", "lookup_table"]
   ```

2. **Order entities** in config to reflect logical processing order

3. **Avoid circular dependencies** - the validator will catch these

### Data Quality

1. **Use `check_functional_dependency`** for important tables
   ```yaml
   check_functional_dependency: true  # Validates data consistency
   ```

2. **Specify `keys`** explicitly for meaningful deduplication
   ```yaml
   keys: ["natural_key1", "natural_key2"]
   drop_duplicates: "@value: entities.table.keys"
   ```

3. **Use meaningful deduplication** - not just `drop_duplicates: true`
   ```yaml
   # Specific deduplication
   drop_duplicates: ["id", "type"]
   
   # Rather than generic
   drop_duplicates: true
   ```

### Foreign Keys

1. **Match key lengths** - `local_keys` and `remote_keys` must have same count

2. **Use include directives** for consistency
   ```yaml
   local_keys: "@value: entities.site.keys"  # DRY principle
   ```

3. **Document complex relationships** with comments
   ```yaml
   foreign_keys:
     # Links to site via composite natural key
     - entity: site
       local_keys: ["ProjektNr", "Fustel", "EVNr"]
       remote_keys: ["ProjektNr", "Fustel", "EVNr"]
   ```

### Performance

1. **Process independent entities** in parallel (handled automatically by dependency resolution)

2. **Minimize unnesting** - only unnest when necessary

3. **Use specific column lists** rather than extracting everything

## Validation

Always validate your configuration before running:

```bash
python validate_config.py config.yml
```

See [docs/config_validation.md](docs/config_validation.md) for details.

### Common Validation Errors

1. **Missing required fields**
   ```
   Entity 'table': data table must have 'columns' or 'keys'
   ```
   **Fix:** Add `columns` or `keys` field

2. **Circular dependencies**
   ```
   Circular dependency detected: a -> b -> c -> a
   ```
   **Fix:** Remove or restructure dependencies

3. **Non-existent entity references**
   ```
   Entity 'child': references non-existent entity 'parent' in foreign key
   ```
   **Fix:** Ensure referenced entity exists or fix typo

4. **Mismatched key lengths**
   ```
   Entity 'table', foreign key #1: 'local_keys' length (2) does not match 'remote_keys' length (1)
   ```
   **Fix:** Ensure both key lists have same number of columns

5. **Duplicate surrogate IDs**
   ```
   Surrogate ID 'id' is used by multiple entities: table1, table2
   ```
   **Fix:** Use unique surrogate ID names for each entity

## Troubleshooting

### Entity not being processed

**Symptom:** Entity appears in config but not in output

**Possible causes:**
1. Circular dependency - check `depends_on` chains
2. Missing dependency - entity referenced in `depends_on` doesn't exist
3. Validation errors - run `validate_config.py`

### Foreign key linking fails

**Symptom:** Foreign key column not added to entity

**Possible causes:**
1. Remote entity not processed yet - check `depends_on`
2. Column names don't match - verify `local_keys` and `remote_keys`
3. Unnesting not complete - foreign key needs "pending" column

### Duplicate rows after processing

**Symptom:** More rows than expected in output

**Possible causes:**
1. `drop_duplicates` not set correctly
2. Wrong columns specified in `drop_duplicates` list
3. Cartesian product from foreign key with missing values

### Missing columns in output

**Symptom:** Expected columns not in final table

**Possible causes:**
1. Column not in `columns` list
2. Column not in `keys` list
3. Source entity doesn't have the column
4. Unnesting renamed the column

## Advanced Topics

### Deferred Linking

Some foreign keys can't be resolved immediately (e.g., when they depend on unnested columns). The normalizer automatically defers these links and retries after unnesting.

### Column Resolution Order

1. Extract columns from source
2. Apply `extra_columns` transformations
3. Add foreign key columns via linking
4. Apply unnesting (if configured)
5. Retry deferred foreign keys
6. Apply translation (if configured)
7. Reorder columns (keys first)

### Dynamic Configuration

Use include directives to build configuration dynamically:

```yaml
site_properties:
  value_vars: "@value: entities.site_property_type.values"
```

This pulls values from another entity definition at runtime.

## See Also

- [docs/config_validation.md](docs/config_validation.md) - Configuration validation system
- [src/arbodat/normalizer.py](src/arbodat/normalizer.py) - Normalization engine
- [src/arbodat/config_model.py](src/arbodat/config_model.py) - Configuration data model
- [tests/arbodat/test_config_specifications.py](tests/arbodat/test_config_specifications.py) - Validation tests
