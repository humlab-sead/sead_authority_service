# Tier 2 Context-Scoped Reconciliation: Phase 1 Task Plan

## Phase Summary

**Phase:** 1, Correct Duplicate Matching Before the Limit. **Readiness:** Validated for implementation.

**Sources:** [Proposal](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2.md) and [Phase 1 of the phase plan](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2_PHASE_PLAN.md#phase-1-correct-duplicate-matching-before-the-limit).

**Goal:** Prevent an existing configured classifier from automatically matching an eligible duplicate label hidden by the SQL row limit.

**Dependencies and constraints:** Use the existing tier-1 configured classifier and generated fuzzy functions. The limit caps rows, not distinct labels. Keep the zero default description weight, label-based automatic-match rule, candidate scoring, descriptions, properties, and unscoped public response unchanged except for duplicate suppression. Do not expand results to reveal omitted duplicates. Phase 2 context and lookup work is not part of this phase.

**Phase criteria**

1. [ ] `PH1-AC-1` (from `P2-AC-11`): For existing configured classifiers, detect duplicate normalized labels before limiting; at `limit: 1`, return at most one row and never auto-match it if another eligible row has the same normalized label.
2. [ ] `PH1-AC-2` (from `P2-AC-8`): Preserve tier-1 public result shape, scoring, and property behavior for unscoped classifiers apart from the duplicate-suppression correction. Do not expose the internal ambiguity flag in candidate responses.

If the repository or generated schema differs materially from these findings, stop and report the conflict rather than inventing a replacement design or extending the scope.

## Repository Findings

**Repository basis:** `dev` at `e231042`, inspected 2026-11-22. The modified proposal and untracked phase plan were considered; other uncommitted changes were left untouched. Graphify was queried using `~/.local/bin/graphify` because `.venv/bin/graphify` is absent. Its navigation results were checked against the current source.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `schema/templates/entity.sql.jinja2`, `schema/generated/feature_type.sql`, `schema/generated/rdb_code.sql` | Both `simple` branches filter and rank before `limit p_limit`. The weighted branch computes `scored` and `filtered`; the zero-weight branch filters directly. The view's `norm_label` is `authority.immutable_unaccent(lower(label))`. | Count equal `norm_label` values in the eligible rows, after existing filters and before the limit, in both branches. Preserve existing ordering and score expressions. |
| `src/strategies/configured_classifier.py::ConfiguredClassifierStrategy` | `as_candidates` counts Python-normalized labels only in returned rows. The candidate builder uses `name_sim` for score, exact label or `label_sim` for `match`, and truncates descriptions to 500 characters. | Carry a SQL ambiguity boolean through to conversion; retain the returned-row duplicate check and all other candidate rules. |
| `src/utility.py::build_classifier_specification`, `src/strategies/query.py::BaseRepository.find`, `src/strategies/strategy.py::find_candidates` | Configured fuzzy SQL selects all function columns, binds the two configured thresholds, and returns dictionaries. The strategy sorts and caps rows again. Configured specs publish no properties or property settings. | Append the internal field to the existing SQL columns; keep arguments, bindings, ordering, row cap, and property metadata. Fail explicitly if a fuzzy row lacks a valid ambiguity flag instead of treating an old schema as safe. |
| `src/reconcile.py::reconcile_queries`, `src/record_selection.py::search_interactive`, `src/api/model.py::ReconCandidate` | Batch and interactive reconciliation both call `as_candidates`. Batch responses use a Pydantic response model; interactive responses return candidate dictionaries directly. | Test both response paths: model filtering alone cannot prove that the internal field stays private. |
| `src/suggest.py::suggest_entities`, `src/utility.py::build_classifier_prefix_sql`, `src/mcp/tools.py::_fallback_fuzzy_search` | Suggest uses separate prefix rows, not `as_candidates`. The MCP fallback reads fuzzy rows by position; it already assumes column 3 is a score, although simple-classifier functions currently put `description` there. | Do not require the fuzzy flag on prefix suggestions or alter existing column positions. The pre-existing MCP scoring issue is outside this phase; do not broaden the fix. |
| `config/entities.yml`, `tests/test_generate_entity_schema.py`, `schema/create_schema.sh::generate_deploy_sql` | There are 46 marked classifiers, all with tracked generated SQL; `rdb_code` alone has positive description weight. `schema/__deploy__.sql` is tracked and built from generated files. The template drops old function signatures before recreating them. | Regenerate marked artifacts and the bundle, verify unmarked SQL is unchanged, and document the changed internal return contract and schema-before-code order. |
| `tests/strategies/test_configured_classifier.py`, `tests/api/test_record_selection.py` | Existing duplicate tests supply both rows to Python. They do not prove behavior when PostgreSQL returns only one. | Add a real PostgreSQL test using synthetic rows as well as focused conversion and HTTP tests. |

## Scope

**In scope:** The `simple` branch of generated fuzzy SQL; internal ambiguity propagation and configured candidate conversion; generated SQL and deployment bundle; focused generator, strategy, API, and disposable-database tests; directly related release guidance.

**Out of scope:** Parent context, `lookup` registration, alternate identities, configuration changes, specialized strategies, MCP scoring repair, production data changes, and deployment. Prefix autocomplete and unmarked SQL must retain their current behavior.

## Work Breakdown

### Area 1: Count eligible duplicates in generated SQL

**Objective:** Return an internal ambiguity flag for every limited fuzzy row without changing candidate ranking or the limit.

**Affected code:** `schema/templates/entity.sql.jinja2`, `schema/generated/`, `schema/__deploy__.sql`, `tests/test_generate_entity_schema.py`.

**Dependencies:** None.

- [ ] `T1.1` **Change:** Add a pre-limit boolean named `label_ambiguous` to both marked fuzzy-function branches.
  - **Target:** `schema/templates/entity.sql.jinja2`, simple-classifier `returns table` and query branches; `tests/test_generate_entity_schema.py`.
  - **Current -> required:** The function returns only limited rows with no full-set ambiguity information -> append `label_ambiguous boolean` after the existing columns, with `true` when more than one eligible row shares the row's `norm_label`.
  - **Implementation:** Retain the view's normalized label through scoring and filtering; compute the boolean over the filtered eligible set, for example with `count(*) over (partition by norm_label) > 1`, before the existing `order by` and `limit`. Apply existing filter-parameter joins and predicates before counting. For weighted classifiers, eligibility remains `label_sim >= p_label_threshold OR description_sim >= p_description_threshold`; an ineligible same-label row must not affect the count.
  - **Constraints:** Preserve all existing return column positions and types, thresholds, score expressions, sort keys, function arguments, view definitions, and the unmarked branch. Keep `p_limit` as the maximum row count. The SQL normalization is the view's `norm_label`; do not introduce a new normalization rule.
  - **Validation:** `V-1`, `V-3`; cover zero and positive description weights, duplicate and unique eligible rows, an ineligible same-label row, filters, and limits of 1 and greater.
- [ ] `T1.2` **Change:** Regenerate the tracked classifier SQL and deployment bundle.
  - **Target:** The 46 `schema/generated/<key>.sql` files listed in Deliverables and `schema/__deploy__.sql`.
  - **Current -> required:** Tracked functions return the tier-1 columns -> every marked function appends the same ambiguity field, and the bundle contains those generated definitions.
  - **Implementation:** Run `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python src/scripts/generate_entity_schema.py --all-entities --force` from the repository root, then `make generate-schema-bundle`. Do not edit generated SQL by hand. Compare generated output with tracked files and verify every unmarked entity is unchanged. Check that the generated `drop function` statements allow the changed return type to be installed twice in the disposable database.
  - **Constraints:** Do not run `schema/create_schema.sh` with `--deploy` or modify shared databases. Preserve pre-existing unrelated work.
  - **Validation:** `V-1`, `V-3`; render and compare all configured entities, exercise both marked branches, and install each fixture function twice.

**Completion evidence:** All marked generated functions and the bundle carry the pre-limit flag; unmarked SQL and existing score columns remain unchanged.

### Area 2: Apply ambiguity to candidate conversion

**Objective:** Suppress automatic matches for flagged rows without exposing the flag or changing other candidate fields.

**Affected code:** `src/strategies/configured_classifier.py`, `tests/strategies/test_configured_classifier.py`, `tests/api/test_router.py`, `tests/api/test_record_selection.py`.

**Dependencies:** Area 1's fuzzy-row contract.

- [ ] `T2.1` **Change:** Use `label_ambiguous` during configured fuzzy candidate conversion.
  - **Target:** `ConfiguredClassifierStrategy.as_candidates` and its candidate helper in `src/strategies/configured_classifier.py`.
  - **Current -> required:** A single returned exact-label row may match even when another eligible row was omitted -> a flagged row always has `match: false`; an unflagged row retains the existing exact-label and label-similarity rules.
  - **Implementation:** Require a boolean flag on each fuzzy row passed to `as_candidates`; raise an explicit error for a missing or invalid flag so an old or incompatible schema cannot produce a success-shaped match. Retain the existing returned-row normalized-label count as an additional suppression check, since Python normalization and PostgreSQL `unaccent` are separate implementations. Do not add the flag to the candidate dictionary. Preserve direct single-row conversion and prefix-suggestion behavior for callers that do not supply fuzzy rows.
  - **Constraints:** Preserve score, ID, name, type, optional 500-character description, threshold behavior, and properties. A high description-derived score alone must not auto-match. Do not silently default a missing fuzzy flag to `false`.
  - **Validation:** `V-1`, `V-2`, `V-3`; test flagged and unflagged rows, missing and malformed flags, exact and similarity matches, description-only hits, and duplicate labels.
- [ ] `T2.2` **Change:** Add focused conversion and HTTP regressions.
  - **Target:** `tests/strategies/test_configured_classifier.py`, `tests/api/test_router.py`, `tests/api/test_record_selection.py`.
  - **Current -> required:** Existing tests check duplicates visible in a returned list -> tests also pass one flagged row with `limit: 1` through batch and interactive responses and compare unambiguous output to tier 1.
  - **Implementation:** Update fuzzy-row fixtures to include the boolean. Assert a single flagged exact match is false, an unflagged exact or sufficiently similar label still matches, description-only evidence does not, and missing/invalid fuzzy flags raise. Assert the exact candidate keys and values, including score, type and optional description, in both HTTP paths; assert `label_ambiguous` is absent and configured property metadata remains empty. Retain the existing case- and accent-duplicate checks.
  - **Validation:** `V-1`, `V-2`; the new cases must fail against the current implementation.

**Completion evidence:** Both reconciliation paths reject flagged matches and return the tier-1 candidate shape; incompatible fuzzy rows fail explicitly.

### Area 3: Verify the SQL-to-response contract

**Objective:** Demonstrate the correction with generated PostgreSQL functions and document the schema/code dependency.

**Affected code and documentation:** `tests/strategies/test_classifier_prelimit_integration.py` **NEW**, `docs/OPERATIONS.md`.

**Dependencies:** Areas 1 and 2.

- [ ] `T3.1` **Change:** Add a disposable PostgreSQL regression using generated SQL and synthetic data.
  - **Target:** `tests/strategies/test_classifier_prelimit_integration.py` **NEW**.
  - **Current -> required:** Mocked rows and template-text checks do not prove pre-limit counting -> run the generated zero-weight `feature_type` and weighted `rdb_code` functions in PostgreSQL and pass their returned rows through configured conversion and both HTTP paths.
  - **Implementation:** Mark the test `integration` and require `CLASSIFIER_SQL_INTEGRATION=1`. In a pytest fixture, start a uniquely identified, test-owned `docker.io/library/postgres:17-alpine` Podman container with `--network none` and `--rm`; use `podman exec -i` and `psql -X -v ON_ERROR_STOP=1` to create only synthetic source tables, `unaccent`, `pg_trgm`, and the same immutable unaccent wrapper as `schema/sql/utility.sql`. Apply the generated `feature_type.sql` and `rdb_code.sql` twice. Read function results as JSON rows, exercise the real configured conversion, and feed those rows into the existing mocked repository in batch and interactive `TestClient` requests. Stop only the container created by the fixture in a finalizer. When explicitly enabled, fail rather than skip if the image, Podman, startup, SQL, or cleanup fails.
  - **Cases:** For each function, insert case/accent variants such as `Cafe` and `Café`, plus a unique `Chert` row. At limits 1 and 2 or greater, assert the row cap, both ambiguity flags, and `match: false`; the unique exact result remains `match: true`. For the weighted branch also check a description-only eligible row and an ineligible same-label row, unchanged `label_sim`/`name_sim`, and no description-only auto-match. Verify `label_ambiguous` is absent from both HTTP responses.
  - **Constraints:** Use no shared database, source dump, host port, staging data, or production data. Do not claim the HTTP test uses a live application connection: SQL results are injected into the existing repository mock.
  - **Validation:** `V-3`; run the explicitly enabled test and require a pass with no skips.
- [ ] `T3.2` **Change:** Record the internal SQL contract and release dependency.
  - **Target:** `docs/OPERATIONS.md`, “Classifier schema, configuration, and code release order”.
  - **Current -> required:** Release guidance describes schema before code but not the new required return field -> state that generated marked functions must include `label_ambiguous` before the new application code is used; an old function is incompatible with the new converter.
  - **Implementation:** Keep the existing schema/config/code order and no-deployment scope. Explain that this field is internal, not an OpenRefine candidate property, and that rollback must keep schema and application contracts compatible.
  - **Validation:** `V-4`; check the guidance against generated SQL and the converter, and verify no deployment command was run.

**Completion evidence:** Real generated SQL proves the row cap and ambiguity rule for both scoring branches, HTTP tests preserve the public contract, and release guidance names the internal schema dependency.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (`P2-AC-11`) | `T1.1`, `T1.2`, `T2.1`, `T2.2`, `T3.1` | `V-1`, `V-3` | Eligible duplicate labels are marked before limiting; at limit 1 the one returned candidate is not a match; unique labels retain matching. |
| `PH1-AC-2` (`P2-AC-8`) | `T1.1`, `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-3`, `V-4` | Batch and interactive results retain fields, scoring, descriptions and property behavior; the SQL-only flag is absent. |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Generator, candidate, reconciliation and HTTP tests | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_generate_entity_schema.py tests/strategies/test_configured_classifier.py tests/test_reconcile.py tests/api/test_record_selection.py tests/api/test_router.py -q` | Both criteria | Updated existing and new cases pass; all marked renders match tracked output and unmarked output is unchanged. | Pass 2026-11-22: 146 existing tests passed; the new pre-limit cases are not yet present. |
| `V-2` | Property, suggestion and repository regressions | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_metadata.py tests/test_suggest.py tests/strategies/test_query.py -q` | `PH1-AC-2` | Property metadata, prefix suggestions, threshold bindings, and unrelated strategies remain unchanged. | Pass 2026-11-22: 78 tests passed. |
| `V-3` | Real generated SQL plus conversion and HTTP; `tests/strategies/test_classifier_prelimit_integration.py` **NEW** | `CLASSIFIER_SQL_INTEGRATION=1 PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/strategies/test_classifier_prelimit_integration.py -q` | Both criteria; `VM-1`, `VM-2` | All synthetic-database cases pass without skips; container cleanup succeeds. | Current `feature_type` SQL was installed in a network-isolated PostgreSQL 17 container on 2026-11-22: `Cafe`/`Café` returned one row at limit 1 and two at limit 10, with no ambiguity field. Existing conversion would auto-match the single exact row. Weighted and HTTP integration cases not run. |
| `V-4` | Focused quality and release guidance | `.venv/bin/ruff check src/strategies/configured_classifier.py tests/test_generate_entity_schema.py tests/strategies/test_configured_classifier.py tests/strategies/test_classifier_prelimit_integration.py tests/api/test_router.py tests/api/test_record_selection.py` and `.venv/bin/black --check` on the same Python paths; review `docs/OPERATIONS.md` against the generated function and converter. | Both criteria; release dependency | Lint and format checks pass; release guidance names the actual internal field and required order. | Pass 2026-11-22 for Ruff and Black on the four existing files `src/strategies/configured_classifier.py`, `tests/test_generate_entity_schema.py`, `tests/strategies/test_configured_classifier.py`, and `tests/api/test_record_selection.py`. New file and documentation change not yet checked. |

`V-3` requires the local Podman image and must not connect to an existing service or database. If the isolated database test cannot run, report that limitation and do not mark the phase complete.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Fuzzy SQL template | `schema/templates/entity.sql.jinja2` | `T1.1` | Both marked branches flag full eligible-set duplicates before limiting. |
| Generated classifier SQL | `schema/generated/{abundance_element,activity_type,age_type,alt_ref_type,colour,contact_type,country,data_type,data_type_group,dataset_submission_type,dating_uncertainty,ecocode_definition,ecocode_group,feature_type,horizon,identification_level,language,location_type,method_group,project_stage,project_type,property_type,property_type_group,rdb_code,record_type,relative_age_type,sample_description_type,sample_group_description_type,sample_location_type,sample_type,season,season_type,site_type,site_type_group,species_association_type,submission_state,submission_task_type,taxa_tree_author,taxa_tree_family,taxa_tree_genus,taxa_tree_order,unit,value_class,value_qualifier,value_type,value_type_item}.sql` | `T1.2` | All 46 marked files match the template; unmarked files are unchanged. |
| Deployment SQL bundle | `schema/__deploy__.sql` | `T1.2` | Bundle contains the regenerated functions; no deployment performed. |
| Configured candidate conversion | `src/strategies/configured_classifier.py` | `T2.1` | Flagged candidates do not match; missing or invalid fuzzy flags fail explicitly. |
| Focused tests | `tests/test_generate_entity_schema.py`, `tests/strategies/test_configured_classifier.py`, `tests/api/test_router.py`, `tests/api/test_record_selection.py` | `T1.1`, `T2.2` | `V-1` and `V-2` pass. |
| Disposable SQL regression | `tests/strategies/test_classifier_prelimit_integration.py` **NEW** | `T3.1` | `V-3` passes without skips and removes its own container. |
| Release guidance | `docs/OPERATIONS.md` | `T3.2` | Schema/code compatibility is explicit and `V-4` passes. |
| Phase tracker | This task plan | All tasks | Record task status, validation results, and any deviations during implementation. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| 1: Count eligible duplicates | Not started | None | Regenerate marked SQL and bundle. |
| 2: Apply ambiguity | Not started | Area 1 | Preserve both public response paths. |
| 3: Verify contract | Not started | Areas 1–2 | Use synthetic data in a test-owned isolated container. |

## Definition Of Done

- [ ] Both phase criteria have passing implementation and validation results recorded above.
- [ ] All tasks and deliverables are complete and the tracker is updated.
- [ ] `V-1` through `V-4` pass; `V-3` runs without skips.
- [ ] Duplicate and unique labels, row limits, weighted and zero-weight scoring, and the two response paths are regression-tested.
- [ ] Generated SQL, bundle, and release guidance agree; no deployment or shared-database write occurred.
- [ ] Deviations and follow-up work are documented; no unresolved question affects correctness or validation.

## Risks And Open Questions

- PostgreSQL cannot change a function's table return type with `CREATE OR REPLACE` alone. The generated template already drops both relevant signatures; verify repeated installation and account for its existing `CASCADE` behavior in the disposable test, not on a shared database.
- The new application must not accept fuzzy rows from the old function as unambiguous. Require the internal boolean and release schema before code; any rollback must restore a compatible pair.
