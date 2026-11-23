# One Contract for Simple Classifiers — Phase 1 Task Plan

## Phase Summary

**Phase.** Phase 1, "One contract, one selection path", from [SIMPLE_CLASSIFIER_CONTRACT_PHASE_PLAN.md](./SIMPLE_CLASSIFIER_CONTRACT_PHASE_PLAN.md).

**Goal.** Make the generated `authority.<key>` view and `authority.fuzzy_<key>` function the complete definition of a `reconciliation: simple` entity, then derive record selection and classifier registration from `table_specs`.

**Readiness: Validated.** The one blocking decision is settled and then closed out: the snapshot question was answered by skipping the two drift guards during implementation, and `make generate-schema-force` has since regenerated `schema/generated/` in-repo, so both guards are restored and passing. See Risks And Open Questions, item 1. Everything below is repository-verified and executable.

**Constraints.**

- `schema/generated/` was regenerated in-repo with `make generate-schema-force`, and `schema/__deploy__.sql` was rebuilt with `schema/create_schema.sh`; deploying either is still outside this phase.
- `description` is nullable and always present; `label_sim` stays in the uniform result.
- Discovery lists only configured types.
- Validation is unconditional.
- Keep record selection read-only, the 500-result interactive cap, and the `site` verification path through SIMS policy.

**Dependencies.** Accepted [SIMPLE_CLASSIFIER_CONTRACT.md](./SIMPLE_CLASSIFIER_CONTRACT.md); the snapshot question is resolved.

**Acceptance criteria.**

1. `PH1-AC-1` Rendering produces the same view columns and the same four-parameter function returning `<id_column>, label, description, label_sim, name_sim` for a spec with and without a `description_column`; non-simple entities keep current output.
2. `PH1-AC-2` No runtime dispatch, registration list, or projection map names an individual simple classifier.
3. `PH1-AC-3` Enabling a simple classifier needs only its `options:record_selection:types` entry and the generated objects.
4. `PH1-AC-4` `GET /records/types` lists exactly the configured types, with limits, fields, and filters derived from the spec.
5. `PH1-AC-5` A configured key that is not a valid simple spec fails startup; a configured simple key with its switch off returns `unsupported_capability`.
6. `PH1-AC-6` `country` reads the tracked `location_type_id` subset through the generated objects, with reviewed differences covered by comparison tests.
7. `PH1-AC-7` A simple spec declaring OpenRefine property mappings fails validation, and simple types publish no properties.
8. `PH1-AC-8` `site` candidate verification and match readiness are unchanged.

## Repository Findings

**Repository basis:** branch `refactor-simple-reconciliation-logic`, commit `3cd1e6d`. Planning date 2026-11-21. Uncommitted changes present: `config/config.yml` (enables both pilot types, `browse_max_rows: 1000`) and `docs/proposals/README.md`; the proposal folder is untracked. Those changes were treated as current state for planning but are not part of this phase.

