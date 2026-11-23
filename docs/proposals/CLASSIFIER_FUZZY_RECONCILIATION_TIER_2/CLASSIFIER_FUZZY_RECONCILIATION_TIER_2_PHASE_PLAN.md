# Tier 2 Context-Scoped Reconciliation: Phase Plan

Source: [Tier 2 — Context-Scoped Classification and Lookup Reconciliation](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2.md).
Task plans: [Phase 1](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2_PHASE_1_TASK_PLAN.md) and [Phase 2](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2_PHASE_2_TASK_PLAN.md).

## Summary

First correct duplicate-label detection for existing configured classifiers. Then add optional parent context and configured lookup reconciliation using that safe matching behavior. The proposal's decisions are approved for planning; the proposal itself is still marked proposed.

## Problem

Before Phase 1, duplicate detection saw only the rows returned after the SQL limit, so an omitted duplicate could cause an incorrect automatic match. Phase 1 corrects that locally. Parent-scoped labels still need context to distinguish candidates, and label-bearing lookups need a conservative configured reconciliation path.

## Scope

This plan covers pre-limit ambiguity detection, optional parent context, thirteen label-bearing lookups, alternate-identity query compatibility, configuration validation, and schema and configuration parity. It excludes `dimension` reconciliation and schema repair, `coordinate_method_dimension`, `contact`, `abundance_element_group`, `dataset`, `taxa`, specialized strategies, production data changes, and deployment.

## Current Position

- Phase 1's pre-limit duplicate detection and unscoped compatibility are implemented and validated locally, including weighted same-label eligibility in isolated PostgreSQL.
- The configured path currently registers `simple` classifiers. The proposal adds the `lookup` marker and optional `scope_columns` without adding per-entity strategies.
- The existing `method` alternate-identity query returns the configured `method_id` and exposes `method_abbreviation` as its property identifier. Both must remain usable.
- The [reconciliation type inventory](../../RECONCILIATION_TYPE_INVENTORY.md) is available locally. For Phase 2 parity, the deployment input will be a release candidate produced by the existing container setup in an isolated directory.

## Phase Plan

### Phase 1: Correct Duplicate Matching Before the Limit

**Goal**

Prevent an existing configured classifier from automatically matching an ambiguous label when the SQL limit hides another eligible row.

**Focus**

- Detect duplicate normalized labels across the full eligible set before limiting rows, and carry ambiguity internally to candidate conversion.
- Preserve the row cap, label-based scoring and automatic matching for unambiguous results, and the existing public response for unscoped classifiers.

**Depends On**

- The tier-1 configured classifier and generated fuzzy-function contracts.

**Outputs**

- A validated ambiguity rule for existing classifiers that Phase 2 can apply after context filtering.

**Acceptance Criteria**

- `PH1-AC-1` (from `P2-AC-11`) For existing configured classifiers, duplicate normalized labels are detected before limiting; with `limit: 1`, at most one row is returned and it cannot auto-match if another eligible row has the same normalized label.
- `PH1-AC-2` (from `P2-AC-8`) Unscoped classifiers retain tier-1 public result shape, scoring, and property behavior apart from the duplicate-suppression correction; the internal ambiguity flag is not exposed in candidate responses.

**Validation Milestones**

- `VM-1` Exercise duplicate and unique labels with limits including one, and verify both the row cap and match flags (`PH1-AC-1`).
- `VM-2` Compare unscoped candidate responses, scoring, and properties with tier 1, allowing only the intended duplicate-match correction (`PH1-AC-2`).

**Task-Plan Handoff**

- Use `P2-AC-8` and `P2-AC-11`. Keep the limit as a maximum row count, not a count of distinct labels; do not expand results to include duplicates. Preserve the tier-1 default description weight of zero and label-based automatic-match rule.

**Readiness**

Complete locally; validation is recorded in the [Phase 1 task plan](./CLASSIFIER_FUZZY_RECONCILIATION_TIER_2_PHASE_1_TASK_PLAN.md).

### Phase 2: Add Context and Configured Lookups

**Goal**

Use optional parent context to reconcile scoped classifiers and register label-bearing lookups without weakening ambiguity protection.

**Focus**

- Extend the configured `simple` and `lookup` path with validated optional scope, readable parent context, context filtering and fallback.
- Register the thirteen label-bearing lookups, generate compatible alternate-identity queries, and keep production, test, and container configuration aligned.
- Preserve excluded and specialized types and verify their recorded exclusion reasons.

**Depends On**

- Phase 1's validated pre-limit ambiguity detection and unscoped compatibility.
- The approved candidate configuration check, using the same repository revision as the application and test inputs.

**Outputs**

