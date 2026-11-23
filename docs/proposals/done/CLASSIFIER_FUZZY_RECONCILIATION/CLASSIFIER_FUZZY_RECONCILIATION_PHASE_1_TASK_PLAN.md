# Fuzzy Reconciliation for Classifier Entities: Phase 1 Task Plan

## Phase Summary

**Phase:** 1, Establish the Marked SQL Contract. **Readiness:** Validated for implementation; database execution requires a disposable database, not staging. [Proposal](CLASSIFIER_FUZZY_RECONCILIATION.md) | [Phase plan](CLASSIFIER_FUZZY_RECONCILIATION_PHASE_PLAN.md#phase-1-establish-the-marked-sql-contract).

**Goal:** Generate marked-classifier views and fuzzy functions while preserving all unmarked output. Phase 2 owns runtime strategy calls, candidate `match`, startup validation, and reference migrations; Phase 3 owns the full inventory and population gate. Do not mark production entities in this phase merely to exercise the template.

**Phase criteria**

1. [x] `PH1-AC-1` (from `P-AC-11`): Unmarked views, function signatures, scoring, and existing resource SQL contracts remain unchanged.
2. [x] `PH1-AC-2` (from `P-AC-4`, `P-AC-13`): Marked functions return descriptions when available; only non-zero weights add description scoring, a description predicate, and a description index.
3. [x] `PH1-AC-3` (from `P-AC-15`): Marked functions compare against explicit service-provided threshold parameters; changing session `pg_trgm` settings does not change results.

**Dependencies and constraints:** Keep the existing function calls with two arguments usable through parameter defaults. Do not change the `site` view, the `method` function, or specialized resource SQL. Preserve existing entity IDs, `extra_columns`, `alternate_identity_column`, materialized views, joins, and filters. No database deployment or production data write is authorized.

## Repository Findings

**Repository basis:** `dev` at `9df7b7c`, checked 2026-11-14. The untracked phase-plan document was considered; no implementation or test changes were present in `git status --short`. Graphify identified the generator but returned a broad, truncated result; the findings below come from current files. The read-only SEAD staging MCP connection failed, so live column availability is unverified.

| Source | Verified finding | Planning implication |
| --- | --- | --- |
| `src/scripts/generate_entity_schema.py::generate_trigram_sql`, `::main` | Passes the whole entity and `get_trigram_config()` to `schema/templates/entity.sql.jinja2`; CLI exposes `--all-entities`, `--force`, `--config`, and `--output-dir`. | Branch inside the existing template. The proposal's example `--all` is not the current CLI flag; use `--all-entities`. |
| `schema/templates/entity.sql.jinja2` | Emits physical description column names, three-column fuzzy returns, and `s.norm_label % pq.q`; no marker or description scoring exists. | Gate every change on `reconciliation: simple`; use explicit threshold comparisons in that branch only. |
| `schema/generated/site.sql`, `schema/generated/method.sql`, `src/resources/method.yml` | Tracked generated files use the existing two-argument function and physical description names; the method resource calls that function. | Byte-compare unmarked generated output against the tracked baseline; preserve those contracts. |
| `src/strategies/query.py::BaseRepository.find`, `::AbstractRepository.get_find_fuzzy_sql`, `src/strategies/strategy.py::ReconciliationStrategy.as_candidate` | The default query passes two arguments and returns row columns as dictionaries; the base strategy currently uses `name_sim` for both score and automatic match. | Marked SQL must retain two-argument calls through defaults and expose label similarity separately when description scoring changes `name_sim`; Phase 2 changes candidate logic. |
| `config/config.yml`, `tests/config/config.yml`, `deployment/container/config/config.yml` | All three define `options.auto_accept_threshold`, but none defines reconciliation thresholds. | Add identical explicit threshold values in all three; consuming and validating them at startup belongs to Phase 2. |
| `config/entities.yml`, `tests/config/entities.yml`, `schema/generated/dating_uncertainty.sql` | `dating_uncertainty.description_column` is `description`; current generated SQL refers to it. | Do not remove the setting based solely on the target-model omission. Verify the physical column before marking this entity in Phase 3. |
| `sead_shape_shifter/resources/target_models/sead_standard_model.yml::dating_uncertainty`, `sead_change_control/resources/tables_and_columns.csv` | The target model omits `description`; the checked-in database column catalogue lists `tbl_dating_uncertainty.description`. | Record this cross-repository disagreement and check `information_schema.columns` on the intended database before promoting the classifier. If absent, stop and report rather than silently changing the contract. |
| `tests/conftest.py`, `pyproject.toml` | Pytest uses `tests/test_*.py`; integration and manual directories are excluded from default collection. No generator-focused test exists. | Add one focused generator test file with temporary configuration and output; use a separate disposable-database method for SQL behavior. |

## Scope

**In scope:** The marked branch of the SQL template, service threshold declarations in application/test/container configuration, template rendering tests, unmarked SQL parity, and a disposable-database threshold check. Synthetic entity specs exercise description present/absent, zero/positive weight, and unmarked paths.

**Out of scope:** Production `config/entities.yml` markers or weights, generated SQL changes for existing entities, runtime query and candidate code, `CLASSIFIER_KEYS`, startup threshold validation, population checks, schema deployment, and changes to either cross-repository schema reference.

## Work Breakdown

### Area 1: Declare Threshold Inputs

**Objective:** All service configuration variants declare the approved SQL threshold values without changing current strategy behavior.

**Affected code:** `config/config.yml`, `tests/config/config.yml`, `deployment/container/config/config.yml`.

**Dependencies:** Proposal's fixed `0.30` label and `0.50` description thresholds; independent of SQL implementation.

**Tasks:**

- [x] `T1.1` **Change:** Add `options:reconciliation:label_threshold` and `description_threshold` to the three existing configuration files.
  - **Target:** `config/config.yml::options`, `tests/config/config.yml::options`, `deployment/container/config/config.yml::options`.
  - **Current -> required:** Only `auto_accept_threshold` exists -> all three have the same explicit reconciliation thresholds.
  - **Implementation:** Set the approved values `0.30` and `0.50`; do not change unrelated configuration or introduce per-entity thresholds. Phase 2 passes and validates these values at runtime.
  - **Constraints:** The template's SQL parameter defaults must match these declared values so existing two-argument callers keep working until Phase 2.
  - **Validation:** `V-1` and `V-4` passed on 2026-11-14.

**Completion evidence:** The three parsed YAML files agree on both thresholds; existing configuration tests pass.

### Area 2: Generate the Marked SQL Contract

**Objective:** Marked entities produce the approved aliases, return columns, optional scoring, and parameterized filtering without modifying any unmarked output.

**Affected code:** `schema/templates/entity.sql.jinja2`; existing `src/scripts/generate_entity_schema.py::generate_trigram_sql` supplies the entity context and should not need modification.

**Dependencies:** `T1.1` for the parameter defaults; keep all existing unmarked template branches intact.

**Tasks:**

- [x] `T2.1` **Change:** Render `description` and `norm_description` only for marked entities with a configured description; add a description trigram index only for positive weights.
  - **Target:** `schema/templates/entity.sql.jinja2` view and index blocks.
  - **Current -> required:** The physical description name is exposed without a normalized alias -> marked views expose `description` and `norm_description`; absent descriptions expose neither.
  - **Implementation:** Keep the physical ID column and `label`; derive normalized description from the configured physical column. Use the existing materialized/non-materialized index location pattern when a description index is enabled. Preserve `extra_columns`, alternate identity, joins, filters, and unmarked rendering.
  - **Constraints:** A missing or zero weight produces no description index; positive weight is meaningful only with a real description column. Do not mark `dating_uncertainty` based on the conflicting schema references.
  - **Validation:** `V-2` and `V-3` passed on 2026-11-14; generated SQL was installed twice and both description index branches were exercised in the disposable database.

- [x] `T2.2` **Change:** Add a marked-only fuzzy function with explicit label and description thresholds and optional description ranking.
  - **Target:** `schema/templates/entity.sql.jinja2` function signature, return columns, predicate, scoring, and ordering blocks.
  - **Current -> required:** `%` uses a session threshold and only `name_sim` is returned -> marked predicates compare `similarity` and, with positive weight, `strict_word_similarity` against `p_label_threshold` and `p_description_threshold` with defaults `0.30` and `0.50`.
  - **Implementation:** Preserve exact normalized-label score `1.0` and label-only `name_sim` when weight is absent or zero. With positive weight, compute combined `name_sim` and expose `label_sim` separately for Phase 2's label-only auto-match; return the description when present, without scoring it at weight zero. Retain the three-column return for marked entities without a description, and make function replacement/repeated generation unambiguous when the signature gains defaulted parameters.
  - **Constraints:** No `%`, `<<%`, or other `pg_trgm`-GUC-dependent predicate in the marked branch. An exact label must rank ahead of a description-driven candidate; no changes to unmarked function signature or body. The proposal's illustrative four-column return omits the label similarity required for its own `match` rule; expose that extra value only when combined scoring requires it, while leaving `name_sim` as the display score.
  - **Validation:** `V-2` and `V-3` passed on 2026-11-14; executable checks confirmed threshold behavior, exact-label priority, description-only inclusion, session-setting independence, and repeatable function creation.

**Completion evidence:** Synthetic marked SQL has the promised aliases and scored/unscored variants; regenerated unmarked SQL equals the tracked baseline.

### Area 3: Prove SQL and Regression Behavior

**Objective:** Tests make the marked-only contract and unchanged unmarked output reproducible before Phase 2 uses them.

**Affected code:** `tests/test_generate_entity_schema.py` **NEW**; tracked `schema/generated/site.sql` and `schema/generated/method.sql` are comparison inputs, not edit targets.

**Dependencies:** `T2.1` and `T2.2`.

**Tasks:**

- [x] `T3.1` **Change:** Add generator tests for the SQL variants and unmarked parity.
  - **Target:** `tests/test_generate_entity_schema.py` **NEW**, using `src/scripts/generate_entity_schema.py::generate_trigram_sql` and pytest `tmp_path`.
  - **Current -> required:** No focused schema-generation tests -> tests render synthetic specs with no description, description and missing/zero weight, and description with weight `0.15`; they assert view aliases, return-column shape, index/predicate presence or absence, and explicit comparisons. Check parsed threshold parity across the three configuration files. Render the current `site`, `method`, and `location` specs and compare their output byte-for-byte with tracked generated SQL; include an unmarked filter-parameter case so the existing contract is retained.
  - **Constraints:** Tests must not overwrite tracked artifacts or require a live connection. If tracked files already differ from a fresh render before implementation, record that baseline drift and compare against a captured pre-change render rather than silently updating them.
  - **Validation:** `V-1`, `V-2`, and `V-5` passed on 2026-11-14.

- [x] `T3.2` **Change:** Verify generated SQL behavior on a disposable database.
  - **Target:** Output of `schema/templates/entity.sql.jinja2` generated by `src/scripts/generate_entity_schema.py`; no production schema or application test fixture is modified.
  - **Current -> required:** SQL behavior is untested -> execute generated marked functions twice in the isolated database, using synthetic labeled rows with identical descriptions, distinct labels, and a description-only term. Compare explicit low/high label thresholds, and compare the same call under two different `pg_trgm.similarity_threshold` and `pg_trgm.strict_word_similarity_threshold` settings.
  - **Constraints:** Use a database with `pg_trgm` and `authority.immutable_unaccent` available. Check actual columns before loading any real-table spec; never deploy generated SQL to staging or production as part of this phase. If the disposable database is unavailable, report `V-3` as unverified, not passed.
  - **Validation:** `V-3` and `V-5` passed on 2026-11-14 using a temporary local PostgreSQL 16 container; the container was stopped after the test.

**Completion evidence:** Focused generator tests pass; the disposable-database check confirms thresholds and setting independence, or is explicitly recorded as an unmet phase gate.

## Acceptance-Criteria Coverage

| Criterion (source) | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (`P-AC-11`) | `T2.1`, `T2.2`, `T3.1` | `V-2` | Tracked unmarked SQL remains byte-identical; specialized resource queries still reference available columns/functions. |
| `PH1-AC-2` (`P-AC-4`, `P-AC-13`) | `T2.1`, `T2.2`, `T3.1`, `T3.2` | `V-2`, `V-3` | Description returned without scoring at zero; only positive weight adds scoring, predicate, and index. |
| `PH1-AC-3` (`P-AC-15`) | `T1.1`, `T2.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-3` | Explicit threshold parameters change inclusion; session setting changes do not. Runtime parameter passing follows in Phase 2. |

## Validation And Testing

| ID | Check and target | Command or executable method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Threshold YAML parity | Parse `options.reconciliation` with `yaml.safe_load` in `tests/test_generate_entity_schema.py`; `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_generate_entity_schema.py -q` | `T1.1`, `PH1-AC-3` | All three configurations specify `0.30` and `0.50`. | Pass: included in the focused generator test run on 2026-11-14. |
| `V-2` | Template contracts and tracked unmarked parity | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/test_generate_entity_schema.py -q` | `PH1-AC-1`, `PH1-AC-2`, `PH1-AC-3`; `VM-1` | Synthetic rendered variants have correct columns and predicates; regenerated unmarked SQL matches captured baseline. | Pass: 10 focused generator tests; separate `--all-entities` render matched all 28 tracked SQL files exactly on 2026-11-14. |
| `V-3` | SQL execution and parameter/GUC independence | In an isolated database, load pg_trgm/normalization prerequisites and generated synthetic view/function SQL; query known rows using the same explicit threshold arguments before and after changing both relevant session settings; repeat installation to check function replacement. | `PH1-AC-2`, `PH1-AC-3`; `VM-2` | Low/high label threshold changes returned rows; same explicit thresholds give identical rows/scores regardless of session settings; exact label ranks first. | Pass: temporary local PostgreSQL 16 database; generated script installed twice, threshold and ranking assertions passed, and results matched with both `pg_trgm` settings at 0 and 1 on 2026-11-14. |
| `V-4` | Existing configuration regression | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider tests/configuration/test_config.py -q` | `T1.1` | Existing config behavior remains intact. | Pass: 8 tests on 2026-11-14. |
| `V-5` | Syntax, formatting, and supported generator CLI | `.venv/bin/ruff check tests/test_generate_entity_schema.py` and `.venv/bin/black --check tests/test_generate_entity_schema.py`; `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python src/scripts/generate_entity_schema.py --help` | `T3.1`, `T3.2` | Focused test file passes quality checks; CLI confirms `--all-entities` and `--output-dir`. | Pass: Ruff, Black, and generator CLI checks on 2026-11-14. |

During implementation, regenerate with `.venv/bin/python src/scripts/generate_entity_schema.py --all-entities --force` only after capturing the pre-change unmarked baseline. This writes tracked generated files; review the resulting diff and retain only intentional marked-entity output. Use `--output-dir` and a temporary directory for speculative renders.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Service threshold values | `config/config.yml`, `tests/config/config.yml`, `deployment/container/config/config.yml` | `T1.1` | Parsed values agree. |
| Marked view and fuzzy-function branch | `schema/templates/entity.sql.jinja2` | `T2.1`, `T2.2` | Marked variants pass focused tests; unmarked output remains unchanged. |
| Generator contract tests | `tests/test_generate_entity_schema.py` **NEW** | `T3.1` | `V-1` and `V-2` pass. |
| SQL execution record (no repository file required) | Disposable database test result | `T3.2` | `V-3` records results; no staging/production changes. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Declare threshold inputs | Done | None | `T1.1`, `V-1`, and `V-4` passed. |
| Area 2: Generate marked SQL | Done | Area 1 | `T2.1`, `T2.2`, `V-2`, and `V-3` passed. |
| Area 3: Prove behavior | Done | Area 2 | `T3.1`, `T3.2`, `V-3`, and `V-5` passed; temporary database stopped. |

## Definition Of Done

- [x] `PH1-AC-1` through `PH1-AC-3` have task and validation evidence (`V-1` through `V-3`).
- [x] All three areas and listed deliverables are complete; tests and focused quality checks pass (`V-1`, `V-2`, `V-4`, `V-5`).
- [x] `site`, `method`, `location`, and all 28 generated SQL files match their pre-change tracked versions; specialized resource files were not changed.
- [x] Marked SQL is checked in a disposable database, including repeated creation, explicit threshold behavior, and session-setting independence (`V-3`).
- [x] Configuration declarations match generated parameter defaults; no production entity was marked or deployed as part of Phase 1.
- [x] Record deviations and stop for review if current source or deployed schema contradicts the verified repository basis; do not broaden Phase 1 or invent another contract.

## Risks And Open Questions

- The proposal's example `returns table` omits `label_sim`, while its scored query selects it and its approved auto-match rule requires it. This plan keeps the three-column no-description return and exposes label similarity separately only when description scoring is enabled; `name_sim` remains the combined display score. Verify generated SQL column counts in `V-2`/`V-3` before Phase 2 consumes the result.
- The target model omits `tbl_dating_uncertainty.description`, but the checked-in database column catalogue includes it. Staging was unreachable during planning. This does not block synthetic Phase 1 SQL work; before this entity is marked, confirm its column on the intended database and stop if the physical schema conflicts with the configured definition.
- The current template drops the old two-argument function before creating it. A marked function with additional defaulted arguments needs repeatable replacement that does not leave an ambiguous overload; `V-3` must execute the generated script twice.