| Evidence | Finding | Planning implication |
|---|---|---|
| `schema/templates/entity.sql.jinja2` | `description`/`norm_description` are emitted only when `description_column` is set; `label_sim` is returned only in the `description_match_weight > 0` branch. | Both must become unconditional for simple entities. |
| `src/utility.py::build_classifier_details_sql`, `::build_classifier_prefix_sql`, `::classifier_view_columns` | Each branches on `table_spec.get("description_column")`. | Remove the branches once the view always has `description`. |
| `src/strategies/configured_classifier.py::validate_classifier_configuration` | Validates `CLASSIFIER_KEYS` bidirectionally; `_register_configured_classifiers()` runs at import. | Replace with marked-spec iteration and one entry point. |
| `src/record_selection.py` | `PILOT_TYPES`, `_PROJECTION_BUILDERS`, `_DISPLAY_FIELDS`, `_text_filter_fields`, `_field_filters`, `search_interactive`, `COUNTRY_FUZZY_SQL`, `COUNTRY_LOCATION_TYPE_IDS`. | All must be replaced by spec-derived equivalents. |
| `src/api/candidate_verification.py` | Imports `PILOT_TYPES` for membership. | Ask the policy instead. |
| `src/api/router.py` | Imports eleven symbols from `src.record_selection`; `get_config_dependency()` calls both validators. | Function names used by the router must survive, and the config dependency must call the new entry point. |
| `main.py::startup` | Calls `validate_classifier_configuration()` then `validate_record_selection_configuration()`. | Call the single entry point instead. |
| `config/entities.yml` | 45 specs declare `reconciliation: simple`; none declares `properties`, `filter_params`, `where_clause`, or `alternate_identity_column`. | Validation rules confirm current practice rather than change it. |
| `config/entities.yml` | No `country` spec exists; `location` has `filter_params` for `location_type_ids`. | Add a `country` spec. |
| `tests/config/config.yml` | Inline `table_specs` has no `country` entry, yet record-selection tests configure `country`. | Add a `country` entry to the test fixture. |
| `sead-tools/authority-service.sead.se/container/config/entities.yml` | No `country` spec, while the sibling `config.yml` enables all five `country` switches. | Add the spec, or that deployment config fails startup under the new rule. |
| `tests/test_generate_entity_schema.py::test_generated_classifier_sql_matches_tracked_output`, `::test_marked_reference_entities_render_tracked_sql` | Assert rendered output equals checked-in snapshots; both pass today. | These fail as soon as the template changes, unless snapshots are regenerated. Blocking decision. |
| `tests/test_generate_entity_schema.py::test_marked_entity_without_description_keeps_three_return_columns`, `::test_weighted_and_zero_weight_classifier_contracts_differ` | Assert the current conditional shape, including absence of `label_sim` when weight is zero. | Must be rewritten to the new uniform contract. |
| `tests/api/test_record_selection.py::test_country_list_filters_to_country_locations` | Asserts the emitted SQL contains `authority.location` and `location_type_id = 1`. | Becomes `authority.country`; the where clause moves into the view. |
| `tests/api/test_record_selection.py::test_country_search_uses_country_scoped_fuzzy_function` | Asserts `fuzzy_location` and `location_type_ids == [1]`. | Becomes `fuzzy_country` with threshold parameters. |
| `tests/strategies/test_administrative_region.py` | Imports `CountryReconciliationStrategy` from `src.strategies.country`. | Must change when that module is deleted. |
| `tests/test_metadata.py`, `tests/strategies/test_configured_classifier.py`, `tests/configuration/test_setup.py`, `tests/test_generate_entity_schema.py` | Import `CLASSIFIER_KEYS`. | All four must switch to a config-derived source. |
| `tests/configuration/test_setup.py::test_validate_classifier_configuration_rejects_invalid_config` | Includes the case `_add_unregistered_marked_key`, expecting "not declared in CLASSIFIER_KEYS". | Case must be removed with the bidirectional check. |
| `docs/OPERATIONS.md` | Record selection section states "Phase 1 adds … for `feature_type` and `country`" and documents the pilot enablement example. | Update to configuration-driven enablement. |

Baselines measured during planning: `tests/test_generate_entity_schema.py` 21 passed; `tests/api/test_record_selection.py`, `tests/strategies/test_configured_classifier.py`, `tests/configuration/test_setup.py`, `tests/test_metadata.py` 110 passed. Full suite and linting not run during planning.

## Scope

**In scope.** The generator template and the SQL helpers that mirror its shape; the `country` spec in the three configuration copies that matter here; validation of the simple contract; record selection derived from specs; candidate verification membership; one classifier initialization entry point and its two call sites; the tests and the `docs/OPERATIONS.md` section that describe this behaviour; the regenerated `schema/generated/` snapshots including the new `schema/generated/country.sql`; and the rebuilt `schema/__deploy__.sql`.

**Out of scope.** Deploying schema to any real database; `administrative_region`; complex strategies; candidate scoring and thresholds; SIMS behaviour; which types a deployment enables.

## Work Breakdown

### Area 1: Make the generated contract uniform

**Objective:** Rendering the template for any simple spec yields the same view columns and the same function result type.

**Affected code:** `schema/templates/entity.sql.jinja2`, `src/utility.py`.

**Dependencies:** None.

**Tasks:**

- [x] `T1.1` **Change:** Emit `description` and `norm_description` for every simple entity, and return `<id_column>, label, description, label_sim, name_sim` from the four-parameter function in every simple branch.
  * **Target:** `schema/templates/entity.sql.jinja2`, the `reconciliation == "simple"` view and function blocks.
  * **Current → required:** `description`/`norm_description` appear only with `description_column`; the scored branch returns `label_sim` while the plain branch does not. Required: a `null::text as description` / `null::text as norm_description` fallback when the spec declares no description, and `label_sim` in both simple branches.
  * **Implementation:** In the view, when `entity.description_column` is falsy emit `null::text as description` and `null::text as norm_description`. In the plain scoring branch add `label_sim double precision` to the return list and select the same label expression already used for `name_sim`, so `label_sim = name_sim` there. Leave the scored branch, the description trigram index condition, and every non-simple branch untouched.
  * **Constraints:** Non-simple output must be byte-identical. `description_match_weight > 0` still requires a real column, enforced in Area 3.
  * **Validation:** `V-1`, `V-2`, `V-6`.

