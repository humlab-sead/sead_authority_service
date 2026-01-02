# Schema Generation

This directory contains template-based SQL schema generation for entity embeddings and search functions.

## Directory Structure

```
schema/
├── templates/              # Jinja2 templates
│   └── entity_embeddings.sql.jinja2
├── generated/             # Auto-generated SQL files (git-ignored)
│   ├── location.sql
│   ├── method.sql
│   ├── site.sql
│   └── ...
└── README.md
```

## Usage

### Generate schema for all entities with embedding_config

```bash
python src/scripts/generate_entity_schema.py --all
```

### Generate schema for specific entities

```bash
python src/scripts/generate_entity_schema.py --entities method,site,location
```

### Force regeneration (overwrite existing files)

```bash
python src/scripts/generate_entity_schema.py --all --force
```

### Verbose output

```bash
python src/scripts/generate_entity_schema.py --all --verbose
```

## Configuration

Entity configurations are defined in `config/entities.yml`. Each entity that supports embeddings must have an `embedding_config` section:

```yaml
method:
  name: "Method"
  table_name: "tbl_methods"
  id_column: "method_id"
  label_column: "method_name"
  description_column: "description"
  embedding_config:
    dimension: 768                    # Embedding vector dimension
    ivfflat_lists: 10                 # IVFFLAT index lists parameter
    materialized: false               # Use materialized view vs regular view
    analyze: true                     # Run ANALYZE after creating table
    extra_columns: []                 # Additional columns to include in view
    joins: []                         # JOIN clauses for the view
    filter_params: []                 # Additional filter parameters for search functions
```

### Advanced Configuration: Filter Parameters

For entities that need additional filtering (e.g., location types), you can define filter parameters:

```yaml
location:
  embedding_config:
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

## Generated SQL Components

Each entity generates the following SQL objects:

1. **Embedding Table**: `authority.{entity}_embeddings`
   - Stores vector embeddings (pgvector)
   - Primary key references source table
   - IVFFLAT index for ANN search

2. **Entity View/Materialized View**: `authority.{entity}`
   - Combines source table with embeddings
   - Includes normalized label for fuzzy search
   - Optional extra columns (geography, metadata, etc.)

3. **Fuzzy Search Function**: `authority.fuzzy_{entity}(text, integer)`
   - Trigram-based similarity search using pg_trgm
   - Returns top-K matches with similarity scores

4. **Semantic Search Function**: `authority.semantic_{entity}(vector, integer)`
   - Vector similarity search using pgvector
   - Returns top-K matches by cosine similarity

5. **Hybrid Search Function**: `authority.search_{entity}_hybrid(...)`
   - Combines trigram and semantic search
   - Blends scores with configurable alpha parameter
   - Returns unified result set

## Integration with Makefile

Add to your `Makefile`:

```makefile
.PHONY: generate-schema
generate-schema:
	python src/scripts/generate_entity_schema.py --all

.PHONY: deploy-schema
deploy-schema: generate-schema
	psql -f schema/generated/*.sql
```

## Workflow

1. **Update Configuration**: Edit `config/entities.yml` to add/modify entities
2. **Generate Schema**: Run `make generate-schema` or the Python script directly
3. **Review Generated SQL**: Check files in `schema/generated/`
4. **Deploy to Database**: Run generated SQL files or use `make deploy-schema`

## Benefits

- **DRY Principle**: Single source of truth in configuration file
- **Consistency**: All entities follow the same pattern
- **Maintainability**: Easy to update all entities by modifying the template
- **Type Safety**: Generated SQL is strongly typed per entity
- **Flexibility**: Entity-specific customizations via configuration
- **Documentation**: Configuration serves as schema documentation

## Notes

- The `schema/generated/` directory should be added to `.gitignore`
- Manual SQL files remain in the `sql/` directory unchanged
- Generated files are intended for development and testing
- Production deployments should use the manually maintained `sql/` files until templates are fully tested
