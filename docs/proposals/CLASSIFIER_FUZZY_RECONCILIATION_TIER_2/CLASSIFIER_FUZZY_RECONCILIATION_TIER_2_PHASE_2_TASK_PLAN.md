# Tier 2 Context-Scoped Reconciliation: Phase 2 Task Plan

## Phase Summary

**Phase:** 2, Add Context and Configured Lookups. **Readiness:** Validated.

**Sources:** [Proposal](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2.md), [Phase 2 of the phase plan](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2_PHASE_PLAN.md#phase-2-add-context-and-configured-lookups), and [Phase 1 task plan](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2_PHASE_1_TASK_PLAN.md).

**Goal:** Add optional parent context and configured lookup reconciliation without weakening duplicate-label protection or changing unscoped behavior.

**Dependencies and constraints:** Phase 1's weighted eligibility regression and the exclusion register are complete locally. For the three-way parity check, use a fresh deployment candidate produced by the existing container setup from the same repository revision. Compare complete marked specifications with the repository and test inputs. The deployment operator checks the actual mounted configuration separately during rollout; candidate parity does not verify a running host. No deployment is authorized by this plan.

**Phase criteria**

1. [x] `PH2-AC-1` (from `P2-AC-1`, `P2-AC-9`): Valid `simple` and `lookup` scopes expose a `context` property and normalized parent context; unscoped entries remain valid. An unresolved scope target or lookup without a label fails startup with a named error.
2. [x] `PH2-AC-2` (from `P2-AC-2`): All thirteen label-bearing lookups use `lookup` and never score or auto-match on descriptions. Only `feature` and `taxa_common_names` use parent context among lookups; a nonzero lookup description weight is rejected.
3. [x] `PH2-AC-3` (from `P2-AC-3`, `P2-AC-11`): Supplied context filters before ranking, ambiguity detection, and the row limit. Matching results expose context in the description and set `context_match: true`. If no label candidate matches the supplied context, at most the requested number of unfiltered suggestions is returned, each with `match: false` and `context_match: false`; duplicates within the selected context cannot auto-match even at `limit: 1`.
4. [x] `PH2-AC-4` (from `P2-AC-6`): Generated alternate-identity results use the configured ID field and preserve property identifiers; `method` candidates continue to convert successfully.
5. [x] `PH2-AC-5` (from `P2-AC-7`): `dimension` configuration and schema are unchanged; `coordinate_method_dimension` is not a supported reconciliation type. `contact`, `abundance_element_group`, `dataset`, `taxa`, and specialized strategies remain unchanged, with exclusion reasons retained in the register tracked by [issue #43](https://github.com/humlab-sead/sead_authority_service/issues/43).
6. [x] `PH2-AC-6` (from `P2-AC-8`, `P2-AC-11`): Unscoped entities retain tier-1 public result shape, scoring, and properties apart from corrected duplicate suppression. Scoped entities without a context property retain label-search behavior with the same correction, omit `context_match`, and respect the row cap.
7. [x] `PH2-AC-7` (from `P2-AC-10`): Classifier and lookup configuration is identical across production, test, and deployment container configuration files.

For `PH2-AC-7`, the deployment input during phase validation is the generated release candidate. An actual host's mounted copy is a separate rollout check. The deployment operator confirmed on 2026-11-22 that the configuration mounted on the running host matches the repository.

## Repository Findings

**Repository basis:** Branch `classifier-fuzzy-reconciliation-tier-2`, commit `a74762c`, inspected 2026-11-22. The uncommitted Phase 1 implementation, generated SQL, tests, tracker, and reconciliation register were considered. Graphify was used for navigation; current source and tests, rather than its historical proposal paths, determine the findings below.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `schema/templates/entity.sql.jinja2`, `tests/strategies/test_classifier_prelimit_integration.py` | The Phase 1 weighted function counts normalized labels after `label_sim >= p_label_threshold OR description_sim >= p_description_threshold` and before the limit. An automated PostgreSQL regression covers equal labels with differently eligible descriptions. | Preserve this order and the regression after context filtering. |
| `src/strategies/configured_classifier.py` | `marked_classifier_keys`, validation, registration, and specification resolution currently accept `simple` only. Fuzzy candidate conversion requires a boolean `label_ambiguous`. | Add lookup registration and scope validation without making missing ambiguity data silently safe. |
| `src/utility.py::build_classifier_specification`, `src/strategies/query.py::BaseRepository.find` | Generated specifications publish no properties; threshold parameters are bound only for `simple`. | Build scoped properties and lookup queries, and pass request context as a bound value. |
| `src/strategies/strategy.py::_find_candidates`, `src/reconcile.py::reconcile_queries` | Batch requests reach the strategy with properties, but the base strategy does not forward them to `find`. Alternate-identity and fuzzy rows are merged before conversion. | Forward context through the configured path; ensure alternate rows satisfy the ambiguity and context contracts too. |
| `src/api/model.py::ReconCandidate`, `src/api/router.py` | The batch response uses a typed candidate model and excludes fields whose value is `None`. | Declare optional `context_match` in the response model and test both omission and explicit `false`. |
| `src/record_selection.py` | `selectable_types()` uses `marked_classifier_keys()` and interactive searches reject property hints. | Preserve existing selectable simple types and the no-property interactive contract; registering lookups must not enable them for record selection. |
| `src/resources/method.yml`, `src/utility.py::resolve_specification` | The specialized resource is resolved before a configured specification. Its query already returns `method_id` and its property ID is `method_abbreviation`. | Preserve the specialized runtime path and property; test the generated query and existing method conversion separately. |
| `config/entities.yml`, `tests/config/config.yml`, `deployment/container/Makefile`, `deployment/container/podman-compose.yml` | Repository entity specs are tracked; test specs are inline. Setup initializes an empty runtime directory from the repository config, and the container mounts the resulting host config read-only. Existing host files are preserved by default. | Generate the deployment candidate in a fresh test-owned directory and compare complete marked specs. Check the actual host mount separately during rollout. |
| `tests/test_generate_entity_schema.py`, `tests/configuration/test_setup.py` | Inventory, schema drift, and startup checks currently assume 46 `simple` registrations. | Update the assertions deliberately for the existing classifiers and the thirteen new lookups. |
| [Reconciliation type inventory](../../RECONCILIATION_TYPE_INVENTORY.md), `src/scripts/generate_reconciliation_inventory.py`, `tests/test_reconciliation_inventory.py` | The local register records model coverage, actual registration statuses, and maintained exclusion reasons. A registry test and snapshot check pass; the GitHub issue remains open. | Maintain the register for the new lookup registrations and verify its exclusion reasons for `PH2-AC-5`. The register is not an API source of truth. |
| `config/entities.yml::country`, `schema/generated/taxa_tree_master.sql` | `country` is currently a marked simple classifier, despite the proposal describing it as specialized. The configured taxon parent label is `species`. | Preserve the actual `country` behavior. Treat taxon parent labels as display text, not unique taxon identities. |

The automated weighted regression checks `Ceramic`/`cafe` and `CÉRAMIC`/`stone`, which normalize to the same label. It verifies one eligible row when only one description passes, and both eligible rows when the label matches. The disposable fixture now waits for the final PostgreSQL process before probing readiness, avoiding the temporary initialization server. All five isolated tests passed without skips after this change.

## Scope

**In scope:** The existing configured strategy, parent-label views and fuzzy functions, optional batch reconciliation context, thirteen lookup registrations, alternate-identity compatibility, startup and manifest validation, generated SQL, configuration parity, and focused unit, HTTP, and isolated PostgreSQL tests.

**Out of scope:** Production data changes or deployment; `dimension` configuration or schema repair; `coordinate_method_dimension`, `contact`, `abundance_element_group`, `dataset`, and `taxa` as new reconciliation targets; new per-entity strategies; generic derived-label expressions; changes to specialized strategy behavior; and adding context support to interactive record selection. Preserve existing specialized registrations and support statuses.

The fourteen classifier scope selections are taken from the earlier proposal inventory and checked against the current model's parent columns. Some current model unique sets do not include the parent; scope is the phase decision, not a claim that every declared key is composite.

| Configured classifier | Scope columns in declaration order |
| --- | --- |
| `abundance_element` | `record_type_id` |
| `colour`, `horizon` | `method_id` |
| `data_type` | `data_type_group_id` |
| `ecocode_definition` | `ecocode_group_id` |
| `ecocode_group` | `ecocode_system_id` |
| `property_type` | `property_type_group_id` |
| `rdb_code` | `rdb_system_id` |
| `season` | `season_type_id` |
| `site_type` | `site_type_group_id` |
| `taxa_tree_family` | `order_id` |
| `taxa_tree_genus` | `family_id` |
| `value_class` | `value_type_id`, `method_id` |
| `value_type_item` | `value_type_id` |

The lookup service keys are `chronology`, `data_provider`, `dating_lab`, `dating_material`, `ecocode_system`, `master_dataset`, `project`, `relative_age`, `taxonomic_order_system`, `feature`, `taxa_common_names`, `taxa_synonym`, and `rdb_system`. The model names the two singular service keys `relative_ages` and `taxa_synonyms`. Only `feature` (`feature_type_id`) and `taxa_common_names` (`taxon_id`) receive scope. `taxon_id` resolves to the existing `taxa_tree_master` table specification; `ecocode_system` and `rdb_system` must first be added as lookup specifications. Keep `taxa_synonym` and `rdb_system` unscoped.

The selected `dating_lab` label is `lab_name`. It is nullable, so rows without a lab name cannot be found by label. No derived label or fallback is authorized.

## Work Breakdown

### Area 1: Configure and validate types

**Objective:** Register the agreed classifiers and lookups with valid parent references and reproducible configuration.

**Affected code:** `config/entities.yml`, `tests/config/config.yml`, `src/strategies/configured_classifier.py`, `src/utility.py`, `src/record_selection.py`, `tests/configuration/test_setup.py`, `tests/test_metadata.py`, `tests/test_generate_entity_schema.py`, and `deployment/container/README.md`.

**Dependencies:** Validated Phase 1 output and the approved deployment-candidate parity method.

* [ ] `T1.1` **Change:** Add the thirteen lookup specifications and the sixteen selected scopes.
	* **Target:** `config/entities.yml` and inline `table_specs` in `tests/config/config.yml`.
	* **Current → required:** Forty-six marked simple specifications exist; nine of the thirteen lookup specifications are missing and none is marked `lookup`.
	* **Implementation:** Use the inventory above and verify table, ID, label, and parent columns against `../sead_shape_shifter/resources/target_models/sead_standard_model.yml` and `../sead_change_control/resources/tables_and_columns.csv`. Add parent lookup specs before resolving `ecocode_group` and `rdb_code`. Use existing service keys for `relative_age` and `taxa_synonym`, and set the `dating_lab` label to `lab_name`.
	* **Constraints:** Keep existing simple markers and weights, the declared parent order, excluded types, and specialized specs. No expression-based labels or inferred public property renames.
	* **Validation:** `V-1`, `V-2`, `V-3`, `V-4`, `V-5`; assert all fourteen classifier scopes, exactly two scoped lookups, eleven unscoped lookups, the null-name limitation for `dating_lab`, and matching full marked specs across the three approved inputs.

* [ ] `T1.2` **Change:** Validate scopes and register lookup types through the existing configured strategy.
	* **Target:** `src/strategies/configured_classifier.py::validate_classifier_configuration`, `initialize_classifiers`, `marked_classifier_keys`, and `src/utility.py::build_classifier_specification`.
	* **Current → required:** Startup validates and registers only simple classifiers and rejects their OpenRefine properties; scoped types must expose `context`, while lookups must use label-only scoring.
	* **Implementation:** Resolve each scope column to one configured parent's ID and label; report the entity and offending column for missing or ambiguous targets. Reject missing lookup labels and nonzero lookup description weights with named startup errors. Publish context metadata only for scoped entries and register lookup types with an explicit support status.
	* **Constraints:** Unscoped simple property behavior remains unchanged. Keep `src/record_selection.py::selectable_types` restricted to simple classifiers even if registry enumeration is extended; do not change interactive property rejection.
	* **Validation:** `V-1`, `V-2`, `V-3`; test valid scopes, unscoped entries, unknown or ambiguous parents, missing label, nonzero weight, metadata, support status, and record selection.

* [ ] `T1.3` **Change:** Establish and check production, test, and deployment configuration parity.
	* **Target:** `tests/test_generate_entity_schema.py` and `deployment/container/README.md`.
	* **Current → required:** A fresh setup-generated candidate matches all 46 marked repository specs, but all 46 test specs differ. Phase validation requires identical classifier and lookup specs in all three inputs.
	* **Implementation:** Add an automated test that runs the existing container setup with a fresh test-owned runtime directory and compares marked key sets and complete parsed table-spec mappings from the repository, test configuration, and generated candidate. Document that the deployment operator must separately compare the target host's actual mounted configuration during rollout.
	* **Constraints:** The candidate and repository input must come from the same checkout. Do not replace a host configuration, deploy the service, compare secrets, or weaken full equality to a field subset. A passing candidate check does not verify a running host.
	* **Validation:** `V-5` and `V-1`; verify a clean candidate, mismatched key or field, and a missing candidate file. Any mismatch or unavailable candidate fails the check.

**Completion evidence:** The configured inventory, startup failures, property metadata, and three-way equality are demonstrated by the checks above.

### Area 2: Generate scoped SQL

**Objective:** Filter context before ranking, ambiguity detection, and the row cap while retaining unscoped behavior.

**Affected code:** `schema/templates/entity.sql.jinja2`, `src/scripts/generate_entity_schema.py`, `schema/generated/`, `schema/__deploy__.sql`, and `tests/test_generate_entity_schema.py`.

**Dependencies:** `T1.1` and `T1.2`; validated Phase 1 ambiguity behavior.

* [ ] `T2.1` **Change:** Generate parent context and eligible-row ambiguity for scoped `simple` and `lookup` entries.
	* **Target:** `schema/templates/entity.sql.jinja2` and the existing generator if additional resolved scope metadata is needed.
	* **Current → required:** Phase 1 functions count eligible normalized labels before `p_limit`; they have no parent context or lookup branch.
	* **Implementation:** Join each configured parent with a left join; expose `context` and `norm_context` in declaration order. Apply normalized supplied context to the eligible label set before scoring order, windowed ambiguity, and `p_limit`. If it yields no label candidates, return the limited unfiltered set with a distinguishable fallback status.
	* **Constraints:** A missing parent makes the context null and cannot satisfy supplied context. Do not treat parent labels as keys, interpolate request values into SQL, change unscoped public results, or weaken Phase 1 ambiguity checks. Lookup eligibility and scoring use labels only.
	* **Validation:** `V-1`, `V-4`, `V-6`; cover weighted and unweighted paths, null parents, two-parent order, accents, duplicates across and within scopes, fallback, and limits of one and greater than one.

* [ ] `T2.2` **Change:** Regenerate and verify the tracked schema and bundle.
	* **Target:** The fourteen existing scoped classifier SQL files, existing `feature.sql`, `relative_age.sql`, `taxa_synonym.sql`, and `taxonomic_order_system.sql`, nine `NEW` lookup SQL files listed in Deliverables, `schema/__deploy__.sql`, and `tests/test_generate_entity_schema.py`.
	* **Current → required:** Tracked outputs reflect the uncommitted Phase 1 baseline; several lookup outputs do not exist.
	* **Implementation:** Extend temporary-render comparisons to every changed classifier and lookup and check bundle contents. Regenerate only after reconciling the existing dirty Phase 1 files, using the repository generation and bundle targets.
	* **Constraints:** Preserve user changes and unchanged specialized SQL; do not invoke schema deployment or destructively clean generated files.
	* **Validation:** `V-1`, `V-4`, `V-6`; regenerated outputs and bundle agree with the template and approved specs.

**Completion evidence:** Generated SQL and the bundle reproduce from configuration, and real PostgreSQL checks demonstrate filtering before ambiguity and limiting.

### Area 3: Carry context and alternate identities through reconciliation

**Objective:** Return correct batch candidates without changing unrelated strategies or the unscoped response.

**Affected code:** `src/utility.py`, `src/strategies/configured_classifier.py`, `src/strategies/query.py`, `src/strategies/strategy.py`, `src/api/model.py`, `src/reconcile.py`, `tests/strategies/test_query.py`, `tests/strategies/test_strategy.py`, `tests/strategies/test_configured_classifier.py`, `tests/test_reconcile.py`, and `tests/api/test_router.py`.

**Dependencies:** Areas 1 and 2. Prefer a configured-strategy override where a shared change would affect specialized strategies.

* [ ] `T3.1` **Change:** Forward and bind optional context for configured searches.
	* **Target:** `ConfiguredClassifierStrategy`, `BaseRepository.find`, and `build_classifier_fuzzy_sql`.
	* **Current → required:** Batch properties reach the strategy, but the base candidate search calls `find(query, limit)` without them; lookup thresholds are not bound.
	* **Implementation:** Carry the supplied context to the generated scoped query as a bound value, including lookup threshold parameters. Preserve the existing unscoped call shape and produce the SQL fallback status needed by conversion.
	* **Constraints:** Filtering and ambiguity must happen before the row limit, including when alternate identities are present. Do not change specialized strategy behavior or enable interactive property hints.
	* **Validation:** `V-1`, `V-2`, `V-3`, `V-4`; assert parameter binding, a quoted input, context hit and miss, omitted property, row cap, and unchanged specialized calls.

* [ ] `T3.2` **Change:** Serialize context and suppress unsafe matches.
	* **Target:** `ConfiguredClassifierStrategy.as_candidates`, its candidate conversion, and `src/api/model.py::ReconCandidate`.
	* **Current → required:** The candidate has a 500-character optional description but no modeled context status; conversion rejects a missing ambiguity flag.
	* **Implementation:** Put `Context: <parent labels>` before the entity description within 500 characters. Emit `context_match: true` for a supplied matching context, `false` for every fallback result, and omit it when no context is supplied. Continue using `name_sim` for score and `label_sim` for automatic matching; do not expose `label_ambiguous`.
	* **Constraints:** Fallback always sets `match: false`; duplicates within a selected context do not auto-match. Null context cannot match a supplied value. Preserve names, unscoped response shape, and row limits.
	* **Validation:** `V-1`, `V-4`; assert the actual HTTP JSON, including `false` versus omitted, description ordering and truncation, duplicate suppression, and no internal flag.

* [ ] `T3.3` **Change:** Generate compatible alternate-identity queries for configured entities.
	* **Target:** `src/utility.py::build_classifier_specification`, `src/strategies/query.py::fetch_by_alternate_identity`, and configured candidate handling.
	* **Current → required:** Generated configured specs have no alternate query; the specialized method resource already returns `method_id` for `method_abbreviation`.
	* **Implementation:** Generate a parameterized query from an explicitly configured alternate column, returning the configured ID field rather than `id` and retaining the declared property identifier. Make alternate rows compatible with required ambiguity and context handling, including duplicates and the result cap. Exercise the generator with method's configured ID and separately exercise the existing method resource through candidate conversion.
	* **Constraints:** Do not replace `src/resources/method.yml` or change the specialized method strategy. Do not fabricate `label_ambiguous: false` for an unverified result, auto-match a context fallback, or change property behavior of existing unscoped simple classifiers.
	* **Validation:** `V-1`, `V-3`, `V-4`; cover `method_id`, `method_abbreviation`, duplicate labels, alternate and fuzzy results for the same ID, and an alternate result outside the supplied context.

**Completion evidence:** Batch HTTP results, bound repository parameters, and alternate-identity candidate conversion meet `PH2-AC-3`, `PH2-AC-4`, and `PH2-AC-6` without specialized regressions.

### Area 4: Verify exclusions and integration

**Objective:** Prove the requested behavior on generated SQL and preserve exclusions and existing clients.

**Affected code:** `tests/strategies/test_classifier_prelimit_integration.py`, `tests/strategies/test_configured_classifier.py`, `tests/api/test_record_selection.py`, `tests/api/test_router.py`, `tests/test_generate_entity_schema.py`, `tests/test_metadata.py`, `docs/RECONCILIATION_TYPE_INVENTORY.md`, `tests/test_reconciliation_inventory.py`, and `docs/OPERATIONS.md` if the generated-schema rollout contract changes.

**Dependencies:** Areas 1–3; the existing issue #43 register.

* [ ] `T4.1` **Change:** Extend the disposable PostgreSQL and HTTP regression coverage.
	* **Target:** `tests/strategies/test_classifier_prelimit_integration.py` and the existing focused unit/API test files.
	* **Current → required:** The opt-in fixture installs `feature_type` and weighted `rdb_code` in a test-owned, network-isolated container; Phase 2 needs scoped and lookup cases.
	* **Implementation:** Add synthetic parent and child rows and install representative generated functions for a scoped classifier, `value_class`, `feature`, `taxa_common_names`, `rdb_system`, `taxa_synonym`, and `dating_lab`. Include lab rows with and without `lab_name`; only the named row is searchable by label. Drive endpoint cases with SQL results selected for the actual request parameters, alongside repository-binding unit tests. Retain the weighted same-label eligibility regression and the final-server readiness check.
	* **Constraints:** Use only the test-owned container, clean it on success and failure, and fail rather than skip when opt-in prerequisites are missing. Do not touch shared or production databases.
	* **Validation:** `V-4` and `V-1`; check hit, miss, no context, null parent, multiple parents, accent normalization, duplicate labels within/across scopes, `limit: 1`, descriptions, lookup label-only scoring, and HTTP response fields.

* [ ] `T4.2` **Change:** Verify exclusions, preserved behavior, and schema rollout guidance.
	* **Target:** `tests/test_generate_entity_schema.py`, `tests/test_metadata.py`, `tests/api/test_router.py`, `tests/api/test_record_selection.py`, `docs/RECONCILIATION_TYPE_INVENTORY.md`, and `tests/test_reconciliation_inventory.py`.
	* **Current → required:** Exclusion assertions and the issue #43 register exist; the phase adds registered types and generated schema.
	* **Implementation:** Assert `dimension` configuration and schema are unchanged, `coordinate_method_dimension` is not supported, and the other excluded or specialized types retain their prior registration and behavior. Update the register's handwritten reasons and planned phases for newly supported lookups, regenerate its snapshot, and compare the remaining exclusions. Document any necessary schema-before-application compatibility requirement in `docs/OPERATIONS.md`.
	* **Constraints:** The register records registry status but must not control the API. Changing deployment behavior requires separate authorization. Preserve `country` as its current simple classifier and `taxon`'s current support status.
	* **Validation:** `V-1`, `V-2`, `V-7`, `V-8`; check registry/manifest, interactive record selection, specialized resources, register reasons, and the full default suite.

**Completion evidence:** The isolated SQL/HTTP matrix passes, exclusions are checked against an available register, and preserved behavior has regression evidence.

## Acceptance-Criteria Coverage

| Criterion | Tasks | Validation | Expected evidence |
| --- | --- | --- | --- |
| `PH2-AC-1` (`P2-AC-1`, `P2-AC-9`) | `T1.1`, `T1.2`, `T2.1` | `V-1`, `V-2`, `V-3`, `V-4`, `V-6` | Scope metadata and normalized context work; invalid parents or labels fail startup by name. |
| `PH2-AC-2` (`P2-AC-2`) | `T1.1`, `T1.2`, `T2.1`, `T4.1` | `V-1`, `V-2`, `V-4`, `V-6` | Thirteen lookups register, two are scoped, and descriptions cannot affect lookup scoring or matching. |
| `PH2-AC-3` (`P2-AC-3`, `P2-AC-11`) | `T2.1`, `T3.1`, `T3.2`, `T3.3`, `T4.1` | `V-1`, `V-2`, `V-3`, `V-4` | Context precedes ranking, ambiguity, and limit; HTTP hit, fallback, and duplicate cases have correct flags. |
| `PH2-AC-4` (`P2-AC-6`) | `T3.3` | `V-1`, `V-3`, `V-4` | Generated IDs and property names survive conversion; existing method conversion still works. |
| `PH2-AC-5` (`P2-AC-7`) | `T1.1`, `T4.2` | `V-1`, `V-2`, `V-7`, `V-8` | Excluded and specialized behavior is unchanged and reasons are present in the approved register. |
| `PH2-AC-6` (`P2-AC-8`, `P2-AC-11`) | `T1.2`, `T2.1`, `T3.1`, `T3.2`, `T4.1`, `T4.2` | `V-1`, `V-2`, `V-3`, `V-4`, `V-8` | No-context and unscoped results retain their contracts and the strict row cap. |
| `PH2-AC-7` (`P2-AC-10`) | `T1.1`, `T1.3` | `V-1`, `V-5` | Full parsed classifier and lookup specifications agree across all three approved inputs. |

## Validation And Testing

Run commands from the repository root. Baselines below are from this planning work unless marked otherwise. Do not run regeneration against a dirty worktree until its existing changes are understood and preserved.

| ID | Check and command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- |
| `V-1` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests/test_generate_entity_schema.py tests/strategies/test_configured_classifier.py tests/test_reconcile.py tests/api/test_record_selection.py tests/api/test_router.py -q` | Generated contracts, candidates, batch/interactive HTTP, exclusions | All tests pass, including the new cases described in the tasks. | Pass: 179 passed, 3 warnings (161 before the new cases). |
| `V-2` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests/test_metadata.py tests/test_suggest.py tests/strategies/test_query.py -q` | Registry metadata, suggestions, bound query parameters | All tests pass and unscoped properties remain unchanged. | Pass: 91 passed (78 before the new cases). |
| `V-3` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests/configuration/test_setup.py tests/strategies/test_strategy.py -q` | Startup errors, generic strategy, alternate identities | All tests pass, including named invalid-scope/lookup errors and method compatibility. | Pass: 58 passed, 4 warnings (55 before the new cases). |
| `V-4` | `CLASSIFIER_SQL_INTEGRATION=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests/strategies/test_classifier_prelimit_integration.py -q` | Real generated PostgreSQL SQL and request-dependent HTTP results | All tests execute without skips and the test-owned container is removed. | Pass: 12 passed, 1 warning, no skips; adds scoped context, fallback, two-parent, lookup label-only, unscoped duplicate, nullable-label, and HTTP context cases. |
| `V-5` | Run the three-input parsed YAML equality check below using a fresh setup-generated deployment candidate. | `PH2-AC-7` | Same marked keys and complete spec mappings in all three inputs; the candidate is removed afterward. | Pass: 59 marked specifications agree across the repository, test, and setup-generated candidate. No deployed host was modified. |
| `V-6` | After preserving existing changes, run `make generate-schema-force`, then `make generate-schema-bundle`, then `V-1`. Inspect the generated diff and use temporary-render/bundle tests. | Generated artifacts and specialized SQL | Changed files agree with the template; excluded and unrelated specialized SQL is unchanged. | Pass: regeneration and bundle succeeded; all 59 marked files reproduce from configuration and unmarked specialized SQL stayed byte-identical; V-1 passed. |
| `V-7` | Run the focused Black and isort commands below, `.venv/bin/python scripts/check_imports.py`, `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests/test_reconciliation_inventory.py -q`, and `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m src.scripts.generate_reconciliation_inventory --check`. Inspect the register and specialized-file diff against the pre-phase state. | Formatting, imports, exclusions | Checks pass, no excluded implementation changes, and register reasons and generated status agree. | Pass: Black, isort, and import checks clean; 8 register tests and the snapshot check pass. `test_registry.py` now restores the shared registry in place so registrations stay visible to later tests. |
| `V-8` | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider -o addopts='' tests -q` | Cross-layer default regression suite | No regressions; record skips separately and run `V-4` explicitly. | Pass: 1396 passed, 62 skipped (integration-marked), 0 failed. |

`V-5` creates a fresh deployment candidate without starting a service or touching an existing deployment. It does not check the configuration mounted by any running host:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c '
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import yaml

def marked(specs):
	return {key for key, spec in specs.items() if isinstance(spec, dict) and spec.get("reconciliation") in ("simple", "lookup")}

with TemporaryDirectory(prefix="authority-candidate-") as directory:
	subprocess.run(["make", "-C", "deployment/container", "setup", f"DEPLOY_DIR={directory}"], check=True)
	production = yaml.safe_load(Path("config/entities.yml").read_text())
	testing = yaml.safe_load(Path("tests/config/config.yml").read_text())["table_specs"]
	deployment = yaml.safe_load((Path(directory) / "config/entities.yml").read_text())
	keys = marked(production)
	assert keys == marked(testing) == marked(deployment), "marked key sets differ"
	different = [key for key in sorted(keys) if production[key] != testing[key] or production[key] != deployment[key]]
	assert not different, f"table specifications differ: {different}"
	print(f"{len(keys)} marked specifications agree")
'
```

For `V-7`, check the Python files changed by the implementation. The following verified paths are the expected starting set; include any additional approved touched Python files:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m black --check src/utility.py src/strategies/configured_classifier.py src/strategies/query.py src/strategies/strategy.py src/api/model.py tests/test_generate_entity_schema.py tests/configuration/test_setup.py tests/strategies/test_configured_classifier.py tests/strategies/test_classifier_prelimit_integration.py tests/strategies/test_query.py tests/strategies/test_strategy.py tests/test_reconcile.py tests/test_metadata.py tests/test_suggest.py tests/api/test_router.py tests/api/test_record_selection.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m isort --check-only src/utility.py src/strategies/configured_classifier.py src/strategies/query.py src/strategies/strategy.py src/api/model.py tests/test_generate_entity_schema.py tests/configuration/test_setup.py tests/strategies/test_configured_classifier.py tests/strategies/test_classifier_prelimit_integration.py tests/strategies/test_query.py tests/strategies/test_strategy.py tests/test_reconcile.py tests/test_metadata.py tests/test_suggest.py tests/api/test_router.py tests/api/test_record_selection.py
.venv/bin/python scripts/check_imports.py
```

## Deliverables

| Deliverable | Target | Tasks | Completion evidence |
| --- | --- | --- | --- |
| Configuration and validation | `config/entities.yml`, `tests/config/config.yml`, `src/strategies/configured_classifier.py`, `src/utility.py` | `T1.1`, `T1.2`, `T1.3`, `T3.3` | Inventory, scope, errors, properties, and three-way parity pass. |
| Generated schema and bundle | `schema/templates/entity.sql.jinja2`, `schema/__deploy__.sql`, and the existing generated SQL files listed below | `T2.1`, `T2.2` | Reproduced SQL passes drift and isolated-database checks. |
| New lookup schema | The nine **NEW** generated SQL files listed below | `T2.2` | All nine files are generated from approved table specs. |
| Runtime and API | `src/strategies/query.py`, `src/strategies/configured_classifier.py`, `src/utility.py`, `src/api/model.py`; `src/strategies/strategy.py` only if a shared change is proven necessary | `T3.1`, `T3.2`, `T3.3` | Bound context and alternate identities produce correct HTTP candidates. |
| Tests | `tests/test_generate_entity_schema.py`, `tests/configuration/test_setup.py`, `tests/strategies/test_configured_classifier.py`, `tests/strategies/test_classifier_prelimit_integration.py`, `tests/strategies/test_query.py`, `tests/strategies/test_strategy.py`, `tests/test_reconcile.py`, `tests/test_metadata.py`, `tests/test_suggest.py`, `tests/api/test_router.py`, `tests/api/test_record_selection.py` | `T1.2`, `T1.3`, `T2.2`, `T3.1`, `T3.2`, `T3.3`, `T4.1`, `T4.2` | `V-1` through `V-4` cover the required cases; `V-8` has no regressions. |
| Reconciliation register | `docs/RECONCILIATION_TYPE_INVENTORY.md`, `tests/test_reconciliation_inventory.py` | `T4.2` | Lookup statuses and remaining reasons are current; the registry test and snapshot check pass. |
| Operational guidance | `deployment/container/README.md`; `docs/OPERATIONS.md` if rollout guidance changes | `T1.3`, `T4.2` | The candidate check, separate host check, and schema dependency are documented without deployment. |

Existing generated classifier files: `schema/generated/abundance_element.sql`, `schema/generated/colour.sql`, `schema/generated/horizon.sql`, `schema/generated/data_type.sql`, `schema/generated/ecocode_definition.sql`, `schema/generated/ecocode_group.sql`, `schema/generated/property_type.sql`, `schema/generated/rdb_code.sql`, `schema/generated/season.sql`, `schema/generated/site_type.sql`, `schema/generated/taxa_tree_family.sql`, `schema/generated/taxa_tree_genus.sql`, `schema/generated/value_class.sql`, and `schema/generated/value_type_item.sql`.

Existing generated lookup files: `schema/generated/feature.sql`, `schema/generated/relative_age.sql`, `schema/generated/taxa_synonym.sql`, and `schema/generated/taxonomic_order_system.sql`.

**NEW** generated lookup files: `schema/generated/chronology.sql`, `schema/generated/data_provider.sql`, `schema/generated/dating_lab.sql`, `schema/generated/dating_material.sql`, `schema/generated/ecocode_system.sql`, `schema/generated/master_dataset.sql`, `schema/generated/project.sql`, `schema/generated/taxa_common_names.sql`, and `schema/generated/rdb_system.sql`.

The issue #43 register is available locally and must be maintained as types are registered. Phase verification uses the generated deployment candidate; the host-mounted configuration is checked separately by the deployment operator during rollout.

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| 1. Configure and validate types | Done | Phase 1; approved candidate method | T1.1–T1.3 delivered; 46 simple and 13 lookup entries validated, 16 scopes resolved, parity confirmed on all three inputs and on the running host. |
| 2. Generate scoped SQL | Done | Area 1 | T2.1–T2.2 delivered; 9 new lookup files, 59 regenerated marked files, unmarked SQL byte-identical. |
| 3. Carry context and identities | Done | Areas 1–2 | T3.1–T3.3 delivered; bound context, `context_match` serialization, generated alternate-identity query. |
| 4. Verify exclusions and integration | Done | Areas 1–3; issue #43 register | T4.1–T4.2 delivered; 12 disposable-PostgreSQL tests, register regenerated, rollout guidance updated. |

## Definition Of Done

* [x] Phase 1's weighted eligibility regression and completion record are corrected, and the exclusion register is available locally.
* [x] The deployment-candidate parity method is approved, the separate host check is assigned to the deployment operator, and the source phase plan marks Phase 2 ready.
* [x] All `PH2-AC-*` criteria have recorded task and fresh validation evidence.
* [x] The thirteen lookups, sixteen scopes, named failures, and all three identical configuration inputs are verified.
* [x] Context, fallback, duplicates, limits, alternate identity, and unscoped/specialized compatibility pass the SQL and HTTP checks.
* [x] Generated SQL and the bundle reproduce, required quality checks pass, and the default regression suite has no unexplained failures.
* [x] Exclusions and their reasons are verified against the approved register; documentation and rollout dependencies are current.
* [x] All work areas and deliverables are complete; deviations, follow-up, and any skips are recorded.
* [x] No unresolved decision affects implementation, correctness, or validation.

## Risks And Open Questions

1. **Deployment parity:** A generated candidate does not prove a running host uses that configuration. The deployment operator must check the actual mount during rollout. The current test specs also need their omitted repository fields restored for literal equality.
   - Resolved for the repository inputs: the inline test specifications now match `config/entities.yml` exactly, and `V-5` reports 59 agreeing marked specifications.
   - Resolved for the running host: the deployment operator confirmed on 2026-11-22 that the mounted configuration matches the repository. This confirmation covers the host inspected; `deployment/container/README.md` and `docs/OPERATIONS.md` keep the check as a repeated rollout step for other hosts and later revisions.
2. **Dating laboratory label:** `lab_name` is nullable. Rows without a name cannot be found by label; a fallback or derived label requires a separate decision.
3. **Alternate identity and context:** The existing method resource wins over configured resolution, while configured fuzzy conversion requires `label_ambiguous`. Keep the method runtime path unchanged and verify generated method-shaped rows separately; if the intended requirement is to replace the specialized runtime query, obtain an explicit decision before changing it. The chosen configured implementation must also account for alternate rows outside a supplied context and duplicates before limiting.
   - Resolved as designed: the specialized method resource is unchanged. Configured specifications now generate an alternate-identity query that returns the configured ID field and computes duplicate labels across the entity, and candidate conversion returns an out-of-context row as a non-matching suggestion rather than dropping or matching it.
4. **Parent display labels:** Parent text is not a unique identifier; the current taxon table spec labels a taxon by `species` alone. Duplicate-label suppression remains mandatory, and a fuller taxon label would require a separate approved design.

When implementation is authorized, stop and report the evidence if repository state, approved decisions, or a required contract differs from this plan. Do not invent a replacement design or broaden scope.