- [x] `T1.2` **Change:** Stop the classifier SQL helpers branching on description presence.
  * **Target:** `src/utility.py::build_classifier_details_sql`, `::build_classifier_prefix_sql`, `::classifier_view_columns`.
  * **Current → required:** `details_sql` and `prefix_find_sql` add `s.description` only when `description_column` is set; `classifier_view_columns` adds `description` only in that case. Required: always include `description`.
  * **Implementation:** Drop the `if table_spec.get("description_column")` guards; keep `details_columns` handling and the alias/source helpers unchanged.
  * **Constraints:** `details_columns` validation must keep rejecting a column the generated view does not expose. `build_classifier_specification` keeps `properties: []` and `property_settings: {}`.
  * **Validation:** `V-1`, `V-3`, `V-6`.

**Completion evidence:** A rendered spec without `description_column` and one with it differ only in the description source expression, not in the column list or the function result type.

### Area 2: Add the `country` spec to every configuration that needs it

**Objective:** `country` is describable as a simple classifier wherever it is enabled.

**Affected code:** `config/entities.yml`, `tests/config/config.yml`, `sead-tools/authority-service.sead.se/container/config/entities.yml`.

**Dependencies:** Area 1's contract, since the spec relies on a nullable description.

**Tasks:**

- [x] `T2.1` **Change:** Add a `country` spec over tracked location types.
  * **Target:** `config/entities.yml`, new `country` entry.
  * **Current → required:** No `country` spec; country behaviour lives in `src/resources/country.yml` and in Python. Required: `name`, `table_name: tbl_locations`, `id_column: location_id`, `label_column: location_name`, `description_column: null`, `reconciliation: simple`, `where_clause: "location_type_id = 1"`.
  * **Implementation:** Place the entry near `location` so the shared table is visible. Do not add `filter_params`, `joins`, or `extra_columns`.
  * **Constraints:** `tbl_locations` has no description column, so `description_column: null` is correct and the nullable view column supplies `description`.
  * **Validation:** `V-4`, `V-6`, `V-9`.

- [x] `T2.2` **Change:** Add the same `country` spec to the inline test `table_specs`.
  * **Target:** `tests/config/config.yml`, `table_specs` block.
  * **Current → required:** No `country` entry exists, while record-selection tests configure `country`. Required: an entry with the same five identifying fields, without `where_clause` if the tests assert emitted SQL against the projection.
  * **Implementation:** Keep `description_column: null` and mark `reconciliation: simple`. If a test asserts `where_clause` text in SQL, include the clause so the assertion stays meaningful.
  * **Constraints:** Other `table_specs` entries must not change; several tests assert the marked inventory.
  * **Validation:** `V-3`, `V-4`, `V-5`.

- [x] `T2.3` **Change:** Add the `country` spec to the deployment configuration copy.
  * **Target:** `sead-tools/authority-service.sead.se/container/config/entities.yml`.
  * **Current → required:** No `country` spec, while the sibling `config.yml` enables all five `country` capabilities. Under the new rule, a configured key that is not a valid simple spec fails startup, so that deployment would refuse to start.
  * **Implementation:** Mirror `T2.1`.
  * **Constraints:** This file is a deployment copy; keep it aligned with `config/entities.yml` for `country` only. Do not reformat the rest of the file.
  * **Validation:** `V-8`, `V-9`.

**Completion evidence:** `country` resolves as a simple classifier in the repository config, the test fixture, and the deployment copy.

### Area 3: One unconditional definition of a valid simple classifier

**Objective:** A malformed simple spec fails startup, and no spec can be registered for serving and then fail at request time.

**Affected code:** `src/strategies/configured_classifier.py::validate_classifier_configuration`.

**Dependencies:** Areas 1 and 2.

**Tasks:**

- [x] `T3.1` **Change:** Validate every marked spec, independent of `CLASSIFIER_KEYS` and record-selection switches, and reject the new contract violations.
  * **Target:** `src/strategies/configured_classifier.py::validate_classifier_configuration`.
  * **Current → required:** Iterates `CLASSIFIER_KEYS`, requires each marked key to be listed, and checks only column and threshold basics. Required: iterate the marked specs from `table_specs`, keep the existing `id_column`/`label_column`/`description_column` checks, and add rejections for `properties`, `property_settings`, and `description_match_weight > 0` without a `description_column`.
  * **Implementation:** Derive the key set the same way `marked_keys()` in the test module does. Keep the message text specific enough to name the offending key and field. Leave the `options:reconciliation` threshold checks unchanged.
  * **Constraints:** No warn-only path. The shipped configuration must still pass: no current spec declares `properties`, and only `rdb_code` sets a weight and it has a description column.
  * **Validation:** `V-6`, `V-2`.

**Completion evidence:** A spec with `properties`, or a weight without a description column, raises `ClassifierConfigurationError` naming the key.

### Area 4: Derive record selection from specs

**Objective:** Discovery, list, details, and interactive search work for any configured simple classifier without per-type code.

**Affected code:** `src/record_selection.py`, `src/api/candidate_verification.py`.

