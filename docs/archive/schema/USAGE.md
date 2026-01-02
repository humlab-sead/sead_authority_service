# Schema Generation Quick Start

## Generate All Entity Schemas

```bash
# Using make (recommended)
make generate-schema

# Or directly with uv
uv run python src/scripts/generate_entity_schema.py --all
```

## Generate Specific Entities

```bash
# Generate only method and site schemas
uv run python src/scripts/generate_entity_schema.py --entities method,site

# With verbose output
uv run python src/scripts/generate_entity_schema.py --entities method,site --verbose
```

## Force Regeneration

```bash
# Overwrite existing files
make generate-schema-force

# Or with the script
uv run python src/scripts/generate_entity_schema.py --all --force
```

## Adding a New Entity

1. Edit `config/entities.yml` and add the `embedding_config` section:

```yaml
your_entity:
  name: "Your Entity"
  table_name: "tbl_your_entity"
  id_column: "your_entity_id"
  label_column: "your_entity_name"
  description_column: "description"
  embedding_config:
    dimension: 768
    ivfflat_lists: 100
    materialized: false
    analyze: false
    extra_columns: []
    joins: []
    filter_params: []
```

2. Generate the schema:

```bash
make generate-schema
```

3. Review the generated file in `schema/generated/your_entity.sql`

## Configuration Options

### Basic Settings

- `dimension`: Vector dimension (default: 768)
- `ivfflat_lists`: Number of IVFFLAT index lists (default: 100, use 10 for small tables <500 rows)
- `materialized`: Use materialized view instead of regular view (default: false)
- `analyze`: Run ANALYZE after creating embeddings table (default: false)

### Advanced Settings

#### Extra Columns

Add additional columns to the entity view:

```yaml
extra_columns:
  - "t.latitude"
  - "t.longitude"
  - "ST_SetSRID(ST_MakePoint(t.longitude, t.latitude), 4326) AS geom"
```

#### Joins

Add JOIN clauses for related tables:

```yaml
joins:
  - "join public.tbl_location_types lt using (location_type_id)"
```

#### Filter Parameters

Add custom filter parameters to search functions:

```yaml
filter_params:
  - name: "location_type_ids"
    type: "integer[]"
    default: "null"
    description: "Filter by location type IDs"
    cte_definition: |
      select location_type_id
      from tbl_location_types
      where array_length(location_type_ids, 1) is null
         or location_type_id = ANY(location_type_ids)
    join_clause: "join filter_params using (location_type_id)"
    where_clause: ""
```

## Output Location

Generated files are saved to: `schema/generated/`

This directory is git-ignored and files are regenerated on demand.

## Comparing Generated vs Manual SQL

To compare generated SQL with your manually maintained files:

```bash
# Compare method entity
diff sql/06_method.sql schema/generated/method.sql

# Or use a visual diff tool
meld sql/06_method.sql schema/generated/method.sql
```

## Integration with Deployment

Currently, the `sql/` directory contains manually maintained files used for production.
The `schema/generated/` files are for development, testing, and eventual migration.

## Troubleshooting

### Missing PyYAML or Jinja2

The dependencies should already be installed, but if you encounter import errors:

```bash
uv pip install PyYAML jinja2 loguru
```

### Template Not Found

Ensure you're running from the project root directory:

```bash
cd /home/roger/source/sead_authority_service
uv run python src/scripts/generate_entity_schema.py --all
```

### Configuration Errors

Validate your YAML syntax:

```bash
python -c "import yaml; yaml.safe_load(open('config/entities.yml'))"
```
