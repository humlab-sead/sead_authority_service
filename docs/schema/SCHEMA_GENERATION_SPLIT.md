# Schema Generation Split - Summary

## Changes Made

The entity schema generation has been split into two separate templates to distinguish between tri-gram and semantic search SQL objects.

### Template Files

1. **`schema/templates/entity.sql.jinja2`** (NEW - Tri-gram only)
   - Generates SQL objects for tri-gram fuzzy search
   - Objects created:
     - `authority.{entity}` (view or materialized view)
     - `authority.fuzzy_{entity}()` (search function)
     - Trigram indexes

2. **`schema/templates/semantic-entity.sql.jinja2`** (NEW - Semantic/Embeddings)
   - Generates SQL objects for semantic search with vector embeddings
   - Objects created:
     - `authority.{entity}_embeddings` (separate table for vector embeddings)
     - `authority.update_{entity}_embeddings()` (function to populate embeddings)
     - `authority.semantic_{entity}()` (semantic search function - JOINs view with embeddings)
     - `authority.search_{entity}_hybrid()` (hybrid search function - JOINs view with embeddings)
     - Vector indexes on embeddings table
   - **Important**: This file does NOT modify the base view. Search functions JOIN the view with embeddings table.

3. **`schema/templates/entity.sql.jinja2.backup`** (Backup of original template)

### Generator Script Updates

**File:** `src/scripts/generate_entity_schema.py`

Changes:
- Split `generate_entity_sql()` into two functions:
  - `generate_trigram_sql()` - Uses `entity.sql.jinja2`
  - `generate_semantic_sql()` - Uses `semantic-entity.sql.jinja2`
- Added `get_trigram_config()` helper function
- Updated main logic to:
  - Generate trigram SQL for **ALL** entities
  - Generate semantic SQL only for entities with `embedding_config`

### File Naming Convention

- **Trigram files:** `{entity_key}.sql`
  - Example: `site.sql`, `location.sql`, `data_type_group.sql`
  
- **Semantic files:** `semantic-{entity_key}.sql`
  - Example: `semantic-site.sql`, `semantic-location.sql`
  - Only generated for entities with `embedding_config`

### Generation Results

Running `python src/scripts/generate_entity_schema.py --all` now produces:

- **28 trigram SQL files** (all entities)
- **16 semantic SQL files** (only entities with `embedding_config`)

Example entity without embeddings (data_type_group):
```
✅ data_type_group.sql         (generated)
❌ semantic-data_type_group.sql (NOT generated - no embedding_config)
```

Example entity with embeddings (site):
```
✅ site.sql                     (generated - trigram objects)
✅ semantic-site.sql            (generated - semantic objects)
```

## Usage

### Generate all entities
```bash
uv run python src/scripts/generate_entity_schema.py --all
```

### Generate specific entities
```bash
uv run python src/scripts/generate_entity_schema.py --entities site,location
```

### Force regeneration
```bash
uv run python src/scripts/generate_entity_schema.py --all --force
```

### Verbose output
```bash
uv run python src/scripts/generate_entity_schema.py --all --verbose
```

## Installation Order

Files can be installed in any order since they create separate objects:

1. **{entity}.sql** - Creates base view and fuzzy search function
2. **semantic-{entity}.sql** (if exists) - Creates embeddings table and semantic search functions

Example for site entity:
```bash
psql -f schema/generated/site.sql              # Creates authority.site view + fuzzy_site()
psql -f schema/generated/semantic-site.sql     # Creates site_embeddings table + semantic functions
```

**Key Architecture**: The semantic file does NOT modify the view. It creates a separate embeddings table that search functions JOIN with the base view.

## Benefits

1. **Clear Separation of Concerns**
   - Tri-gram search logic isolated from semantic search
   - Easier to maintain and update independently

2. **All Entities Get Tri-gram Search**
   - Previously, only entities with `embedding_config` got SQL objects
   - Now ALL entities get tri-gram search capabilities

3. **Explicit Semantic Dependencies**
   - Semantic search SQL clearly separated
   - Easy to identify which entities support vector search

4. **Better File Organization**
   - File names clearly indicate purpose
   - `semantic-*.sql` files are easy to identify and manage

5. **Clean Architecture**
   - Base views never contain embeddings (no mixing of concerns)
   - Embeddings kept in separate dedicated tables
   - Search functions handle JOINs internally
   - No risk of view replacement conflicts

## Migration Notes

- Old combined template backed up as `entity.sql.jinja2.backup`
- Existing generated files can be regenerated with `--force`
- No changes needed to entity configurations in `config/entities.yml`
- The generator automatically determines which templates to use based on `embedding_config` presence

## Example Output

```
13:15:59 | INFO     | Total entities: 28
13:15:59 | INFO     | Entities with embedding_config: 16
13:15:59 | INFO     | Generating trigram search SQL files...
13:15:59 | SUCCESS  | Generated trigram: schema/generated/site.sql
13:15:59 | SUCCESS  | Generated trigram: schema/generated/data_type_group.sql
...
13:15:59 | INFO     | Generating semantic search SQL files...
13:15:59 | SUCCESS  | Generated semantic: schema/generated/semantic-site.sql
...
13:15:59 | SUCCESS  | Generated 28 trigram SQL files
13:15:59 | SUCCESS  | Generated 16 semantic SQL files
```