**Dependencies:** Areas 1–3.

**Tasks:**

- [x] `T4.1` **Change:** Replace the type tuple and projection maps with spec-derived functions.
  * **Target:** `src/record_selection.py`; remove `PILOT_TYPES`, `_PROJECTION_BUILDERS`, `_feature_type_projection`, `_country_projection`.
  * **Current → required:** Two hardcoded builders and a two-element tuple. Required: one builder that reads `table_specs.<key>` and returns table `authority.<key>`, the spec's `id_column` through the existing identifier check, `label_column="label"`, and `description_column="description"`, plus a helper listing selectable keys.
  * **Implementation:** Keep `RecordProjection` and the SQL builders. Replace `PILOT_TYPES` membership with a set derived from marked specs, and use it in `load_record_selection_policy`, `validate_record_selection_configuration`, and `discovery_types`. Preserve the current error for a configured key outside that set, keeping the "unsupported type" code.
  * **Constraints:** `RecordSelectionError` versus `RecordSelectionConfigurationError` semantics and status codes must not change. `browse_max_rows`, `browse_max_bytes`, and the 500 cap stay global.
  * **Validation:** `V-3`, `V-4`.

- [x] `T4.2` **Change:** Derive discovery metadata from the projection instead of `_DISPLAY_FIELDS` and the `feature_type` branches.
  * **Target:** `src/record_selection.py`; remove `_DISPLAY_FIELDS`, `_display_fields`, `_text_filter_fields`, `_field_filters`, `DisplayField`.
  * **Current → required:** A per-type tuple indexed directly, plus `if entity_type == "feature_type"` branches. Required: `name` and `target_id` always, and `description` in `display_fields`, `text_filter_fields`, and `field_filters` only when the spec declares a description column.
  * **Implementation:** Emit the same field names, labels, and filter operators the current output uses so the descriptor model validators continue to pass. Keep `SORT_FIELDS`.
  * **Constraints:** A missing map entry currently raises `KeyError`; the replacement must not have an equivalent failure mode.
  * **Validation:** `V-3`, `V-4`.

- [x] `T4.3` **Change:** Replace per-type search dispatch with one classifier path.
  * **Target:** `src/record_selection.py`; remove `_feature_type_candidates`, `_country_candidates`, `COUNTRY_FUZZY_SQL`, `COUNTRY_LOCATION_TYPE_IDS`.
  * **Current → required:** An `if`/`elif` over two keys and a literal SQL call. Required: resolve the registered strategy, call `find_candidates`, then `as_candidates`, and keep the existing post-filter that drops candidates whose URI does not parse back to the requested type.
  * **Implementation:** Keep `validate_interactive_query` unchanged, including the single-query rule and the `search_limit_exceeded` behaviour.
  * **Constraints:** Duplicate-label suppression and accent normalization now apply to `country`; this is the reviewed behaviour change from `P-AC-7`.
  * **Validation:** `V-3`, `V-4`.

- [x] `T4.4` **Change:** Take verification membership from the policy.
  * **Target:** `src/api/candidate_verification.py`; remove the `PILOT_TYPES` import.
  * **Current → required:** `item.type in PILOT_TYPES`. Required: membership in the loaded `RecordSelectionPolicy.types`.
  * **Implementation:** Leave the `site` branch and `_site_strategy` untouched.
  * **Constraints:** Order preservation and per-item outcomes must not change.
  * **Validation:** `V-9`.

**Completion evidence:** A simple classifier added only to `table_specs` and `options:record_selection:types` serves discovery, list, details, and search with no code naming it.

### Area 5: One initialization entry point, wiring, and removal of the duplicated country path

**Objective:** Classifier registration follows configuration, `country` has one declaration, and documentation matches.

**Affected code:** `src/strategies/configured_classifier.py`, `main.py`, `src/api/router.py`, `src/strategies/country.py` (delete), `src/resources/country.yml` (delete), `docs/OPERATIONS.md`, and the four test modules importing `CLASSIFIER_KEYS`.

**Dependencies:** Areas 1–4.

**Tasks:**

- [x] `T5.1` **Change:** Replace import-time registration and the static key tuple with one entry point.
  * **Target:** `src/strategies/configured_classifier.py`; remove `CLASSIFIER_KEYS` and `_register_configured_classifiers()`.
  * **Current → required:** Registration at import from a tuple. Required: `initialize_classifiers()` that validates then registers one dynamically named subclass per marked spec, using the existing `Strategies.register(..., support="supported")` call.
  * **Implementation:** Derive keys from `ConfigValue("table_specs")`. Keep registration idempotent. Keep `set_configured_specification_resolver` wired at import so `resolve_specification` works before initialization.
  * **Constraints:** `resolve_specification()` must still prefer `src/resources/<key>.yml`; that precedence is what `T5.3` depends on.
  * **Validation:** `V-5`, `V-7`.

