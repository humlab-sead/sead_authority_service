# SIMS Operations Guide

Operational reference for the SEAD Identity Management System (`src/identity/`).  
For design context see the system reference docs in `docs/SIMS/` (reflect Phases 1–2 implementation). For the module API see `src/identity/README.md`.

---

## Deployment

### Prerequisites

| Requirement                      | Detail                                                       |
|----------------------------------|--------------------------------------------------------------|
| PostgreSQL 16+                   | `pgcrypto` extension required (provides `gen_random_uuid()`) |
| `sead_authority_service` running | Module wires in at startup via `main.py`                     |
| Python deps                      | `psycopg`, `psycopg-pool` — already in `pyproject.toml`      |

### Applying Both Schemas

Start with a SEAD database that contains the public tables used by the
reconciliation strategies. From the Authority Service repository, generate
and apply its `authority` schema:

```bash
schema/create_schema.sh --deploy \
  --database "$DB_NAME" \
  --host "$DB_HOST" \
  --port "$DB_PORT" \
  --user "$DB_USER"
```

This generates `schema/__deploy__.sql` and deploys it. The generated SQL drops
and recreates `authority` with `CASCADE`, creates the required extensions, and
builds the configured reconciliation views and functions. Use it only when
that schema replacement is appropriate for the target database. Store
credentials in `~/.pgpass` or `PGPASSFILE`, not in command arguments.

Then apply the numbered `sead_identity` SQL files in lexical order. On a
fresh database with no `sead_identity` schema, apply every file once. On an
existing database, do not replay already-applied migrations:

```bash
for schema_file in schema/sql/identity/[0-9]*.sql; do
  psql -X -v ON_ERROR_STOP=1 \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    -f "$schema_file" || exit 1
done
```

The current sequence ends with `010_aggregate_identity_value.sql` and
`011_resolve_batch_idempotency.sql`. These migrations rename
`sead_internal_id` to `aggregate_id` and add the `resolve_batches` table.

### Verify After Deployment

```sql
-- Both schemas and required extensions
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'sead_identity';
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'authority';
SELECT extname FROM pg_extension WHERE extname = 'pgcrypto';
SELECT to_regprocedure('authority.fuzzy_site(text,integer)');

-- All ten SIMS tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'sead_identity'
ORDER BY table_name;

-- Current identity column and batch table exist
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'sead_identity'
  AND table_name = 'tracked_identities';
SELECT to_regclass('sead_identity.resolve_batches');

-- Well-known scopes seeded
SELECT scope_name FROM sead_identity.source_scopes ORDER BY scope_name;
-- Expected: sead://admin, sead://migration, sead://reconciliation
```

### Environment Variables

Set these in `.env` (root) or via environment before starting the service:

| Variable                                 | Example                     | Purpose          |
|------------------------------------------|-----------------------------|------------------|
| `SEAD_AUTHORITY_OPTIONS_DATABASE_HOST`   | `database_server.domain.xx` | DB host          |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_DBNAME` | `database_name`             | DB name          |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_USER`   | `database_user`             | DB user          |
| `SEAD_AUTHORITY_OPTIONS_DATABASE_PORT`   | `nnnn`                      | DB port          |
| `CONFIG_FILE`                            | `./config/config.yml`       | Config file path |

The identity module uses the shared connection pool set up by `setup_config_store()` at startup — no separate identity-specific connection configuration is needed.

### Running Integration Tests

```bash
SIMS_INTEGRATION_DB=1 uv run pytest -o addopts='' -q tests/identity/test_service_integration.py
```

