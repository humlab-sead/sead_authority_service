# Fuzzy Reconciliation for Classifier Entities: Phase 2 Task Plan

## Phase Summary

**Phase:** 2, Connect the Shared Runtime and Reference Types. **Readiness:** Validated for implementation against the current Phase 1 worktree; preserve and verify its SQL contract before starting. [Proposal](CLASSIFIER_FUZZY_RECONCILIATION.md) | [Phase plan](CLASSIFIER_FUZZY_RECONCILIATION_PHASE_PLAN.md#phase-2-connect-the-shared-runtime-and-reference-types) | [Phase 1 task plan](CLASSIFIER_FUZZY_RECONCILIATION_PHASE_1_TASK_PLAN.md).

**Goal:** Reconcile `feature_type` and `data_type` through one configured strategy, with explicit support status and startup configuration checks. Phase 3 owns the remaining classifier inventory and description-scoring enablement.

**Phase criteria**

1. [x] `PH2-AC-1` (from `P-AC-2`, `P-AC-7`, `P-AC-8`): Both reference types use generic registration and generated details SQL without their redundant resource or strategy files; specialized details remain unchanged and `dimension` stays deferred.
2. [x] `PH2-AC-2` (from `P-AC-3`, `P-AC-5`, `P-AC-6`): Exact unique labels auto-match; duplicate normalized labels and description-only hits do not; candidate descriptions are capped at 500 characters and details remain full length.
3. [x] `PH2-AC-3` (from `P-AC-10`): Every registration declares a valid support status, the manifest uses those declarations, and an undeclared status fails validation.
4. [x] `PH2-AC-4` (from `P-AC-12`, `P-AC-16`): Invalid classifier specs or missing/out-of-range configured thresholds fail startup with a named error.

**Dependencies and constraints:** Phase 1's marked view/function contract and its verified unmarked parity are prerequisites. Its present edits are uncommitted; do not overwrite or discard them. Keep static registration and existing public type IDs; do not modify `dimension`, `sampling_context` details, other specialized queries, or unmarked generated SQL. No deployment or production data write is authorized.

## Repository Findings

**Repository basis:** `dev` at `9df7b7c`, checked 2026-11-14 with the uncommitted Phase 1 SQL template, threshold configuration, generator tests, and Phase 1 task plan included. Graphify was queried through `~/.local/bin/graphify` (the skill's `.venv/bin/graphify` path is absent); current source and tests below establish the findings. Focused baseline: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_generate_entity_schema.py tests/test_metadata.py tests/strategies/test_feature_type.py tests/configuration/test_setup.py -q` passed (41 tests).

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `schema/templates/entity.sql.jinja2`, `tests/test_generate_entity_schema.py`, `schema/generated/feature_type.sql`, `schema/generated/data_type.sql` | Phase 1's marked branch exists and has tests; the two tracked generated reference files still reflect unmarked specs. A marked function with description but zero weight returns `description` and `name_sim`, while a positively weighted one also returns `label_sim`. | Mark both reference specs with zero weight, regenerate only their intended SQL output, and do not require `label_sim` for zero-weight rows. Test positive-weight label-only matching with a synthetic marked spec or fixture; enabling production weights belongs to Phase 3. |
| `src/utility.py::resolve_specification`, `src/strategies/strategy.py::ReconciliationStrategy.__init__`, `src/strategies/query.py::BaseRepository` | String specifications resolve only resource YAML. `BaseRepository.find` passes two SQL arguments, and `get_details` needs `details_sql`. | Build marked fallback only after configuration is available; keep explicit resource specs authoritative. Pass both service thresholds for marked queries without changing specialized two-argument calls. |
| `src/strategies/feature_type.py`, `src/strategies/data_type.py`, corresponding `src/resources/*.yml`, `src/strategies/__init__.py` | Each reference type has an import-time registration and resource SQL; the package recursively imports strategy modules. The `data_type` resource details query references columns absent from the generated view. | Replace both registrations with one statically enumerated generic module, delete the four redundant files, and generate details from marked view aliases. |
| `src/reconcile.py::reconcile_queries`, `src/strategies/strategy.py::ReconciliationStrategy.as_candidate`, `src/api/model.py::ReconCandidate` | Candidates are converted one at a time; the base strategy uses `name_sim` for `match`. Candidate descriptions are limited to 500 characters. | Inspect the entire result before conversion to suppress ambiguous matches; override only generic candidate behavior, leaving the base and specialized paths unchanged. |
| `src/utility.py::Registry.register`, `src/strategies/strategy.py::StrategyRegistry.registered_class_hook`, `src/metadata.py::_get_supported_types` | Registry entries are classes in `Strategies.items`; the class hook can receive decorator arguments. `defaultTypes` is display-name sorted and `supportedTypes` currently comes from a hand-maintained tuple. | Store declared support on each registered class, reject missing/invalid declarations in tests, and derive supported IDs from the registry while preserving `defaultTypes` ordering. |
| `main.py::startup`, `src/configuration/setup.py::setup_config_store`, `src/api/router.py::get_config_dependency` | Startup loads configuration before checking the provider; a router dependency can load configuration independently. | Run named classifier and threshold checks after configuration loads, including the dependency's lazy-load path, before publishing a manifest. Do not query the database in these checks. |
| `config/config.yml`, `tests/config/config.yml`, `deployment/container/config/config.yml`, `config/entities.yml`, `tests/config/entities.yml`, `deployment/container/config/entities.yml` | Phase 1 declared `0.30`/`0.50` thresholds in the three runtime variants. Test `table_specs` are inline in `tests/config/config.yml`; both entity files also exist. None currently marks the reference types. | Mark only the two references in all configurations actually loaded by tests or containers; assert threshold parity and marker/key equality for the Phase 2 subset. |
| `src/preview.py::render_preview`, `src/suggest.py::render_flyout_preview`, `tests/test_metadata.py`, `tests/api/test_router.py`, `tests/strategies/test_feature_type.py` | Preview/flyout and manifest consumers instantiate registered classes; current tests import the feature-specific class and a supported-type constant. | Preserve type IDs and `Name` in generated details, migrate tests to registry lookups and declared statuses, and check previews and specialized behavior. |

## Scope

**In scope:** Reference markers and generated SQL, marked-spec resolution and details SQL, static generic registration for two keys, candidate/ambiguity handling, explicit status for every existing registration, manifest derivation, startup validation, application/test/container parity, and focused unit/HTTP/SQL verification.

**Out of scope:** The other tier-1 classifiers, four opt-in production weights and population checks, tier-2 `dimension`, unrelated specialized resources or scoring, deployment, and database writes outside a disposable schema.

**Affected contracts:** `authority.feature_type` and `authority.data_type` views and fuzzy functions; the service's manifest, candidate, details, preview, and startup behavior. Generated SQL must be applied to a disposable database before exercising the new runtime queries there; do not assume the deployed schema has been updated.

## Work Breakdown

### Area 1: Prepare Reference SQL and Configurations

**Objective:** Both reference specs satisfy the Phase 1 marked contract in all runtime variants.

**Affected code:** `config/entities.yml`, `tests/config/entities.yml`, inline `tests/config/config.yml::table_specs`, `deployment/container/config/entities.yml`, `schema/generated/feature_type.sql`, `schema/generated/data_type.sql`.

**Dependencies:** Verified Phase 1 contract and unmarked SQL parity.

**Tasks:**

- [x] `T1.1` **Change:** Mark only `feature_type` and `data_type` as `reconciliation: simple` in application, test, and mounted container entity specs, including the inline test configuration.
  - **Target:** The four existing configuration files above, at their `feature_type` and `data_type` entries.
  - **Current -> required:** Neither reference is marked -> all four effective configurations declare the same two marked keys with their existing ID, label, and description columns; leave weights unset/zero.
  - **Implementation:** Confirm the loaded test `table_specs` path before changing fixtures; preserve unrelated entities. Phase 3 will expand the closed inventory.
  - **Validation:** `V-1`, `V-2`; assert parsed marker/key parity, description aliases, and absence of scoring/index for zero weight.
- [x] `T1.2` **Change:** Regenerate and review reference SQL using `src/scripts/generate_entity_schema.py`.
  - **Target:** `schema/generated/feature_type.sql`, `schema/generated/data_type.sql`; existing `schema/generated/site.sql` and `schema/generated/method.sql` are read-only regression comparisons.
  - **Current -> required:** Reference SQL is unmarked -> both generated views expose `description` and `norm_description`, and fuzzy functions return description with threshold parameters; unmarked output remains byte-identical.
  - **Implementation:** Render with `--all-entities --force --output-dir` into a temporary directory first; copy only intentional reference output through the established generator workflow. Review all generated diffs, and never deploy from planning.
  - **Validation:** `V-1`, `V-2`, `V-7`; test function creation and reference details against a disposable schema.

**Completion evidence:** Exactly two marked keys in the Phase 2 configurations, working reference SQL, and unchanged unmarked generated output.

### Area 2: Implement the Configured Strategy

**Objective:** Both reference types use one runtime implementation and generated details SQL.

**Affected code:** `src/utility.py::resolve_specification`, `src/strategies/strategy.py::ReconciliationStrategy`, `src/strategies/query.py::BaseRepository`, `src/reconcile.py::reconcile_queries`, `src/strategies/configured_classifier.py` **NEW**, four obsolete reference strategy/resource files (delete), `tests/strategies/test_configured_classifier.py` **NEW**, `tests/strategies/test_feature_type.py` (replace/remove entity-specific assertions), `tests/test_reconcile.py`, `tests/api/test_router.py`.

**Dependencies:** Area 1; runtime access to configured thresholds and table specs.

**Tasks:**

- [x] `T2.1` **Change:** Resolve marked specifications and details SQL from loaded `table_specs`, while retaining resource YAML priority for unmarked or explicitly specialized keys.
  - **Target:** `src/utility.py::resolve_specification` and/or a marked-only resolver invoked from `src/strategies/configured_classifier.py` **NEW**; `src/strategies/query.py::BaseRepository` consumes the resulting `sql_queries` unchanged.
  - **Current -> required:** Missing resource returns `None` and no details SQL -> marked spec supplies `key`, physical `id_field`, `label_field: label`, display name, fuzzy SQL, and parameterized `details_sql` selecting `ID`, `Name`, and full `Description` when configured; `details_columns` includes only columns actually exposed by the view.
  - **Implementation:** Use only statically registered/config-validated keys when interpolating identifiers; bind the row ID as `%(id)s::int`. Keep existing resource-backed strategies and preview/flyout consumers intact.
  - **Validation:** `V-2`, `V-3`; cover missing description, extra details columns, absent ID, and the two reference views.
- [x] `T2.2` **Change:** Register one subclass per reference key from a static `CLASSIFIER_KEYS` tuple; migrate the reference implementations.
  - **Target:** `src/strategies/configured_classifier.py` **NEW**; delete `src/strategies/feature_type.py`, `src/strategies/data_type.py`, `src/resources/feature_type.yml`, `src/resources/data_type.yml`; replace `tests/strategies/test_feature_type.py` with generic tests in `tests/strategies/test_configured_classifier.py` **NEW**.
  - **Current -> required:** Two separate classes and YAML specs -> one generic implementation registered as `feature_type` and `data_type`, without reading configuration at import time or replacing `Strategies.items`.
  - **Implementation:** Use `Strategies.register(key=..., repository_cls=BaseRepository, support="supported")`; ensure old modules cannot re-register on package auto-import. Keep `sampling_context` and `dimension` on their existing paths.
  - **Validation:** `V-2`, `V-3`, `V-5`; assert key identities and no duplicated registrations or resource dependencies.
- [x] `T2.3` **Change:** Pass configured thresholds for marked fuzzy calls and convert generic candidates using the complete per-query result.
  - **Target:** `src/strategies/configured_classifier.py` **NEW**, `src/strategies/query.py::BaseRepository.find` or a marked-only repository override, and `src/reconcile.py::reconcile_queries` only if a generic batch hook is necessary; keep `ReconciliationStrategy.as_candidate` semantics for specialized types.
  - **Current -> required:** Two-argument calls and `name_sim`-based matching -> generic calls bind validated `label_threshold` and `description_threshold`; `score` uses `name_sim`, `match` uses normalized exact label or label similarity (`label_sim` when returned, otherwise `name_sim` on zero-weight functions), and duplicate normalized labels in the returned result all have `match: false`.
  - **Implementation:** Compare normalized labels with `src/utility.py::normalize_text` and group before candidate conversion; use the existing `auto_accept_threshold` for label similarity only. Truncate candidate description to 500 characters, preserve `None`/missing descriptions, and leave details full length. Avoid relying on a scored row's `label_sim` when Phase 1's zero-weight return does not include it.
  - **Validation:** `V-3`, `V-4`, `V-7`; exercise 500/501 characters, exact/unaccented duplicates, scored description-only rows, and threshold arguments in mock SQL calls.

**Completion evidence:** Both keys resolve without per-entity files; HTTP candidates validate, details/preview return full descriptions, and specialized candidate behavior is unchanged.

### Area 3: Declare Support and Fail Invalid Startup Configuration

**Objective:** Manifest publication and startup checks agree with statically registered types and loaded runtime configuration.

**Affected code:** `src/strategies/strategy.py::StrategyRegistry.registered_class_hook`, registration decorators in `src/strategies/administrative_region.py`, `bibliographic_reference.py`, `country.py`, `dimension.py`, `geonames.py`, `location.py`, `method.py`, `sampling_context.py`, `site.py`, `taxon.py`, `src/strategies/llm/modification_type.py`, `src/metadata.py`, `main.py::startup`, `src/api/router.py::get_config_dependency`, `tests/test_metadata.py`, `tests/api/test_router.py`, `tests/configuration/test_setup.py`.

**Dependencies:** Areas 1 and 2 supply the marked set and static keys.

**Tasks:**

- [x] `T3.1` **Change:** Require explicit supported/excluded registration metadata and derive the manifest's `supportedTypes` from it.
  - **Target:** `src/strategies/strategy.py::StrategyRegistry.registered_class_hook`, all remaining existing `@Strategies.register` declarations, `src/metadata.py::_get_supported_types`; `src/strategies/configured_classifier.py` **NEW** from `T2.2`.
  - **Current -> required:** A manually maintained tuple determines support -> every registered class declares `support`; supported IDs come from `Strategies.items` and excluded IDs stay in `defaultTypes` only.
  - **Implementation:** Preserve the existing supported/excluded decisions (including `dimension`'s current supported declaration until tier 2, and excluded `taxon`, `geonames`, `modification_type`); do not change specialized matching behavior. Retain the current display-name ordering of `defaultTypes` and deterministic supported-ID ordering. Update fake registries/tests instead of preserving the removed constant for their sake.
  - **Validation:** `V-5`; test all real registrations, invalid/missing status, and manifest membership with `dimension` still declared supported.
- [x] `T3.2` **Change:** Validate static classifier keys and thresholds after configuration loads, before service or lazy router configuration can publish a manifest.
  - **Target:** `main.py::startup`, `src/api/router.py::get_config_dependency`, and a shared validation function in `src/strategies/configured_classifier.py` **NEW** (or another existing owning configuration module); tests in `tests/configuration/test_setup.py` and `tests/api/test_router.py`.
  - **Current -> required:** Startup checks only that a provider exists -> missing/unmarked classifier specs, non-text label/int ID declarations, invalid details-column references, and missing/non-numeric/out-of-range `options:reconciliation` values raise a named configuration error before serving requests.
  - **Implementation:** Validate loaded effective `table_specs` against `CLASSIFIER_KEYS` in both directions for Phase 2 and require `0 < threshold <= 1`; do not read configuration at module import or fall back to SQL defaults. Run the same check after router-triggered lazy setup. Configuration parity tests compare application, test, and mounted container values without reading the database.
  - **Validation:** `V-1`, `V-6`; use mock providers and monkeypatch setup to cover startup success plus absent key/marker/column, extra marker, and each missing, zero, greater-than-one, or non-numeric threshold.

**Completion evidence:** Valid configuration serves the manifest; an invalid classifier or threshold produces a named startup failure, and no registered type silently inherits support.

### Area 4: Verify End-to-End Reference Behavior

**Objective:** Prove reference queries against the generated SQL and retain specialized contracts.

**Affected code:** `tests/strategies/test_configured_classifier.py` **NEW**, `tests/test_reconcile.py`, `tests/test_metadata.py`, `tests/api/test_router.py`, `tests/test_generate_entity_schema.py`, `tests/configuration/test_setup.py`; existing `src/resources/sampling_context.yml`, `src/resources/site.yml`, `src/resources/method.yml` are regression inputs only.

**Dependencies:** Areas 1-3.

**Tasks:**

- [x] `T4.1` **Change:** Add contract and HTTP cases for both references and specialized regressions.
  - **Target:** The existing test files above plus `tests/strategies/test_configured_classifier.py` **NEW**.
  - **Current -> required:** Feature-only tests and hand-maintained manifest assertions -> reference tests verify generated query columns and `ID`/`Name`/`Description` details, preview/flyout consumption, valid serialized POST candidate payloads, and unchanged `sampling_context` details and other unmarked calls.
  - **Implementation:** Use the existing mock provider and HTTP `TestClient` patterns; build a synthetic positively weighted marked spec for the description-only case without enabling production weights. Test duplicate normalized labels in one result, including when both rows score 100, and confirm distinct exact labels can auto-match.
  - **Validation:** `V-2` through `V-5`, `V-7`.
- [x] `T4.2` **Change:** Run a disposable-schema reference smoke test and record results before handoff.
  - **Target:** Generated SQL in `schema/generated/feature_type.sql` and `schema/generated/data_type.sql`; no production or staging schema edits.
  - **Current -> required:** Phase 1 tested synthetic SQL, not the reference runtime queries -> execute each generated view/function and generic details query for a known reference row in an isolated database, then reconcile those rows through the HTTP path using that database's test configuration.
  - **Implementation:** Use an isolated PostgreSQL instance with `pg_trgm`, `authority.immutable_unaccent`, and the required source tables; keep fixture data disposable. If unavailable, record `V-7` as unverified and do not claim the phase done.
  - **Validation:** `V-7`; assert candidate ID/name/description, full details, thresholds, and specialized schema parity.

**Completion evidence:** Focused unit/HTTP checks pass; disposable-schema reference SQL and generic details pass without modifying a deployed database.

## Acceptance-Criteria Coverage

| Criterion (source) | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P-AC-2`, `P-AC-7`, `P-AC-8`) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T4.1`, `T4.2` | `V-1`, `V-2`, `V-3`, `V-7` | Two generic keys, no reference resource/classes, successful generated details, specialized paths unchanged (`VM-3`). |
| `PH2-AC-2` (`P-AC-3`, `P-AC-5`, `P-AC-6`) | `T2.3`, `T4.1`, `T4.2` | `V-3`, `V-4`, `V-7` | Exact unique/duplicate/description-only flags, candidate length limit and full details (`VM-4`). |
| `PH2-AC-3` (`P-AC-10`) | `T2.2`, `T3.1`, `T4.1` | `V-5` | Every real registration has an explicit supported/excluded declaration; manifest and negative status test pass (`VM-5`). |
| `PH2-AC-4` (`P-AC-12`, `P-AC-16`) | `T1.1`, `T3.2` | `V-1`, `V-6` | Parity and named startup failures for invalid specs/thresholds (`VM-5`). |

## Validation And Testing

| ID | Check and target | Command or executable method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Reference marker/config parity and generated SQL | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_generate_entity_schema.py -q`; extend the file to parse the four effective reference specs and compare rendered SQL. | `PH2-AC-1`, `PH2-AC-4` | Two marked references, matching fixture/container specs and thresholds; unmarked site/method output unchanged. | Pass: reference marker and parity tests added; 14 generator tests pass; an `--all-entities` render matched every tracked unmarked SQL file on 2026-11-14. |
| `V-2` | Generic spec, registration and details unit tests | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/strategies/test_configured_classifier.py tests/strategies/test_strategy.py -q` | `PH2-AC-1` | Both references resolve view-backed details, missing description and invalid ID cases behave as specified; specialized tests pass. | Pass: `tests/strategies/test_configured_classifier.py` and `tests/strategies/test_strategy.py` passed on 2026-11-14. |
| `V-3` | Query and repository contract | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/strategies/test_configured_classifier.py tests/strategies/test_query.py tests/test_reconcile.py -q` | `PH2-AC-1`, `PH2-AC-2` | Marked SQL binds both configured thresholds; unmarked queries remain two-argument calls, details use only view columns, and `match` uses label evidence. | Pass: query, repository, and reconcile contract tests confirmed threshold binding and label-evidence behavior on 2026-11-14. |
| `V-4` | Candidate serialization and long details | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/api/test_router.py tests/api/test_model.py tests/test_reconcile.py -q` | `PH2-AC-2` | 500/501-character candidates serialize; full details remain available; duplicate normalized labels and description-only hits do not auto-match. | Pass: candidate truncation at 500 characters, duplicate-label suppression, and 500-character response validation passed on 2026-11-14. |
| `V-5` | Manifest status and specialization regression | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_metadata.py tests/api/test_router.py tests/strategies/test_strategy.py -q` | `PH2-AC-1`, `PH2-AC-3` | All real registrations declare a valid status, invalid/missing status fails a test, and default/supported lists preserve IDs and ordering. | Pass: every registration declares a status, the manifest is derived from declarations, and metadata and strategy tests pass on 2026-11-14. |
| `V-6` | Startup and lazy-load negative config cases | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/configuration/test_setup.py tests/api/test_router.py -q` | `PH2-AC-4` | Valid config starts; each malformed classifier or threshold causes a named configuration error before the manifest. | Pass: startup success plus nine invalid classifier/threshold cases and the lazy router path passed on 2026-11-14. |
| `V-7` | Generated SQL and HTTP reference smoke | In a disposable PostgreSQL instance, install required extensions/normalization and the two source-table fixtures; apply `schema/generated/feature_type.sql` and `schema/generated/data_type.sql`, execute both marked fuzzy functions with explicit thresholds and the generated `details_sql`, then POST matching reference queries via a test service configured against that instance. Check full details and unmarked `site`/`method` render parity separately. | `PH2-AC-1`, `PH2-AC-2`; `VM-3`, `VM-4` | Both reference SQL queries and HTTP candidates succeed without a deployed schema change. | Pass: disposable PostgreSQL 16 container; both generated functions and service-path queries passed, including duplicate-label suppression, truncation, full details, repeatable installation, and `pg_trgm` setting independence on 2026-11-14. |
| `V-8` | Focused quality checks | `.venv/bin/ruff check src/strategies src/metadata.py src/utility.py src/strategies/query.py src/reconcile.py main.py src/api/router.py tests/strategies/test_configured_classifier.py tests/test_metadata.py tests/api/test_router.py tests/configuration/test_setup.py` and `.venv/bin/black --check` on the touched Python files. | All tasks | No new lint/format failures in touched Python files. | Pass: Ruff and Black checks passed across `src`, `tests`, and `main.py` on 2026-11-14. |

When generating SQL, use `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python src/scripts/generate_entity_schema.py --all-entities --force --output-dir <temporary-directory>` with an actual temporary directory; do not overwrite tracked artifacts until reviewing the render. The Phase 1 plan records the required disposable-database prerequisites; no production/staging SQL execution is part of this phase.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Reference markers and test/runtime parity | `config/entities.yml`, `tests/config/entities.yml`, `tests/config/config.yml`, `deployment/container/config/entities.yml` | `T1.1` | `V-1` passes. |
| Reference generated SQL | `schema/generated/feature_type.sql`, `schema/generated/data_type.sql` | `T1.2` | `V-1`, `V-7` pass; unmarked files unchanged. |
| Configured strategy and fallback | `src/strategies/configured_classifier.py` **NEW**, `src/utility.py`, `src/strategies/query.py`, `src/reconcile.py` only if needed | `T2.1`-`T2.3`, `T3.2` | `V-2`-`V-4`, `V-6` pass. |
| Removed reference duplicates | `src/strategies/feature_type.py`, `src/strategies/data_type.py`, `src/resources/feature_type.yml`, `src/resources/data_type.yml` (delete) | `T2.2` | No stale imports or duplicate registrations. |
| Explicit support and startup checks | `src/strategies/strategy.py`, the eleven remaining registration modules named in Area 3, `src/metadata.py`, `main.py`, `src/api/router.py` | `T3.1`, `T3.2` | `V-5`, `V-6` pass. |
| Focused tests | `tests/strategies/test_configured_classifier.py` **NEW**, `tests/strategies/test_feature_type.py` (replace/remove), `tests/test_reconcile.py`, `tests/test_metadata.py`, `tests/api/test_router.py`, `tests/test_generate_entity_schema.py`, `tests/configuration/test_setup.py` | `T2.1`-`T4.1` | `V-1`-`V-6` pass. |
| Disposable SQL/HTTP result | No tracked file; record in implementation handoff | `T4.2` | `V-7` result recorded; no deployment. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Prepare reference SQL | Done | Phase 1 output | Markers added to all four configurations; reference SQL regenerated; unmarked output unchanged. |
| Area 2: Implement configured strategy | Done | Area 1 | Generic strategy, spec fallback, threshold binding, candidate and ambiguity rules implemented; reference duplicates removed. |
| Area 3: Declare support and validate startup | Done | Areas 1-2 | Support declarations on every registration; manifest derived; startup and lazy-router validation added. |
| Area 4: Verify reference behavior | Done | Areas 1-3 | Unit/HTTP/SQL checks passed; disposable PostgreSQL container verified and removed. |

## Definition Of Done

- [x] `PH2-AC-1` through `PH2-AC-4` have implementation and validation results mapped above.
- [x] Areas 1-4 and all deliverables are complete; `V-1` through `V-8` pass or unmet validation is explicitly reported rather than marked done.
- [x] Both reference types resolve candidate and full details queries against generated SQL; preview/flyout and candidate serialization remain valid.
- [x] `sampling_context`, `dimension`, and other specialized behavior and unmarked SQL are regression-tested; no type IDs or ordering are silently changed.
- [x] Runtime and mounted configuration, threshold values, static keys, and generated artifacts are synchronized before any future schema/config/code release.
- [x] Stop and report with results if actual source or schema contradicts this repository basis; do not invent a replacement design or expand into Phase 3.

## Risks And Open Questions

- Phase 1 changes have been tested but are not committed in the current worktree. If they change before implementation, rerun `V-1` and verify the SQL result columns before using this plan.
- The current `dimension` registration appears in `supportedTypes` even though its generated view is missing; preserve the declared status as the proposal requires and leave its functional repair to tier 2. A manifest status is not proof that its SQL works.
- SQL identifiers in generated details must come only from validated, registered table specs. Do not concatenate request-controlled type names or details columns into SQL.