- [x] `T5.2` **Change:** Call the entry point from both configuration entry paths.
  * **Target:** `main.py::startup`, `src/api/router.py::get_config_dependency`.
  * **Current → required:** Both call `validate_classifier_configuration()`. Required: both call `initialize_classifiers()` so a code path that first configures through the router dependency also registers classifiers.
  * **Implementation:** Keep `validate_record_selection_configuration()` after it.
  * **Constraints:** Scripts and tests that never call either path see no classifiers; that is the accepted contract and must be stated in the module docstring.
  * **Validation:** `V-5`, `V-8`, `V-10`.

- [x] `T5.3` **Change:** Remove the duplicated country path.
  * **Target:** delete `src/strategies/country.py` and `src/resources/country.yml`; update `tests/strategies/test_administrative_region.py`.
  * **Current → required:** A dedicated strategy module and a resource spec that overrides configuration. Required: `country` comes from the configured spec so `authority.fuzzy_country` is used.
  * **Implementation:** Delete both files. Rewrite the administrative-region assertion to compare registry keys without importing the deleted class.
  * **Constraints:** The resource file must be removed, not edited; leaving it would bypass the generated function.
  * **Validation:** `V-3`, `V-5`, `V-10`.

- [x] `T5.4` **Change:** Update the operator documentation.
  * **Target:** `docs/OPERATIONS.md`, "Record selection" section.
  * **Current → required:** States the feature covers `feature_type` and `country`. Required: states that any `reconciliation: simple` entity can be enabled, that the enablement example is spec-driven, and that `country` reads `authority.country` filtered by tracked location type.
  * **Implementation:** Keep the settings table and the rollout rule about the Phase 4 image and p95 measurement. Correct the country paragraph that names `fuzzy_location`.
  * **Constraints:** Do not describe the schema as already regenerated.
  * **Validation:** `V-12`.

