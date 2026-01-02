# SQL File Installation Order

## Architecture Overview

The schema generation split creates two types of SQL files:

1. **{entity}.sql** - Tri-gram search objects (view + fuzzy search)
2. **semantic-{entity}.sql** - Semantic search objects (embeddings table + semantic search functions)

## Installation Order

Files can be installed in any order, but typically you'll want the base view first:

```bash
# Step 1: Install trigram file (creates base view and fuzzy search)
psql -f schema/generated/{entity}.sql

# Step 2: Install semantic file (creates embeddings table and semantic search)
psql -f schema/generated/semantic-{entity}.sql  # Only if file exists
```

## Clean Separation of Concerns

### What {entity}.sql Creates
- `authority.{entity}` view/materialized view (base entity data, NO embeddings)
- `authority.fuzzy_{entity}()` function for tri-gram fuzzy search
- Trigram indexes on the view

**Example (site.sql):**
```sql
create materialized view authority.site as
  select
    t.site_id,
    t.site_name as label,
    authority.immutable_unaccent(lower(t.site_name)) as norm_label,
    t.site_description,
    t.national_site_identifier,
    t.latitude_dd,
    t.longitude_dd,
    ST_SetSRID(ST_MakePoint(t.longitude_dd, t.latitude_dd), 4326) AS geom
  from public.tbl_sites as t;
  -- Note: NO emb column - embeddings kept separate!
```

### What semantic-{entity}.sql Creates
- `authority.{entity}_embeddings` table (separate table for embeddings)
- `authority.update_{entity}_embeddings()` function to populate embeddings
- `authority.semantic_{entity}()` function for pure semantic search
- `authority.search_{entity}_hybrid()` function for hybrid search
- Vector indexes on the embeddings table

**Key Design**: The view is NOT modified. Search functions JOIN the view with embeddings.

**Example (semantic-site.sql):**
```sql
-- Creates separate embeddings table
create table authority.site_embeddings (
  site_id integer primary key,
  emb vector(768)
);

-- Semantic search JOINs view with embeddings
create function authority.semantic_site(qemb vector, p_limit integer)
returns table (site_id integer, label text, sem_sim double precision)
as $$
  select
    v.site_id,
    v.label,
    1.0 - (e.emb <=> qemb) as sem_sim
  from authority.site as v                      -- Base view
  inner join authority.site_embeddings as e     -- Embeddings table
    using (site_id)
  where e.emb is not null
  order by e.emb <=> qemb
  limit p_limit;
$$;
```

## Installation Examples

### Entity WITH Embeddings (e.g., site)

```bash
# Both files exist - install in order
psql -d sead -f schema/generated/site.sql           # Creates base view
psql -d sead -f schema/generated/semantic-site.sql  # Extends view with embeddings
```

### Entity WITHOUT Embeddings (e.g., data_type_group)

```bash
# Only trigram file exists - install it
psql -d sead -f schema/generated/data_type_group.sql

# No semantic file needed - entity doesn't have embedding_config
```

## Batch Installation Script

```bash
#!/bin/bash
# install_entity_schemas.sh

DB="sead"
SCHEMA_DIR="schema/generated"

# Install all trigram files first
for file in $SCHEMA_DIR/*.sql; do
  if [[ ! "$file" =~ semantic- ]]; then
    echo "Installing: $file"
    psql -d $DB -f "$file"
  fi
done

# Then install all semantic files
for file in $SCHEMA_DIR/semantic-*.sql; do
  if [ -f "$file" ]; then
    echo "Installing: $file"
    psql -d $DB -f "$file"
  fi
done
```

## Benefits of This Architecture

### 1. Clean Separation
- **Base view** (`authority.{entity}`) contains only source data
- **Embeddings table** (`authority.{entity}_embeddings`) keeps vectors separate
- No mixing of concerns - embeddings never in materialized views

### 2. Flexible Installation
- Files can be installed independently
- Installing semantic file doesn't modify the base view
- No risk of view replacement conflicts

### 3. Performance Benefits
- Embeddings not duplicated in materialized views
- Vector indexes on dedicated embeddings table
- Joins only happen when needed (in search functions)

### 4. Easy Maintenance
- Update base view without touching embeddings
- Regenerate embeddings without affecting base view
- Clear separation makes debugging easier

## Verification

After installation, verify the structure:

```sql
-- Check base view (NO emb column)
\d+ authority.site

-- Should see:
--   site_id, label, norm_label, site_description, 
--   national_site_identifier, latitude_dd, longitude_dd, geom
--   (NO emb column)

-- Check embeddings table (if semantic file installed)
\d+ authority.site_embeddings

-- Should see:
--   site_id (PK), emb (vector)

-- Test semantic search (automatically joins view + embeddings)
SELECT * FROM authority.semantic_site('[0.1,0.2,...]'::vector, 10);
```

## Summary

| File Type | Creates View | Creates Embeddings Table | View Includes `emb`? | Search Functions Join? |
|-----------|--------------|--------------------------|---------------------|----------------------|
| {entity}.sql | ✅ Yes | ❌ No | ❌ No | N/A |
| semantic-{entity}.sql | ❌ No (uses existing) | ✅ Yes | ❌ No (kept separate) | ✅ Yes (automatic) |

**Key Takeaway**: Embeddings are kept in a separate table and joined by search functions. The base view never contains embeddings.
