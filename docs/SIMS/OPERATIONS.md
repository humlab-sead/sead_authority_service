# SIMS Operations Guide

Operational reference for the SEAD Identity Management System (`src/identity/`).  
For design context see the frozen design docs in `docs/SIMS/design`. For the module API see `src/identity/README.md`.

---

## Deployment

### Prerequisites

| Requirement                      | Detail                                                       |
|----------------------------------|--------------------------------------------------------------|
| PostgreSQL 16+                   | `pgcrypto` extension required (provides `gen_random_uuid()`) |
| `sead_authority_service` running | Module wires in at startup via `main.py`                     |
| Python deps                      | `psycopg`, `psycopg-pool` — already in `pyproject.toml`      |

### Applying the Schema

SQL files live in `schema/sql/identity/`. Apply them in order against the target database:

```bash
PGPASSWORD=<password> psql -h <host> -p <port> -U <user> -d <dbname> \
  -f schema/sql/identity/000_schema.sql \
  -f schema/sql/identity/001_source_scopes.sql \
  -f schema/sql/identity/002_submissions.sql \
  -f schema/sql/identity/003_source_identities.sql \
  -f schema/sql/identity/003b_source_identity_keys.sql \
  -f schema/sql/identity/004_submission_source_identities.sql \
  -f schema/sql/identity/005_tracked_identities.sql \
  -f schema/sql/identity/006_binding_sets.sql \
  -f schema/sql/identity/007_bindings.sql \
  -f schema/sql/identity/008_seed_scopes.sql
```

Or use the merged file for a single-shot deploy:

```bash
psql ... -f schema/sql/identity/__merged.sql
```

`__merged.sql` is checked in and reflects the full schema. Regenerate it after any DDL change:

```bash
cat schema/sql/identity/0*.sql > schema/sql/identity/__merged.sql
```

### Verify After Deployment

```sql
-- Schema and extension
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'sead_identity';
SELECT extname FROM pg_extension WHERE extname = 'pgcrypto';

-- All seven tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'sead_identity'
ORDER BY table_name;

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
SIMS_INTEGRATION_DB=1 ENV_FILE=tests/.env uv run pytest tests/identity/test_service_integration.py -v
```

`tests/.env` must contain the DB credentials above. The integration tests create isolated scopes (unique per run) and do not pollute persistent data.

---

## Configuration

### `config/identity_policy.yml`

Loaded once at startup by `src.identity.policy.IdentityPolicy`. Controls per-entity-type behaviour.

**Fields per entity entry:**

| Field              | Values                                                  | Meaning                                                                    |
|--------------------|---------------------------------------------------------|----------------------------------------------------------------------------|
| `entity_subtype`   | `provider_owned` \| `shared_metadata` \| `relationship` | Classification driving default behaviour                                   |
| `accept_uuid`      | `true` / `false`                                        | Whether a caller-supplied UUID is accepted as the Tracked Identity (FR-11) |
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

### Refreshing the Policy from Shape Shifter

`identity_policy.yml` is seeded from Shape Shifter's `sead_standard_model.yml`. After a Shape Shifter release:

1. Open `sead_standard_model.yml` in the Shape Shifter repo (`target_models/`).
2. For each entity, check the `identity_tracking` and `reconciliation` fields.
3. Update `config/identity_policy.yml` to reflect new or changed entity entries.
4. Run the unit test suite to verify policy loads correctly: `uv run pytest tests/identity/test_policy.py -v`.
5. Update `docs/SIMS/TRACKED_ENTITIES.md` to keep the entity register in sync.

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