**Completion evidence:** `grep` finds no per-type classifier key in `src/`, `country` has one declaration, and both configuration entry paths register classifiers.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` | `T1.1`, `T1.2` | `V-1`, `V-2`, `V-6` | Rendered view columns and function result type identical across specs with and without a description column; unmarked output unchanged |
| `PH1-AC-2` | `T4.1`, `T4.2`, `T4.3`, `T5.3` | `V-3`, `V-4` | No dispatch, registration list, or projection map names a simple classifier |
| `PH1-AC-3` | `T2.1`, `T4.1`, `T5.1` | `V-4` | Third simple entity works with only spec and switch changes |
| `PH1-AC-4` | `T4.2` | `V-3`, `V-4` | Discovery lists exactly the configured types with spec-derived fields and filters |
| `PH1-AC-5` | `T3.1`, `T4.1` | `V-6`, `V-3` | Startup error for an invalid configured spec; `unsupported_capability` for a disabled switch |
| `PH1-AC-6` | `T2.1`, `T4.3` | `V-3`, `V-9` | Country list, details, and search read `authority.country`; reviewed differences covered by tests |
| `PH1-AC-7` | `T1.2`, `T3.1` | `V-6`, `V-7` | Property mappings rejected; simple types publish no properties |
| `PH1-AC-8` | `T4.4` | `V-9` | `site` outcomes unchanged in a mixed batch |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Template contract for a spec with and without `description_column`, and with `description_match_weight` above zero | `uv run pytest tests/test_generate_entity_schema.py -q` with rewritten shape assertions | `PH1-AC-1` | View always exposes the five columns; function always returns the five result columns including `label_sim`; index only with a positive weight | Pass (21 tests) before change; assertions must be rewritten |
| `V-2` | Unmarked entities unchanged | `uv run pytest tests/test_generate_entity_schema.py -q -k unmarked` | `PH1-AC-1` | `site`, `method`, `location` render unchanged | Pass |
| `V-3` | Record selection suite | `uv run pytest tests/api/test_record_selection.py -q` | `PH1-AC-2`, `PH1-AC-4`, `PH1-AC-5`, `PH1-AC-6` | All pass after country SQL and search-parameter assertions are updated | Pass today; 2 country assertions must change |
| `V-4` | New third-entity proof | `NEW` test in `tests/api/test_record_selection.py` adding a third simple spec and one switch, then exercising discovery, list, details, and search | `PH1-AC-2`, `PH1-AC-3`, `PH1-AC-4` | All four surfaces work; no Python file names the key | Not run: test does not exist |
| `V-5` | Configured classifier and inventory tests | `uv run pytest tests/strategies/test_configured_classifier.py -q` | `PH1-AC-3` | Registration covers every marked spec, including `country`, after `initialize_classifiers()` | Pass today; `CLASSIFIER_KEYS` import must be replaced |
| `V-6` | Configuration validation | `uv run pytest tests/configuration/test_setup.py -q` | `PH1-AC-1`, `PH1-AC-5`, `PH1-AC-7` | New rejection cases pass; the `_add_unregistered_marked_key` case is removed | Pass today; case list must change |
| `V-7` | Manifest and default types | `uv run pytest tests/test_metadata.py -q` | `PH1-AC-7` | `supportedTypes` unchanged; simple types publish no properties | Pass today; `CLASSIFIER_KEYS` import must be replaced |
| `V-8` | Router and configuration dependency | `uv run pytest tests/api/test_router.py -q` | `PH1-AC-5` | Configuration errors still surface through the dependency; classification still registered | Pass today |
| `V-9` | Candidate verification, mixed batch | `uv run pytest tests/api/test_candidate_verification.py -q` | `PH1-AC-6`, `PH1-AC-8` | Site outcomes unchanged; pilot outcomes unchanged apart from the reviewed country differences | Pass today |
| `V-10` | Full unit suite | `uv run pytest tests -q` | Regression | Green with no unexplained skips beyond the pre-existing integration skips | Not run during planning |
| `V-11` | Style and static checks | `ruff check --no-cache src tests main.py` and `black --check src tests main.py` | Quality gate | No findings | Not run during planning |
| `V-12` | Documentation consistency | Manual read of `docs/OPERATIONS.md` against the enabled behaviour | `PH1-AC-6` | No claim of `feature_type`-only support and no stale `fuzzy_location` reference | Not run |

Manual method where a database is available: apply `schema/__deploy__.sql` in a disposable environment, then run a read-only integration check confirming `authority.fuzzy_country` resolves and country row counts match `location_type_id = 1`. Done: see the apply test in Execution Evidence.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Uniform template | `schema/templates/entity.sql.jinja2` | `T1.1` | Both specs render the same shape |
| Regenerated snapshots | `schema/generated/*.sql` (44 updated, `country.sql` added) | `T1.1`, `T2.1` | `make generate-schema-force` produced 58 files; both drift guards pass |
| Rebuilt deploy bundle | `schema/__deploy__.sql` | `T1.1`, `T2.1` | `schema/create_schema.sh` rebuilt it from 58 files; applied cleanly to a disposable PostGIS database |
| Unified SQL helpers | `src/utility.py` | `T1.2` | No description-presence branch remains |
| Country spec (3 copies) | `config/entities.yml`, `tests/config/config.yml`, `sead-tools/authority-service.sead.se/container/config/entities.yml` | `T2.1`, `T2.2`, `T2.3` | Startup passes with `country` enabled in each |
| Unconditional validation | `src/strategies/configured_classifier.py` | `T3.1` | Rejection cases pass |
| Spec-derived record selection | `src/record_selection.py` | `T4.1`, `T4.2`, `T4.3` | No per-type structure remains |
| Policy-based membership | `src/api/candidate_verification.py` | `T4.4` | No `PILOT_TYPES` import |
| Initialization entry point | `src/strategies/configured_classifier.py` | `T5.1` | `initialize_classifiers()` registers marked specs |
| Wired entry paths | `main.py`, `src/api/router.py` | `T5.2` | Both call the entry point |
| Removed duplication | `src/strategies/country.py` (delete), `src/resources/country.yml` (delete) | `T5.3` | `grep` finds neither |
| Updated tests | `tests/test_generate_entity_schema.py`, `tests/api/test_record_selection.py`, `tests/strategies/test_configured_classifier.py`, `tests/configuration/test_setup.py`, `tests/test_metadata.py`, `tests/strategies/test_administrative_region.py`, `NEW` third-entity test | `T1.1`, `T2.2`, `T3.1`, `T4.1`–`T4.4`, `T5.1`, `T5.3` | `V-1`–`V-10` green |
| Operator docs | `docs/OPERATIONS.md` | `T5.4` | Configuration-driven enablement described |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: uniform contract | Done | None | Drift guards restored after in-repo regeneration; unmarked output unchanged |
| Area 2: country specs | Done | Area 1 | All three configuration copies validate at startup |
| Area 3: validation | Done | Areas 1, 2 | Bidirectional key check removed; property and weight rejections added |
| Area 4: record selection | Done | Areas 1–3 | Third-entity proof added as `TestThirdSimpleClassifier` |
| Area 5: initialization and cleanup | Done | Areas 1–4 | `initialize_classifiers()` wired in `main.py` and the router dependency |

## Execution Evidence

Recorded 2026-11-21 on branch `refactor-simple-reconciliation-logic`. Executed with the repository `.venv` interpreter.

| Check | Command | Result |
|---|---|---|
| `V-1` | `.venv/bin/python -m pytest tests/test_generate_entity_schema.py` | Pass: 21 of 21, no skips. After `make generate-schema-force`, both drift guards compare rendered output against the regenerated snapshots and pass. The no-description spec asserts `null::text as description`, `null::text as norm_description`, and the five-column result |
| `V-2` | same module, `-k "unmarked or filter_parameters"` | Pass: `site`, `method`, `location` render byte-identical to the tracked snapshots |
| `V-3` | `.venv/bin/python -m pytest tests/api/test_record_selection.py` | Pass: 65 tests. Country list reads `authority.country` with no `location_type_id` predicate; country search uses `fuzzy_country` with the two threshold parameters |
| `V-4` | `TestThirdSimpleClassifier` in the same module | Pass: `data_type_group` serves discovery, list, details, and search with only an `options:record_selection:types` entry |
| `V-5` | `.venv/bin/python -m pytest tests/strategies/test_configured_classifier.py` | Pass: `initialize_classifiers()` registers every marked spec including `country` |
| `V-6` | `.venv/bin/python -m pytest tests/configuration/test_setup.py` | Pass: rejections cover blank `id_column`, blank `label_column`, unknown details column, `properties`, `property_settings`, and a weight without `description_column`. The enabled-but-unmarked case is asserted through `validate_record_selection_configuration` |
| `V-7` | `.venv/bin/python -m pytest tests/test_metadata.py` | Pass: `supportedTypes` unchanged for the dummy registry; every marked classifier is supported and published with no properties |
| `V-8` | `.venv/bin/python -m pytest tests/api/test_router.py` | Pass: configuration failures still surface through the dependency; discovery lists the selectable set |
| `V-9` | `.venv/bin/python -m pytest tests/api/test_candidate_verification.py` | Pass: `site` outcomes and ordering unchanged |
| `V-10` | `.venv/bin/python -m pytest tests` | Pass: 1336 passed, 50 skipped, 0 failed. The 50 skips are pre-existing integration and external-service skips |
| `V-11` | `.venv/bin/python -m ruff check --no-cache src tests main.py`; `.venv/bin/python -m black --check src tests main.py`; `.venv/bin/python -m pylint` on the changed modules | Pass: no findings, 10.00/10 |
| `V-12` | Manual read of `docs/OPERATIONS.md` | Pass: the record-selection section describes spec-driven enablement, `authority.country`, and `authority.fuzzy_country`, and names the bundle rebuild as the step that puts them in a database |

Startup smoke checks, both with `initialize_classifiers()` followed by `validate_record_selection_configuration()`:

- `config/config.yml` + `config/entities.yml`: 46 classifiers registered, `country` present with `fuzzy_country`, record selection validates for `country` and `feature_type`.
- `sead-tools/authority-service.sead.se/container/config/`: same 46 classifiers and the same record-selection result, so the deployment copy now starts with all five `country` capabilities enabled.

Deploy-bundle apply test, run after `bash schema/create_schema.sh`:

- Regeneration was byte-identical to the earlier `make generate-schema-force` output (`diff -r` reported no differences), so the script's `cleanup` step was safe.
- `schema/__deploy__.sql` grew from 3871 to 4233 lines and now references `authority.country` / `fuzzy_country`.
- Applied to a disposable `docker.io/postgis/postgis:17-3.4-alpine` database with `-v ON_ERROR_STOP=1`, after creating the SEAD prerequisites the bundle assumes exist (`sead_utility.table_columns`, the `humlab_admin` role, and the `public.tbl_*` base tables). Exit code 0.
- Functional checks in that database: the `authority.country` view returned only type-1 locations; `fuzzy_country` returned `location_id, label, description, label_sim, name_sim`; simple functions expose only the four-argument signature; `fuzzy_site` kept `(text, integer)` with three result columns; `fuzzy_location` kept its `integer[]` filter parameter; `fuzzy_rdb_code('ceramic', 5)` matched through description with `label_sim = 0, name_sim = 0.15`.

Note: the bundle needs `sead_utility.table_columns`, `humlab_admin`, and the `public.tbl_*` tables to exist before it runs. Those are database prerequisites that predate this change, not deliverables of this phase.

Acceptance criteria supported by that evidence: `PH1-AC-1` through `PH1-AC-7`. `PH1-AC-8` is supported by `V-9` (mixed-batch ordering and `site` outcomes unchanged) and by the untouched `src/api/candidate_verification.py::_site_strategy` path. `PH1-AC-6` is additionally supported by the apply test above.

Deviations from the plan, all inside the affected files:

- `tests/api/test_router.py::TestRecordSelectionDiscovery` also asserted the two-type discovery set and is updated to the selectable set, the same change required in `tests/api/test_record_selection.py`.
- `docs/OPERATIONS.md` grant checks and the release-order step referred to `authority.fuzzy_location(text,integer,integer[])` and `CLASSIFIER_KEYS` in sections outside "Record selection"; both were corrected because the referenced objects no longer exist.
- `validate_classifier_configuration()` now returns the validated keys so `initialize_classifiers()` can register from the same pass.
- The `country` test-fixture spec keeps `where_clause: "location_type_id = 1"` so the list assertion can prove the predicate moved into the view rather than into the query.

Regeneration landed after the tests were rewritten: `make generate-schema-force` produced 58 files, adding `schema/generated/country.sql` and updating all 44 previously marked classifier snapshots. `schema/generated/rdb_code.sql` is byte-identical because it already returned `description` and `label_sim`. `schema/__deploy__.sql` was then rebuilt with `schema/create_schema.sh`, which re-ran the generator (byte-identical output) and concatenated the 58 files into the bundle.

`schema/create_schema.sh` gained a `--bundle-only` option after this phase, because the default path deletes `schema/generated/` before regenerating and there was no way to rebuild only the bundle. `--bundle-only` rebuilds the bundle from the files on disk, refuses to run against an empty source folder instead of writing a bundle with no entity SQL, and is exposed as `make generate-schema-bundle`. Verified that it leaves `schema/generated/` untouched and reproduces the same bundle bytes, and that the default path and `--no-generate` are unchanged.

## Definition Of Done

- [x] Every acceptance criterion has implementation and validation evidence.
- [x] All five work areas and all deliverables are complete.
- [x] `uv run pytest tests -q`, `ruff check --no-cache src tests main.py`, and `black --check src tests main.py` pass.
- [x] Unmarked entity output is regression-tested as unchanged.
- [x] `site` verification and mixed-batch ordering are regression-tested.
- [x] The `country` spec exists in all three configuration copies, and the deployment copy starts.
- [x] No module in `src/` names an individual simple classifier for dispatch, registration, or projection.
- [x] The snapshot decision is recorded and the affected tests carry an explicit marker or reason. Superseded: the snapshots were regenerated in-repo, so both drift guards run again with no marker.
- [x] No unresolved question affects implementation, correctness, or validation. `schema/__deploy__.sql` is rebuilt and was applied cleanly to a disposable PostgreSQL 17 + PostGIS database; nothing is deployed to a real environment by this phase.

## Risks And Open Questions

1. **Closed: the template-versus-snapshot tests were skipped, then restored after in-repo regeneration.**
   `test_generated_classifier_sql_matches_tracked_output` and `test_marked_reference_entities_render_tracked_sql` assert rendered output equals `schema/generated/<key>.sql`. Changing the template made them fail while regeneration was external, so both carried `pytest.mark.skip` during implementation. `make generate-schema-force` then regenerated the snapshots in-repo, and both guards now run and pass with no marker. `test_weighted_and_zero_weight_classifier_contracts_differ` renders its own SQL rather than reading snapshots, so it was unaffected by the sequencing.

2. **Closed: the deployment configuration now has a `country` spec.** `sead-tools/authority-service.sead.se/container/config/config.yml` enables all five `country` capabilities, and its sibling `entities.yml` now carries the matching spec from `T2.3`. Startup was smoke-tested against that copy and passes, so `PH1-AC-5` keeps its unconditional validation.

3. **Closed: the deploy bundle is rebuilt and applies cleanly.** `schema/create_schema.sh` regenerated `schema/generated/` (byte-identical to the `make generate-schema-force` output) and rebuilt `schema/__deploy__.sql` from 58 files. The bundle was applied to a disposable PostgreSQL 17 + PostGIS 3.4 database with `ON_ERROR_STOP=1` and finished with exit 0. Verification in that database: `authority.country` returned only the `location_type_id = 1` rows; `fuzzy_country('sweden', 10)` returned the five columns with `label_sim = name_sim = 1`; `fuzzy_age_type`, `fuzzy_country`, and `fuzzy_rdb_code` each expose only the four-argument signature; `fuzzy_site` keeps `(text, integer)` and three result columns; `fuzzy_rdb_code('ceramic', 5)` matched on description alone with `label_sim = 0` and `name_sim = 0.15`. Deploying to a real database is still a release step, not part of this phase.

4. **Closed: test fixtures no longer depend on the removed key tuple.** `tests/config/config.yml` has a `country` spec, and `_classifier_config()` in `tests/configuration/test_setup.py` now derives its specs from the marked entries in that fixture instead of from `CLASSIFIER_KEYS`, so a stale fixture cannot silently pass validation.

5. **Closed: tooling calls the entry point explicitly.** After `T5.1`, a script that builds strategies without calling `initialize_classifiers()` sees an empty simple-classifier registry. Each affected test module now calls it before asserting, including `tests/api/test_record_selection.py`, whose `_set_selection` helper initializes classifiers so router tests exercise the real registry.
