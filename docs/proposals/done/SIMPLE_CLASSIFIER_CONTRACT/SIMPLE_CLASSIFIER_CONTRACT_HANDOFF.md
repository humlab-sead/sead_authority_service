# One Contract for Simple Classifiers — Enabling a Type

## Purpose

How to make one `reconciliation: simple` entity servable through record selection, and where to look when it does not work. This is operator guidance for the contract defined in [SIMPLE_CLASSIFIER_CONTRACT.md](./SIMPLE_CLASSIFIER_CONTRACT.md); it does not change any decision recorded there.

## Current State

- Phase 1 is implemented and validated on branch `refactor-simple-reconciliation-logic`. See [SIMPLE_CLASSIFIER_CONTRACT_PHASE_1_TASK_PLAN.md](./SIMPLE_CLASSIFIER_CONTRACT_PHASE_1_TASK_PLAN.md).
- No Python module names an individual simple classifier. A type is served from three inputs only: its marked `table_specs` entry, the generated `authority.<type>` and `authority.fuzzy_<type>` objects, and its `options:record_selection:types` entry.
- The shipped `config/config.yml` lists all 46 simple classifiers with every capability off. It is an inventory, not an enablement.
- `schema/generated/` and `schema/__deploy__.sql` are current. The bundle was applied to a disposable database and passed, but nothing is deployed to a real environment.

## Completed Work

- Uniform generated contract: every simple view exposes `description`, and every four-argument function returns `<id_column>, label, description, label_sim, name_sim`.
- Record selection, discovery, and classifier registration are derived from configuration.
- `country` is declared once, in `config/entities.yml`, and served by `authority.country`.
- Startup validates every marked spec, whether or not its capabilities are enabled.

## Key References

| Topic | Document |
|---|---|
| The three requirements, capability settings, and rollout gate | [docs/OPERATIONS.md](../../../OPERATIONS.md), section *Record selection* |
| Schema, configuration, and code release order | [docs/OPERATIONS.md](../../../OPERATIONS.md), section *Classifier schema, configuration, and code release order* |
| Design decisions and their reasons | [SIMPLE_CLASSIFIER_CONTRACT.md](./SIMPLE_CLASSIFIER_CONTRACT.md) |
| Minimal working spec to copy | `config/entities.yml`, the `country` entry |
| Validation and registration | `src/strategies/configured_classifier.py`, `initialize_classifiers()` |
| Which types can be served | `src/record_selection.py`, `selectable_types()` |

## Next Actions

To enable one entity `abc`, do these in order. Steps 1 and 2 can land before step 3, but step 4 must come last.

### 1. Declare the entity as a simple classifier

Add the entry to `config/entities.yml`:

```yaml
abc:
  name: "Abc"                 # optional; defaults to the key in title case
  table_name: "tbl_abcs"
  id_column: "abc_id"
  label_column: "abc_name"
  description_column: null    # optional; the view emits null::text when absent
  reconciliation: simple
  where_clause: "abc_active = true"  # optional; applies to the generated view
```

The `country` entry does the same thing over a subset of `tbl_locations`, which is a useful copy source.

Startup rejects a marked spec that has no `id_column` or `label_column`, that declares `properties` or `property_settings`, or that sets `description_match_weight` above 0 without a `description_column`. Validation runs whether or not the type is enabled, so a spec mistake fails startup even while every switch is off.

### 2. Generate the SQL and rebuild the deploy bundle

```bash
make generate-schema          # creates schema/generated/abc.sql for a new entity
make generate-schema-bundle   # rebuilds schema/__deploy__.sql from existing files
```

`make generate-schema` skips a file that already exists. If the entity was already marked and you changed its spec, use `make generate-schema-force` instead, then rebuild the bundle. Do not run bare `./schema/create_schema.sh` for this: it deletes `schema/generated/` before regenerating.

### 3. Apply the schema

`authority.abc` and `authority.fuzzy_abc` must exist in the target database before the routes can answer. Apply the rebuilt bundle through the normal deployment process. The release order is schema first, then configuration, then the application image.

### 4. Enable one capability

Edit `config/config.yml`, then restart the service. Configuration is read at startup, so a restart is required.

```yaml
options:
  record_selection:
    types:
      abc:
        browse_supported: true
        search_supported: false
        details_supported: false
        identifier_search_supported: false
        export_verification_supported: false
```

| Setting | Enables |
|---|---|
| `browse_supported` | `GET /records/abc`, the complete list |
| `search_supported` | `POST /reconcile` with `X-Record-Selection: interactive` |
| `details_supported` | `GET /records/abc/details?id=<record URI>` |
| `identifier_search_supported` | `GET /records/abc/details?target_id=<integer>` |
| `export_verification_supported` | `POST /reconcile/verify-candidates` |

The last two are easy to mix up: `details_supported` covers lookup by URI under `options:id_base`, while `identifier_search_supported` covers lookup by bare numeric `target_id`.

### 5. Verify

```bash
curl -s http://localhost:8000/records/types | jq '.types[] | select(.type=="abc")'
```

The entry should report the one capability you enabled, and `null` for the limits attached to capabilities you left off. Then call the endpoint for that capability once and confirm it returns records rather than an error.

### When it does not work

| Symptom | Cause |
|---|---|
| Startup fails with `enables unsupported type 'abc'` | The key is enabled but has no `reconciliation: simple` spec |
| Startup fails with `Classifier 'abc' must declare a non-empty text 'label_column'` (or `id_column`) | Incomplete spec |
| `422 unsupported_capability` | The capability is off for that type |
| `422 unsupported_type` | The key is not a marked simple spec |
| `503 database_unavailable` | Usual cause is that `authority.abc` or `authority.fuzzy_abc` is missing from the database |
| `409 too_large_to_browse` | The list exceeds `browse_max_rows` or `browse_max_bytes` |

## Risks

- Do not enable a capability on a deployment until the rollout gate in [docs/OPERATIONS.md](../../../OPERATIONS.md) is met: Phase 4 records the exact Authority image and contract, and for interactive search, 100 warm searches per type are measured through the Shape Shifter backend at p95 ≤ 2000 ms. A failed measurement leaves only that capability and type disabled.
- Enablement before schema deployment produces confusing `503 database_unavailable` responses rather than an obvious configuration error.
- The deploy bundle expects the SEAD prerequisites to exist already: the `sead_utility` schema with `table_columns`, the `humlab_admin` role, and the `public.tbl_*` base tables. This predates the contract work and applies to every deployment.

## Open Decisions

- Which of the 46 types to enable, in what order, and when. This is a rollout decision, not a code constraint.
- Whether `administrative_region` joins the simple contract or stays a dedicated strategy. It is deliberately out of Phase 1.

## Suggested Follow-Up Documents

- A rollout plan naming the types to enable per environment and the measurement record for the interactive-search gate.
- An operations note for `administrative_region` once its outcome is decided.