- Context-aware classifier and lookup reconciliation with validated generated schema, candidate responses, startup checks, and configuration parity.

**Acceptance Criteria**

- `PH2-AC-1` (from `P2-AC-1`, `P2-AC-9`) Valid `simple` and `lookup` scopes expose a `context` property and normalized parent context; unscoped entries remain valid. An unresolved scope target or lookup without a label fails startup with a named error.
- `PH2-AC-2` (from `P2-AC-2`) All thirteen label-bearing lookups use `lookup` and never score or auto-match on descriptions. Only `feature` and `taxa_common_names` use parent context among lookups; a nonzero lookup description weight is rejected.
- `PH2-AC-3` (from `P2-AC-3`, `P2-AC-11`) Supplied context filters before ranking, ambiguity detection, and the row limit. Matching results expose context in the description and set `context_match: true`. If no label candidate matches the supplied context, at most the requested number of unfiltered suggestions is returned, each with `match: false` and `context_match: false`; duplicates within the selected context cannot auto-match even at `limit: 1`.
- `PH2-AC-4` (from `P2-AC-6`) Generated alternate-identity results use the configured ID field and preserve property identifiers; `method` candidates continue to convert successfully.
- `PH2-AC-5` (from `P2-AC-7`) `dimension` configuration and schema are unchanged; `coordinate_method_dimension` is not a supported reconciliation type. `contact`, `abundance_element_group`, `dataset`, `taxa`, and specialized strategies remain unchanged, with exclusion reasons retained in the register tracked by [issue #43](https://github.com/humlab-sead/sead_authority_service/issues/43).
- `PH2-AC-6` (from `P2-AC-8`, `P2-AC-11`) Unscoped entities retain tier-1 public result shape, scoring, and properties apart from corrected duplicate suppression. Scoped entities without a context property retain label-search behavior with the same correction, omit `context_match`, and respect the row cap.
- `PH2-AC-7` (from `P2-AC-10`) Classifier and lookup configuration is identical across production, test, and deployment container configuration files.

**Validation Milestones**

- `VM-3` Check generated scoped views and functions, context property exposure, and named startup failures for invalid scopes, missing lookup labels, and nonzero lookup description weights (`PH2-AC-1`, `PH2-AC-2`).
- `VM-4` Exercise matching context, unmatched-context fallback, missing context, duplicate labels within and across contexts, and `limit: 1` through the endpoint. Verify the description and `context_match` values and row cap (`PH2-AC-3`, `PH2-AC-6`).
- `VM-5` Verify generated alternate-identity results through candidate conversion, including `method`, and compare unscoped behavior with tier 1 (`PH2-AC-4`, `PH2-AC-6`).
- `VM-6` Check lookup registration, ambiguous `rdb_system` and `taxa_synonyms` results, exclusions and their register, and configuration parity across the repository, test, and generated deployment candidate (`PH2-AC-2`, `PH2-AC-5`, `PH2-AC-7`).

**Task-Plan Handoff**

- Use `P2-AC-1`, `P2-AC-2`, `P2-AC-3`, and `P2-AC-6` through `P2-AC-11`. Apply scope to the fourteen context-dependent classifiers and the two named lookups. Keep `rdb_system` and `taxa_synonyms` unscoped because parent labels omit parts of their unique keys.
- Join parent labels in scope declaration order using left joins; a null context cannot satisfy a supplied context. Parent labels are display values, not unique keys. Put context first in the existing 500-character candidate description without changing the candidate name or label scoring.
- Use `lab_name` as the `dating_lab` label. Rows with a null lab name cannot be found by label; no derived label or fallback is authorized.
- Compare complete marked specifications against a fresh deployment candidate generated by container setup. The deployment operator separately checks the actual mounted configuration during rollout; candidate parity does not verify a running host.
- Do not add per-entity strategies or a generic derived-label expression. Keep generated SQL and specialized behavior compatible with the proposal's exclusions.

**Readiness**

Ready for the Phase 2 task plan; Phase 1 is validated locally and the deployment parity method is approved.

## Cross-Phase Rules

- Keep ambiguous labels as suggestions, including duplicates within a supplied context; never treat parent labels as unique keys.
- Preserve tier-1 behavior for unscoped entities except for the duplicate-suppression correction.
- Generate schema from the configured path and keep application, test, and deployment configuration consistent. This plan does not authorize deployment.

## Validation Strategy

Validate the safety correction and unscoped compatibility first (`VM-1`–`VM-2`). Then check generated schema and startup validation, exercise context and fallback through HTTP, and run alternate-identity, exclusion, and configuration-parity regressions (`VM-3`–`VM-6`). Exact commands, fixtures, and assertions belong in the phase task plans.