Run these tests only against the helper-owned disposable database. See
[DEVELOPMENT.md](../DEVELOPMENT.md#disposable-database-for-integration-tests)
for its Podman setup, source dump, and connection settings. The test fixture
rejects targets other than `127.0.0.1:55432/sead_staging`.

---

## Configuration

### `config/identity_policy.yml`

Loaded once at startup by `src.identity.policy.IdentityPolicy`. This describes the current legacy implementation, which uses per-entity subtype defaults. It is not the target SIMS identity contract: the target uses generic allocator code with independently validated SIMS configuration and does not consume Shape Shifter's target model.

**Fields per entity entry:**

| Field              | Values                                                  | Meaning                                                                    |
|--------------------|---------------------------------------------------------|----------------------------------------------------------------------------|
| `entity_subtype`   | `provider_owned` \| `shared_metadata` \| `relationship` | Classification driving default behaviour                                   |
| `accept_uuid`      | `true` / `false`                                        | Legacy behavior: whether a caller-supplied UUID is accepted as the Tracked Identity; the target contract retains it as a source key and SIMS mints its own tracked UUID |
| `allow_allocation` | `true` / `false`                                        | Whether the service may mint a new Tracked Identity when no match is found |
| `auto_confirm`     | `true` / `false`                                        | Whether Binding Sets are auto-confirmed without manual review (D6)         |

**Subtype defaults:**

| Subtype           | `accept_uuid` | `allow_allocation` | `auto_confirm` |
|-------------------|---------------|--------------------|----------------|
| `provider_owned`  | `false`       | `true`             | `true`         |
| `shared_metadata` | `true`        | `false`            | `false`        |
| `relationship`    | `false`       | `false`            | `false`        |

Entities not listed in the file fall back to the `defaults:` block (currently `shared_metadata` conservative defaults: no allocation, no auto-confirm).

**Phase coverage as of 2026-04-06:**

| Entity                                                            | Subtype           | Phase             |
|-------------------------------------------------------------------|-------------------|-------------------|
| `site`, `sample_group`, `sample`, `analysis_entity`, `dataset`    | `provider_owned`  | Phase 1–2 (live)  |
| `taxa_tree_master`, `feature_type`, `method`, `data_type`, `unit` | `shared_metadata` | Phase 3 (planned) |
| `sample_dimension`, `abundance`                                   | `relationship`    | Phase 3 (planned) |

### Refreshing the Legacy Policy from Shape Shifter

The current `identity_policy.yml` was seeded from Shape Shifter's `sead_standard_model.yml`. Until the generic SIMS configuration replaces this legacy process:

1. Open `sead_standard_model.yml` in the Shape Shifter repo (`resources/target_models/`).
2. For each entity, check the `identity_tracking` and `reconciliation` fields.
3. Update `config/identity_policy.yml` to reflect new or changed entity entries.
4. Run the unit test suite to verify policy loads correctly: `uv run pytest tests/identity/test_policy.py -v`.
5. Regenerate `docs/SIMS/SHAPE_SHIFTER_TARGET_MODEL_ENTITY_REPORT.md` from Shape Shifter's superset model:

  ```bash
  cd /path/to/sead_shape_shifter
  python scripts/generate_target_model_docs.py resources/target_models/sead_standard_model.yml --format sims --output-dir /tmp/sims-docs
  cp /tmp/sims-docs/sead_standard_model.sims.md /path/to/sead_authority_service/docs/SIMS/SHAPE_SHIFTER_TARGET_MODEL_ENTITY_REPORT.md
  ```

There is no automated sync — this is intentional (D5: avoids runtime cross-repo dependency).

---

## Troubleshooting

### `ValueError: Config context 'default' not properly initialized`

**Cause:** `setup_config_store()` was not awaited before the first repository call.  
**Fix:** The FastAPI lifespan in `main.py` calls it at startup. If hitting this in tests, ensure `SIMS_INTEGRATION_DB=1` and that `tests/identity/conftest.py` fixture ran (session-scoped, automatic).

---

### `psycopg.errors.UndefinedTable: relation "sead_identity.source_scopes" does not exist`

**Cause:** Schema not applied to the target database.  
**Fix:** Run the SQL files in order per the Deployment section above.

---

### `pgcrypto` / `uuid-ossp` extension missing

```
ERROR:  function gen_random_uuid() does not exist
```

**Cause:** `pgcrypto` not installed on the PostgreSQL instance.  
**Fix:** `000_schema.sql` runs `CREATE EXTENSION IF NOT EXISTS pgcrypto;`. If it fails, the DB user lacks `SUPERUSER` or `pg_extension_owner` membership. Ask the DB admin to run:

```sql
CREATE EXTENSION pgcrypto;
```

---

### Duplicate source identity on re-submit

Re-submitting the same entity in the same scope is expected to produce the **same** `source_identity_uuid` (FR-12, FR-13). The `source_identity_keys` uniqueness constraint enforces this. If you see a `UniqueViolation` rather than a silent upsert, the repository `create_or_get` method encountered a race condition — safe to retry.

---

### `LookupError: Tracked identity <uuid> not found` from `detect_change`

**Cause:** A `ChangeDetectionRequest` was submitted for a Tracked Identity UUID that does not exist in `sead_identity.tracked_identities`.  
**Fix:** Ensure the entity was resolved and bound before calling `detect_change`. The Tracked Identity UUID comes from the `Binding` returned by `bind()`.

---

### Identity policy file not found at startup

```
FileNotFoundError: ... config/identity_policy.yml
```

**Cause:** Working directory is not the repo root, or `CONFIG_FILE` env var points to a non-standard location that changes the resolved path.  
**Fix:** Run the service from the repo root, or set an explicit policy path by overriding `ConfigValue("identity:policy_file")` in `config.yml`.

---

### Binding Set stays `proposed` — not auto-confirmed

**Cause:** At least one entity type in the batch has `auto_confirm: false` in the policy (e.g. shared metadata entities like `taxa_tree_master`).  
**Fix:** This is correct behaviour. Use `POST /identity/binding-sets/{id}/confirm` to confirm manually after review, or update the policy if auto-confirm is appropriate for that entity type.
