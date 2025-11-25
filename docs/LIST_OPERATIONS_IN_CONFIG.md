# List Operations in Configuration Include Directives

## Overview

The configuration system now supports list operations with `include:` directives, allowing you to build lists dynamically by referencing and combining other configuration values.

## Constraints

To keep the implementation simple and maintainable, the following constraints are enforced:

1. **No Nested Lists**: Only flat lists are allowed. Lists containing other lists will be rejected.
2. **No Brackets in Values**: String values within lists cannot contain `[` or `]` characters.

These constraints ensure reliable parsing and prevent edge cases while covering the vast majority of practical use cases.

## Basic Syntax

### Simple Include (existing feature)
```yaml
entities:
  sample:
    keys: ["ProjektNr", "Befu", "ProbNr"]
  
  another_entity:
    columns: "include: entities.sample.keys"
    # Result: ["ProjektNr", "Befu", "ProbNr"]
```

### Prepend Items
```yaml
entities:
  sample:
    keys: ["ProjektNr", "Befu", "ProbNr"]
  
  extended:
    columns: "['sample_id'] + include: entities.sample.keys"
    # Result: ["sample_id", "ProjektNr", "Befu", "ProbNr"]
```

### Append Items
```yaml
entities:
  sample:
    keys: ["ProjektNr", "Befu", "ProbNr"]
  
  extended:
    columns: "include: entities.sample.keys + ['notes', 'status']"
    # Result: ["ProjektNr", "Befu", "ProbNr", "notes", "status"]
```

### Both Prepend and Append
```yaml
entities:
  sample:
    keys: ["ProjektNr", "Befu", "ProbNr"]
  
  extended:
    columns: "['sample_id'] + include: entities.sample.keys + ['created_at']"
    # Result: ["sample_id", "ProjektNr", "Befu", "ProbNr", "created_at"]
```

### Multiple Includes
```yaml
entities:
  location:
    keys: ["Ort", "Kreis", "Land"]
  
  site:
    keys: ["ProjektNr", "Fustel"]
  
  site_location:
    columns: "include: entities.site.keys + include: entities.location.keys"
    # Result: ["ProjektNr", "Fustel", "Ort", "Kreis", "Land"]
```

### Complex Chaining
```yaml
entities:
  project:
    keys: ["ProjektNr"]
  
  site:
    keys: "include: entities.project.keys + ['Fustel', 'EVNr']"
    # Result: ["ProjektNr", "Fustel", "EVNr"]
  
  feature:
    keys: "include: entities.site.keys + ['Befu']"
    # Result: ["ProjektNr", "Fustel", "EVNr", "Befu"]
  
  sample:
    keys: "include: entities.feature.keys + ['ProbNr']"
    # Result: ["ProjektNr", "Fustel", "EVNr", "Befu", "ProbNr"]
```

## Real-World Examples

### Foreign Key Configuration
```yaml
entities:
  sample:
    surrogate_id: sample_id
    keys: ["ProjektNr", "Befu", "ProbNr"]
  
  taxa:
    surrogate_id: taxon_id
    keys: ["BNam", "TaxAut"]
  
  sample_taxa:
    keys: []
    columns: "include: entities.sample.keys + include: entities.taxa.keys + ['SumFAnzahl']"
    # Result: ["ProjektNr", "Befu", "ProbNr", "BNam", "TaxAut", "SumFAnzahl"]
    
    foreign_keys:
      - entity: sample
        local_keys: "include: entities.sample.keys"
        remote_keys: "include: entities.sample.keys"
      - entity: taxa
        local_keys: "include: entities.taxa.keys"
        remote_keys: "include: entities.taxa.keys"
```

### Unnest Configuration
```yaml
entities:
  location:
    surrogate_id: location_id
    keys: ["Ort", "Kreis", "Land", "Staat", "FlurStr"]
    unnest:
      id_vars: "include: entities.location.surrogate_id"
      # Result: "location_id"
      
      value_vars: "include: entities.location.keys"
      # Result: ["Ort", "Kreis", "Land", "Staat", "FlurStr"]
      
      var_name: location_type
      value_name: location_name
```

### Building Columns from Multiple Sources
```yaml
defaults:
  audit_columns: ["created_at", "created_by", "updated_at", "updated_by"]

entities:
  sample:
    surrogate_id: sample_id
    keys: ["ProjektNr", "Befu", "ProbNr"]
    
    # All columns = surrogate + keys + data columns + audit
    columns: "['sample_id'] + include: entities.sample.keys + ['depth', 'notes'] + include: defaults.audit_columns"
    # Result: ["sample_id", "ProjektNr", "Befu", "ProbNr", "depth", "notes", "created_at", "created_by", "updated_at", "updated_by"]
```

### Hierarchical Entity Keys
```yaml
entities:
  project:
    keys: ["ProjektNr"]
    columns: "include: entities.project.keys"
  
  site:
    keys: "include: entities.project.keys + ['Fustel']"
    columns: "include: entities.site.keys + ['site_type']"
  
  feature:
    keys: "include: entities.site.keys + ['Befu']"
    columns: "include: entities.feature.keys + ['feature_type']"
  
  sample:
    keys: "include: entities.feature.keys + ['ProbNr']"
    columns: "include: entities.sample.keys + ['sample_date', 'depth']"
```

## Features

- **List Literals**: Use standard YAML/JSON list syntax: `['item1', 'item2']`
- **Concatenation Operator**: Use `+` to combine lists
- **Path Resolution**: Use dot notation for nested paths: `entities.sample.keys`
- **Recursive Resolution**: Include directives within referenced values are also resolved
- **Type Flexibility**: Works with strings, numbers, and mixed types in lists
- **Error Handling**: Malformed expressions or constraint violations return the original string
- **Backward Compatibility**: Simple `include:` directives work exactly as before

## Constraint Examples

```yaml
# ✅ ALLOWED
columns: "['a', 'b', 'c']"                      # Flat list
columns: "include: entities.sample.keys"         # Simple include
columns: "['id'] + include: path + ['status']"  # List operations

# ❌ NOT ALLOWED (returns original string)
columns: "[['nested'], 'item']"                 # Nested list (constraint #1)
columns: "['value[with]brackets']"              # Brackets in values (constraint #4)
source: [["nested"], "item"]
columns: "include: source"                       # References nested list (constraint #1)
```

## Notes

- Whitespace around operators is handled automatically
- Empty lists are handled gracefully
- Nonexistent paths are skipped (won't break the operation)
- The feature integrates seamlessly with existing `@include:` file includes
- All operations are evaluated at configuration load time

## Implementation Details

The feature is implemented in `src/utility.py` via:
- `_parse_list_expression()`: Parses and evaluates list expressions
- `_replace_references()`: Recursively processes configuration data
- `replace_references()`: Main entry point called by `ConfigFactory`

The parser:
1. Validates bracket balance and detects list operations
2. Splits expressions by `+` operator (simple state machine: in/out of list)
3. Evaluates each part (include directive or list literal)
4. Enforces constraints (no nested lists, no brackets in values)
5. Concatenates results into a single flat list
6. Returns original string if parsing fails or constraints violated (safe fallback)

### Constraint Enforcement

**Constraint #1 (No Nested Lists)**: After parsing each list literal or resolving each include, the parser checks if any item is itself a list using `isinstance(item, list)`. If found, parsing fails and returns the original string.

**Constraint #4 (No Brackets in Values)**: When parsing list literals, the parser checks if any string item contains `[` or `]` characters. If found, parsing fails and returns the original string.

These checks ensure that all lists remain flat and parseable without complex escape sequences.
