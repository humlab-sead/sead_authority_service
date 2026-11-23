# Fuzzy Reconciliation for Classifier Entities: Phase 3 Task Plan

## Phase Summary

**Phase:** 3, Expand the Closed Inventory and Validate Release Inputs. **Readiness:** Validated for implementation against the current Phase 1/2 worktree. [Proposal](CLASSIFIER_FUZZY_RECONCILIATION.md) | [Phase plan](CLASSIFIER_FUZZY_RECONCILIATION_PHASE_PLAN.md#phase-3-expand-the-closed-inventory-and-validate-release-inputs) | [Phase 2 task plan](CLASSIFIER_FUZZY_RECONCILIATION_PHASE_2_TASK_PLAN.md).

**Goal:** Enable the approved tier-1 classifier inventory and verify schema, application/test/container configuration, and reconciliation behavior without deploying.

**Dependencies and constraints:** The [issue #43 interim register](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123) records 45 planned generic keys and eight exclusions. Read-only checks on 2026-11-14 through the `SEAD TNG (9023)` profile's `sead_staging` database show only `rdb_code` passes both population gates; the separate `SEAD Staging (5433)` profile was unavailable. The named decision is to leave the other three code-label types at zero weight. Recheck `rdb_code` against its generated view before merge. Phase 2's implementation is uncommitted; preserve it and verify its tests before extending it. If physical schema or repository state conflicts with the recorded inventory, stop and report rather than changing the approved set silently.

**Phase criteria**

1. [x] `PH3-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-9`): Approved generic keys appear in both manifest lists, marker and key lists agree, and excluded classifiers are not generically registered and have recorded reasons.
2. [x] `PH3-AC-2` (from `P-AC-4`, `P-AC-5`, `P-AC-14`): Only `rdb_code` uses non-zero description weight after passing the population gate; the other three code-label classifiers stay at zero weight. Description-only hits never auto-match and exact label matches retain priority. Verified against a disposable schema on 2026-11-14.
3. [x] `PH3-AC-3` (from `P-AC-7`, `P-AC-11`, `P-AC-12`, `P-AC-16`): Generated details and fuzzy queries work for every marked type, unmarked contracts remain unchanged, and container classifier/threshold configuration matches application configuration. Verified against a disposable schema and over HTTP on 2026-11-14.

## Repository Findings

**Repository basis:** `dev` at `9df7b7c`, inspected 2026-11-14 with uncommitted Phase 1 and Phase 2 changes considered. Graphify was queried through `~/.local/bin/graphify` because `.venv/bin/graphify` is absent; the findings below were checked against files and tests. Baseline: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_generate_entity_schema.py tests/strategies/test_configured_classifier.py tests/test_metadata.py tests/configuration/test_setup.py -q` passed, 55 tests (with FastAPI startup deprecation warnings). This baseline covers only the two reference types, not Phase 3's inventory or live-data gate.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `src/strategies/configured_classifier.py::CLASSIFIER_KEYS`, `validate_classifier_configuration`, `src/metadata.py::_get_supported_types` | Only `data_type` and `feature_type` are statically registered as generic; startup checks markers against keys and the manifest derives support from registration metadata. | Expand the tuple and marked specs together; check both manifest lists against the approved set, without replacing `Strategies.items`. |
| `config/entities.yml`, `tests/config/entities.yml`, `deployment/container/config/entities.yml`, `tests/config/config.yml::table_specs` | The two reference types are marked in each effective configuration. `relative_age_type` exists in the entity files, but `age_type`, `rdb_code`, and `value_qualifier` have no entries there. The test configuration has inline table specs. | Add verified table specs, preserve existing names/IDs, and synchronize all four configuration paths. |
| `sead_shape_shifter/resources/target_models/sead_standard_model.yml`, read-only staging catalog | The 53 classifier entries yield 45 planned generic keys after eight documented exclusions. All four proposed code-label columns and the physical `tbl_dating_uncertainty.description` column exist on the checked staging schema; the model omits the latter. | Preserve `dating_uncertainty.description` for this schema; verify physical tables/columns before generating each remaining view. The model is not a runtime dependency. |
| `schema/templates/entity.sql.jinja2`, `src/scripts/generate_entity_schema.py`, `tests/test_generate_entity_schema.py` | The marked branch and focused generator tests exist; the generator accepts `--all-entities`, `--force`, and `--output-dir`. Unmarked `site`, `method`, and `location` render identically to tracked SQL in the current tests. | Regenerate approved marked SQL only, compare all other generated output, and test the positive-weight SQL contract. |
| `src/utility.py::build_classifier_details_sql`, `src/strategies/configured_classifier.py::ConfiguredClassifierStrategy`, `tests/strategies/test_configured_classifier.py` | Marked details SQL uses generated aliases; candidate conversion uses label evidence for `match`, caps descriptions at 500 characters, and suppresses duplicate-label matches. | Expand tests across missing-description, scored-description, name-only, code-label, and duplicate-label classes without changing specialized strategies. |
| [Issue #43 interim register](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123), proposal population-gate section | The issue comment records the 45/8 inventory. Read-only `sead_staging` source-table counts on 2026-11-14 were: `age_type` 1/1 described, 1 label/1 description; `relative_age_type` 10/14, 14/10; `rdb_code` 27/27, 20/27; `value_qualifier` 13/13, 13/13. Only `rdb_code` passes both gates. Three generated views were not installed. | Enable only `rdb_code`; retain the other three as label-only and recheck the weighted entity against generated-view results before merge. |

## Scope

**In scope:** The approved tier-1 marker/key inventory, test and mounted container configuration, generated SQL artifacts, the `rdb_code` opt-in weight, interim issue #43 exclusion register, manifest and startup checks, disposable-schema and representative reconciliation tests, and release-order guidance.

**Out of scope:** `dimension` (tier 2), specialized registrations and SQL, alternate-identity matching, production data changes, and deployment. Keep `sampling_context` details and unmarked `site`/`method` contracts unchanged. Preserve existing type IDs and the schema-then-runtime-configuration-then-application-code order.

## Work Breakdown

### Area 1: Resolve Inventory and Data Gates

**Objective:** Establish an approved closed key list and recorded eligibility for each proposed positive description weight.

**Affected sources:** [Issue #43 interim register](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123), `sead_shape_shifter/resources/target_models/sead_standard_model.yml`, `config/entities.yml`, and read-only staging source tables.

**Dependencies:** The approved interim issue comment and read-only source-table counts are recorded. The `rdb_code` generated-view recheck belongs to Area 3; no production schema deployment is required to begin implementation.

- [x] `T1.1` **Change:** Record the approved tier-1 keys and reasons for each excluded classifier in the issue #43 interim inventory register.
  - **Target:** [Issue #43 interim register](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123); the checked-in register proposed by the issue remains a separate follow-up.
  - **Current -> required:** Only two generic keys are registered locally -> the comment records 45 planned generic keys and the eight excluded model entities with reasons; `coordinate_method_dimension`, `value_qualifier_symbol`, `abundance_element_group`, specialized types, and `dimension` remain outside the generic list.
  - **Implementation:** Compare the register with the target-model classifier snapshot and existing strategies. Do not add a per-entity Python class or resource file. Stop for a decision if the approved set differs from the proposal's tier-1 inventory.
  - **Validation:** `V-1`; compare all exclusions and keys, including no-table and no-usable-label cases.
- [x] `T1.2` **Change:** Record read-only population results and a pass/fail decision for each of the four code-label entities.
  - **Target:** The [proposal's population record](CLASSIFIER_FUZZY_RECONCILIATION.md#which-entities-enable-it); read-only physical tables `public.tbl_age_types`, `public.tbl_relative_age_types`, `public.tbl_rdb_codes`, and `public.tbl_value_qualifiers` where three generated views are not yet installed.
  - **Current -> required:** The dated staging counts show one pass (`rdb_code`) and three failures -> keep only `rdb_code` eligible for positive weight; retain the other three generic keys at zero weight.
  - **Implementation:** The same physical label/description columns as the planned generated views supplied the four-column aggregates. Require rows > 0, `with_description > 0.8 * rows`, and `distinct_descriptions > distinct_labels`. Recheck `rdb_code` against its generated view before merge; a changed result blocks its weight and requires a new decision.
  - **Validation:** `V-2`, `V-4`; review four dated results and the generated-view recheck.

**Completion evidence:** The issue comment records the 45 planned keys and eight exclusions; the proposal records four staging counts and the approved single-weight decision. The generated-view recheck remains a release validation, not an unrecorded planning decision.

### Area 2: Expand Matched Configuration and Generated SQL

**Objective:** Mark and register exactly the approved set, with only `rdb_code` description scored.

**Affected code:** `src/strategies/configured_classifier.py::CLASSIFIER_KEYS`, `config/entities.yml`, `tests/config/entities.yml`, `tests/config/config.yml::table_specs`, `deployment/container/config/entities.yml`, `schema/generated/` (generated SQL for approved keys), `tests/test_generate_entity_schema.py`, `tests/configuration/test_setup.py`.

**Dependencies:** Area 1, plus Phase 1/2 contracts and physical-column verification.

- [x] `T2.1` **Change:** Expand and validate the closed marked-key inventory in every loaded configuration.
  - **Target:** The four configuration files above; `src/strategies/configured_classifier.py::CLASSIFIER_KEYS`; `tests/test_generate_entity_schema.py` and `tests/configuration/test_setup.py`.
  - **Current -> required:** Two marked keys -> approved keys match the static tuple in both directions across app, test, and mounted container specs. Add the missing `age_type`, `rdb_code`, and `value_qualifier` specs only after confirming physical columns; preserve the existing `relative_age_type` ID/label/description spec.
  - **Implementation:** Keep specialized and excluded types unmarked; the staging `tbl_dating_uncertainty.description` column exists, so retain the current description spec there and verify the target schema before exposing it. Assert marker/key equality, inverse drift failures, and named startup failure for a missing/misconfigured approved key. Do not import config during static registration.
  - **Validation:** `V-1`, `V-3`; include missing-key and extra-marker negative cases.
- [x] `T2.2` **Change:** Apply positive description weight only to `rdb_code`; regenerate marked SQL.
  - **Target:** The application, test, and container entity specs above; generated SQL files under `schema/generated/` for the approved keys; `tests/test_generate_entity_schema.py`.
  - **Current -> required:** No production description weights -> `rdb_code` alone uses a non-zero weight between `0.10` and `0.20`; all other marked keys, including the three failed code-label types, remain at zero or omit it. Stop if its generated-view recheck fails the gate.
  - **Implementation:** Render with `src/scripts/generate_entity_schema.py --all-entities --force --output-dir` into a temporary directory, inspect generated diffs, then generate intended artifacts. Preserve unmarked view/function text; assert zero-weight types have no description scoring predicate or index and enabled types use `strict_word_similarity` and explicit thresholds.
  - **Validation:** `V-2`, `V-3`, `V-4`; compare tracked `site`/`method` SQL and the rendered approved inventory.

**Completion evidence:** Marker, tuple, runtime configurations, and generated SQL agree; no unsupported type is published. Verified 2026-11-14: 45 approved keys are marked in `config/entities.yml`, `tests/config/entities.yml`, `deployment/container/config/entities.yml`, and the inline test `table_specs`; only `rdb_code` carries `description_match_weight: 0.15`; 57 generated SQL files render from the template, and every unmarked entity keeps its tracked SQL text.

### Area 3: Verify Runtime and Release Inputs

**Objective:** Demonstrate every marked details/fuzzy contract and representative reconciliation behavior without deployment.

**Affected code and documentation:** `tests/strategies/test_configured_classifier.py`, `tests/test_metadata.py`, `tests/api/test_router.py`, `tests/test_generate_entity_schema.py`, `docs/OPERATIONS.md`; generated artifacts under `schema/generated/` are validation inputs.

**Dependencies:** Area 2, disposable schema with the generated SQL, and synchronized application/test/container configuration.

- [x] `T3.1` **Change:** Extend classifier tests and run a disposable-schema query matrix.
  - **Target:** The four test files above; `src/metadata.py::get_reconciliation_metadata`, `src/utility.py::build_classifier_details_sql`, and `src/strategies/configured_classifier.py::ConfiguredClassifierStrategy` are existing consumers to exercise, not assumed refactor targets.
  - **Current -> required:** Reference-only checks -> every marked type returns fuzzy candidates and details against its generated view; manifest `defaultTypes` and `supportedTypes` include each approved key once and exclude disallowed keys.
  - **Implementation:** For each approved key, use a known label and ID from the disposable schema, check function return columns and `ID`/`Name`/full `Description` where configured. Exercise HTTP requests for name-only, descriptive-name, code-label, description-only, duplicate normalized label, and 500/501-character description cases. Keep `sampling_context` and specialized manifest behavior unchanged.
  - **Validation:** `V-3`, `V-4`, `V-5`; assert exact-label priority, label-only `match`, and duplicate-label suppression.
- [x] `T3.2` **Change:** Record deployment-input parity and release order without deploying.
  - **Target:** `docs/OPERATIONS.md` release guidance; `config/config.yml`, `tests/config/config.yml`, `deployment/container/config/config.yml` thresholds; the three entity config files and inline test table specs.
  - **Current -> required:** Phase 2 threshold values are aligned -> verify thresholds and all approved specs stay aligned after expansion; state schema, then mounted configuration, then application code as the release order and explicitly prohibit silent reliance on `pg_trgm.*` settings.
  - **Implementation:** Compare parsed YAML rather than text, report any mismatches and correct only intended config drift. Do not deploy or write production data.
  - **Validation:** `V-3`, `V-6`; record all checked inputs and the release-order guidance.

**Completion evidence:** Complete disposable-schema matrix, representative HTTP tests, unchanged unmarked SQL, and synchronized release inputs. Completed 2026-11-14: 45/45 marked types returned expected details and fuzzy rows on an ephemeral database, the `rdb_code` generated-view population recheck passed, and `POST /reconcile` returned the expected score and `match` flags for the four representative categories.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH3-AC-1` (`P-AC-1`, `P-AC-2`, `P-AC-9`) | `T1.1`, `T2.1`, `T3.1` | `V-1`, `V-3`, `V-5` | Approved marker/key equality, manifest membership, documented exclusions. |
| `PH3-AC-2` (`P-AC-4`, `P-AC-5`, `P-AC-14`) | `T1.2`, `T2.2`, `T3.1` | `V-2`, `V-4`, `V-5` | Four recorded decisions; only `rdb_code` passes and is weighted; label-only automatic matching. |
| `PH3-AC-3` (`P-AC-7`, `P-AC-11`, `P-AC-12`, `P-AC-16`) | `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-3`, `V-4`, `V-5`, `V-6` | All marked queries and details work; unmarked parity and mounted config parity hold. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Inventory, exclusion, marker/key drift; `tests/configuration/test_setup.py`, `tests/test_generate_entity_schema.py` | Compare the [issue #43 interim register](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123) with target-model classifier entries, `CLASSIFIER_KEYS`, and parsed YAML; run the focused pytest command below after extending tests. | `PH3-AC-1` | Both directions match; excluded keys remain outside generic registrations and have reasons. | Pass 2026-11-14: the register's 45 keys and eight exclusions match `CLASSIFIER_KEYS`, the 53 target-model classifier entries, and all four configuration paths. |
| `V-2` | Live-data population gate | Use the dated read-only physical-table aggregates recorded in the proposal; recheck weighted `rdb_code` against its generated view during `V-4`. | `PH3-AC-2` | Only `rdb_code` passes both gates; other three remain at zero weight. | Pass 2026-11-14: source-table counts, the single-weight decision, and zero weights on the other three keys hold. Generated-view recheck passed in the disposable schema, where `authority.rdb_code` returned 27 rows, 27 described, 20 distinct labels, and 27 distinct descriptions. |
| `V-3` | Config and generator parity; `tests/test_generate_entity_schema.py`, `tests/configuration/test_setup.py` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_generate_entity_schema.py tests/configuration/test_setup.py -q`; compare temporary generator output with tracked SQL. | `PH3-AC-1`, `PH3-AC-3` | All marked artifacts agree, named startup failures for drift, unmarked `site`/`method` unchanged. | Pass 2026-11-14: focused tests pass; temporary generator output matches tracked SQL; unmarked `site`, `method`, and `location` render byte-identical SQL. |
| `V-4` | Generated SQL contract and disposable-schema details/fuzzy matrix | Run `.venv/bin/python src/scripts/generate_entity_schema.py --all-entities --force --output-dir "$OUTPUT_DIR"` with `OUTPUT_DIR` set to a disposable directory; apply generated SQL only in a disposable database and execute details and fuzzy queries for one known ID/label per approved type. Query the generated `authority.rdb_code` view for row/description/distinct-label/distinct-description counts before merge. | `PH3-AC-2`, `PH3-AC-3` | All queries succeed; `rdb_code` still passes both population gates and alone scores descriptions; no unmarked signature drift. | Pass 2026-11-14 on an ephemeral `postgres:17-alpine` database: all 45 marked files installed, details and fuzzy queries returned expected rows for 45/45 types, the `rdb_code` population gate passed (27/27/20/27), a description-only query scored `label_sim 0.0` with `name_sim 0.087`, zero-weight `age_type` returned nothing for that query, `label_threshold` changed candidate inclusion, and three `pg_trgm` settings at `0.99` left results unchanged. Generation into a temporary directory matched tracked files with differences only for approved keys. |
| `V-5` | Manifest and representative candidate/HTTP behavior; `tests/strategies/test_configured_classifier.py`, `tests/test_metadata.py`, `tests/api/test_router.py` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/strategies/test_configured_classifier.py tests/test_metadata.py tests/api/test_router.py -q`; run representative `POST /reconcile` against the disposable schema. | `PH3-AC-1`, `PH3-AC-2`, `PH3-AC-3` | Approved types in both lists; exact/description/duplicate/long-text cases have expected score and match flags. | Pass 2026-11-14: offline suite passes; the manifest published 56 `defaultTypes` and 53 `supportedTypes` with no excluded key; `POST /reconcile` returned 100/`match: true` for exact labels on name-only, name+description, and weighted code-label types; a `rdb_code` description-only query scored 8.68 with `match: false`; duplicate normalized labels returned two rows with no match; the 700-character description was truncated to 500 in candidates; and `GET /reconcile/preview` succeeded for 45/45 marked types. |
| `V-6` | Quality and release-input parity | `.venv/bin/ruff check src tests main.py`; `.venv/bin/black --check src tests main.py`; compare parsed application/test/container YAML and review `docs/OPERATIONS.md` release order. | `PH3-AC-3` | Checks pass; thresholds and marked specs align; guidance lists schema, config, code. | Pass 2026-11-14: ruff and black pass; thresholds and marked classifier specs agree across application, test, and container configuration; `docs/OPERATIONS.md` records the release order and `pg_trgm` independence. |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Approved inventory, exclusions, and population record | [Issue #43 interim register](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123) and [proposal population record](CLASSIFIER_FUZZY_RECONCILIATION.md#which-entities-enable-it) | `T1.1`, `T1.2` | Eight reasons, four dated count rows, and single-weight decision accessible for review. |
| Closed registrations and runtime/test/container specs | `src/strategies/configured_classifier.py`, `config/entities.yml`, `tests/config/entities.yml`, `tests/config/config.yml`, `deployment/container/config/entities.yml` | `T2.1`, `T2.2` | Approved set and only one eligible weight agree across all effective configs. |
| Generated classifier SQL | `schema/generated/` SQL files named by approved keys | `T2.2` | Rendered output equals tracked files; unchanged unmarked contracts. |
| Contract, startup, and HTTP coverage | `tests/test_generate_entity_schema.py`, `tests/configuration/test_setup.py`, `tests/strategies/test_configured_classifier.py`, `tests/test_metadata.py`, `tests/api/test_router.py` | `T2.1`, `T2.2`, `T3.1` | `V-3`, `V-4`, and `V-5` pass on the expanded set, including the disposable-schema matrix and representative HTTP behavior. |
| Release-input guidance | `docs/OPERATIONS.md` | `T3.2` | Release order and config parity recorded; no deployment. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1 | Done | None | `T1.1` and `T1.2` complete; source-table population gate recorded, with generated-view recheck in `V-4`. |
| Area 2 | Done | Area 1 | 45 approved keys are marked and registered; only `rdb_code` is weighted; generated SQL regenerated. |
| Area 3 | Done | Area 2 | Tests, disposable-schema matrix, representative HTTP behavior, static column checks, configuration parity, and release guidance are complete. |

## Definition Of Done

- [x] The interim inventory and four population results are recorded; `P-AC-14` and `PH3-AC-2` now require only `rdb_code` to pass. Its generated-view recheck passed under `V-4`.
- [x] `PH3-AC-1`, `PH3-AC-2`, and `PH3-AC-3` have task and validation results (`V-1` through `V-6`).
- [x] Every marked type passes generated fuzzy/details checks and representative HTTP behavior; specialized and unmarked regressions pass.
- [x] Application, test, and mounted container configuration and generated artifacts agree; release order is documented without deploying.
- [x] Deviations and remaining decisions are recorded. If repository state differs from this plan during implementation, stop and report the discrepancy rather than broadening the design.

## Risks And Open Questions

- The [issue #43 interim comment](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123) records the approved snapshot. Its proposed checked-in generated register is separate work; keep API status in registration metadata.
- The source-table counts are a planning gate, not proof that generated SQL works. `rdb_code` must still pass the generated-view population check before merge; if it fails, stop and seek a new decision.
- The model omits `dating_uncertainty.description` while the checked staging table has it. Do not delete the configured column on this evidence; verify each deployment target's physical schema before marking the entity.
- Execution note 2026-11-14: `authority.rdb_code` and the other newly marked views are not installed in the read-only `sead_staging` snapshot, so the database checks ran on an ephemeral `postgres:17-alpine` container instead. That container held only the `authority` schema objects the marked SQL needs (`unaccent`, `pg_trgm`, `authority.immutable_unaccent`) plus generated base tables. The 44 unweighted classifiers used seeded rows; `rdb_code` used 27 rows exported read-only from `public.tbl_rdb_codes`. No SEAD database received writes, and PostGIS was not required.