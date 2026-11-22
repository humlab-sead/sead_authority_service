# Fuzzy Reconciliation for Classifier Entities: Phase Plan

Source: [Fuzzy Reconciliation for Classifier Entities](CLASSIFIER_FUZZY_RECONCILIATION.md). This plan covers tier 1 only; [tier 2](../../CLASSIFIER_FUZZY_RECONCILIATION_TIER_2.md) owns `dimension` and context-scoped reconciliation.

## Summary

Deliver the configured-classifier path in three stages: establish the marked SQL contract, connect a shared strategy and migrate the two reference types, then enable the closed classifier inventory with deployment and data checks. Each stage must preserve generated contracts for unmarked entities.

## Problem

Most classifier types cannot be reconciled because each currently needs a separate strategy and resource specification. Existing generated views and resource queries already disagree for `feature_type` and `data_type`. A broad registration change without schema, manifest, and configuration checks could advertise types that fail at runtime.

## Scope

This plan covers tier-1 classifier SQL generation, service configuration, generic strategy registration, explicit support status, reference migrations, the approved inventory, and validation across application and container configuration. It excludes specialized strategies, `dimension`, tier-2 matching, production data changes, and deployment.

## Current Position

- The uncommitted Phase 1 worktree adds the `reconciliation: simple` generator branch; both reference entities are marked in application, test, and container configuration.
- The uncommitted Phase 2 worktree replaces the supported-type tuple with registration metadata. Static `CLASSIFIER_KEYS` contains only `data_type` and `feature_type`.
- The uncommitted Phase 2 worktree migrates the two reference types to generated specifications and removes their separate strategy/resource files. Verify and preserve this worktree before expansion; it is not deployed behavior.
- The [issue #43 interim inventory](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123) records 45 planned generic keys and eight exclusions. Read-only checks on the `SEAD TNG (9023)` profile's `sead_staging` database found that only `rdb_code` passes both description-population gates; the other three code-label types remain label-only.

## Phase Plan

### Phase 1: Establish the Marked SQL Contract

**Goal**

Generate a stable view and fuzzy-function contract for marked classifiers without changing unmarked SQL.

**Focus**

- Gate view aliases, description returns, optional scoring and indexing on `reconciliation: simple`; leave zero-weight descriptions available for display without scanning or scoring them.
- Pass service-configured label and description thresholds as explicit function parameters; keep exact normalized labels and label-only matching behavior independent of `pg_trgm` settings.
- Check the declared description column against the source schema before exposing it, including the `dating_uncertainty` discrepancy.

**Depends On**

- The proposal's marked-entity and function contracts; no runtime registration change is needed to validate generated SQL.

**Outputs**

- A generator contract usable by the shared strategy, with verified unchanged output for unmarked entities.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-11`) Unmarked views, function signatures, scoring, and existing resource SQL contracts remain unchanged.
- `PH1-AC-2` (from `P-AC-4`, `P-AC-13`) Marked functions return descriptions when available; only non-zero weights add description scoring, a description predicate, and a description index.
- `PH1-AC-3` (from `P-AC-15`) Generated functions use explicit service-provided thresholds, and changing session `pg_trgm` settings does not change results.

**Validation Milestones**

- `VM-1` Compare generated marked and unmarked SQL contracts, including the unchanged `site` view and `method` function (`PH1-AC-1`, `PH1-AC-2`).
- `VM-2` Verify threshold-driven candidate inclusion and database-setting independence against generated functions (`PH1-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-4`, `P-AC-11`, `P-AC-13`, and `P-AC-15`; keep the marker exclusive to the generic path and preserve unmarked generated output. Verify the physical description columns before describing them as available. Threshold and weight decisions are fixed by the proposal.

**Readiness**

Ready for a task plan.

### Phase 2: Connect the Shared Runtime and Reference Types

**Goal**

Prove the generated contract end to end using `feature_type` and `data_type`, while making manifest support status explicit.

**Focus**

- Resolve specifications and details SQL from marked table specs, register static generic keys without reading configuration at import time, and retain the existing public type IDs.
- Return at most 500 characters of description in candidates and full descriptions in details; derive `match` only from label similarity and suppress automatic matches for duplicate normalized labels.
- Migrate the two reference types, preserve `sampling_context` and other specialized behavior, and derive `supportedTypes` from explicit registration status.
- Validate classifier specs and thresholds after configuration loads, so invalid runtime configuration fails startup with a named error.

**Depends On**

- Phase 1's verified generated view and fuzzy-function contract.

**Outputs**

- A working shared classifier path for the reference types, declared support metadata for every registration, and startup validation for runtime configuration.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`, `P-AC-7`, `P-AC-8`) Both reference types use generic registration and generated details SQL without their redundant resource or strategy files; specialized details remain unchanged and `dimension` stays deferred.
- `PH2-AC-2` (from `P-AC-3`, `P-AC-5`, `P-AC-6`) Exact unique labels auto-match; duplicate normalized labels and description-only hits do not; candidate descriptions are capped at 500 characters and details remain full length.
- `PH2-AC-3` (from `P-AC-10`) Every registration declares a valid support status, the manifest uses those declarations, and an undeclared status fails validation.
- `PH2-AC-4` (from `P-AC-12`, `P-AC-16`) Invalid classifier specs or missing/out-of-range configured thresholds fail startup with a named error.

**Validation Milestones**

- `VM-3` Exercise both reference types' candidates and details against generated SQL, with specialized regression coverage (`PH2-AC-1`).
- `VM-4` Verify exact-label, duplicate-label, description-only, and long-description response behavior (`PH2-AC-2`).
- `VM-5` Verify manifest statuses, drift checks, and named startup errors for invalid specifications and thresholds (`PH2-AC-3`, `PH2-AC-4`).

**Task-Plan Handoff**

- Use `P-AC-2`, `P-AC-3`, `P-AC-5` through `P-AC-8`, `P-AC-10`, `P-AC-12`, and `P-AC-16`. Preserve static registration, `Strategies.items`, existing type IDs, and `sampling_context` details. Keep test and container configuration aligned when runtime settings are introduced.

**Readiness**

Ready for a task plan after Phase 1's output is available.

### Phase 3: Expand the Closed Inventory and Validate Release Inputs

**Goal**

Enable all approved tier-1 classifiers and verify that schema, configuration, and application code agree.

**Focus**

- Mark and register the approved classifier set with a two-direction drift check; keep excluded and specialized types out of generic registration and use the issue #43 interim inventory for exclusion reasons until its checked-in register is delivered.
- Enable non-zero description weight only for `rdb_code`; keep `age_type`, `relative_age_type`, and `value_qualifier` at zero weight after their failed population checks.
- Keep application, test, and independently mounted container configuration consistent; validate generated schema, details, representative reconciliation behavior, and the required schema-then-config-then-code release order without deploying.

**Depends On**

- Phase 2's working generic strategy, startup checks, and support-status manifest.
- The recorded read-only population results and the decision to enable only `rdb_code`; recheck its counts against the generated view before merge.

**Outputs**

- A validated closed inventory, issue #43 interim exclusion reasons and recorded population results, synchronized deployment inputs, and release-order guidance.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-9`) Approved generic keys appear in both manifest lists, marker and key lists agree, and excluded classifiers are not generically registered and have recorded reasons.
- `PH3-AC-2` (from `P-AC-4`, `P-AC-5`, `P-AC-14`) Only `rdb_code` uses non-zero description weight after passing the population gate; the other three code-label classifiers stay at zero weight. Description-only hits never auto-match and exact label matches retain priority.
- `PH3-AC-3` (from `P-AC-7`, `P-AC-11`, `P-AC-12`, `P-AC-16`) Generated details and fuzzy queries work for every marked type, unmarked contracts remain unchanged, and container classifier/threshold configuration matches application configuration.

**Validation Milestones**

- `VM-6` Compare the closed marker/key inventory and manifest with the recorded exclusions (`PH3-AC-1`).
- `VM-7` Recheck `rdb_code` population against the generated view, retain the recorded failed results for the other three keys, and verify ranking and match flags (`PH3-AC-2`).
- `VM-8` Check schema and configuration parity, run disposable-schema details/fuzzy checks for each marked type, and reconcile representative name-only, description, code-label, and duplicate-label cases (`PH3-AC-3`).

**Task-Plan Handoff**

- Use `P-AC-1`, `P-AC-2`, `P-AC-4`, `P-AC-5`, `P-AC-7`, `P-AC-9`, `P-AC-11`, `P-AC-12`, `P-AC-14`, and `P-AC-16`. Use the issue #43 interim register and the four recorded staging counts; recheck weighted `rdb_code` against the generated view before merge. Preserve the proposal's exclusions and schema/config/code release order.

**Readiness**

Ready for a task plan. The four results and the decision to leave failed keys at zero weight are recorded; generated-view checks remain implementation validation.

## Cross-Phase Rules

- Never change generated SQL for unmarked entities or alter specialized strategy behavior to accommodate generic classifiers.
- Keep registration static and ensure runtime configuration and the registry agree before publishing a type as supported.
- Treat schema generation, mounted configuration, and application code as distinct release inputs in that order; this plan does not authorize deployment.

## Validation Strategy

Validate generated SQL contracts and threshold behavior first (`VM-1`–`VM-2`), then reference HTTP behavior and startup/manifest checks (`VM-3`–`VM-5`). Only then validate the complete marked set with the recorded population decision, a generated-view recheck, disposable-schema checks, and representative reconciliation cases (`VM-6`–`VM-8`). Exact tests, fixtures, and commands belong in each phase task plan.