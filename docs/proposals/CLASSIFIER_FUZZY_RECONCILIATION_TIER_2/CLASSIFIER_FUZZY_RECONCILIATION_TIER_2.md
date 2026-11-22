# Proposal: Tier 2 — Context-Scoped Classification and Lookup Reconciliation

## Status

- Confirmed feature / change request
- Tier 2 of a two-tier change. Tier 1, [Fuzzy Reconciliation for Classifier Entities](../done/CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION.md), is implemented and validated across Phases 1–3. Its completion records include disposable-database and HTTP checks; production deployment was out of scope. See the [Phase 1](../done/CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION_PHASE_1_TASK_PLAN.md), [Phase 2](../done/CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION_PHASE_2_TASK_PLAN.md), and [Phase 3](../done/CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION_PHASE_3_TASK_PLAN.md) task plans.
- The completed [One Contract for Simple Classifiers](../done/SIMPLE_CLASSIFIER_CONTRACT/SIMPLE_CLASSIFIER_CONTRACT.md) is the baseline for generated views and functions.
- Acceptance criteria use the `P2-AC-<N>` prefix to distinguish them from tier-1 criteria.
- Scope: safe duplicate handling, parent-context matching, and configured lookup reconciliation
- Goal: extend the configured path without adding per-entity strategy classes or generic SQL-label expressions

## Summary

Tier 1's Python code suppresses duplicate-label matches only among rows returned by the SQL function. Since the function applies its row limit first, a limit of one can hide duplicates and allow an incorrect automatic match. Tier 2 must detect ambiguity before limiting the returned rows.

Use the existing `simple` and `lookup` markers, with optional `scope_columns` on either. Apply supplied context before ranking and limiting, show the context in candidate descriptions, and report whether context matched. Register labeled lookups through the configured path. `coordinate_method_dimension` is not reconcilable and is outside this proposal's scope.

## Problem

- Fourteen classifier entities have labels that repeat across parent entities. Without parent context, the current result can show duplicate labels without distinguishing their parent.
- Fourteen lookups lack reconciliation strategies. Thirteen have a usable label; `contact` does not. Reconciliation should not auto-accept duplicate labels.
- `coordinate_method_dimension` is not reconcilable. It is not a target for derived-label or context matching.
- Duplicate suppression currently sees only rows remaining after SQL applies its result limit, so it misses same-label entities omitted by that limit.

## Scope

- Determine duplicate normalized labels across the full eligible set before applying the row limit; return no more rows than requested.
- Add optional `scope_columns` to `simple` classifiers and `lookup` entities. Use it for the fourteen context-dependent classifiers and for `feature` and `taxa_common_names`.
- Register all thirteen label-bearing lookups with the `lookup` marker. `rdb_system` and `taxa_synonyms` remain unscoped: their unique sets include version or bibliography fields that parent labels alone do not represent. Duplicate labels for these entities remain ambiguous suggestions.
- Generate alternate-identity queries from `alternate_identity_column` while preserving the configured entity ID field and property identifiers.
- Extend configuration validation, endpoint tests, generated-schema checks, and deployment configuration parity for the new behavior.

## Non-Goals

- `coordinate_method_dimension` is not reconcilable and remains outside scope. This proposal adds no label-generation or search path for it.
- `dimension` reconciliation and schema repair. The supplied [table export](./tbl_dimensions.csv) shows duplicate `dimension_abbrev` values, including duplicates within the same `unit_id` and `method_group_id`, contrary to the target model's declared unique set. Investigate this as a possible data or model integrity issue separately.
- `contact`, which has no label column, and `abundance_element_group`, which has no target table.
- `dataset`, which is a tracked aggregate, and specialized strategies including `site`, `location`, `method`, `taxon`, `modification_type`, `bibliographic_reference`, `administrative_region`, `country`, `geonames`, and `sampling_context`.
- Embeddings, semantic search, LLM disambiguation, SIMS identity allocation, OpenRefine UI changes, and production deployment.

## Current Behavior

The configured simple-classifier SQL ranks candidates and applies `p_limit`. `ConfiguredClassifierStrategy.as_candidates()` then counts duplicate normalized labels in the returned rows. A duplicate outside that limited result is invisible to the Python check.

The candidate response includes `id`, `name`, `score`, `match`, `type`, and an optional description of up to 500 characters. It has no context status. The completed simple-classifier contract uses an opt-in `description_match_weight` with a default of zero and uses label similarity for automatic matching.

## Proposed Design

### 1. Configuration and scope

Keep two marker values:

| Value | Use | Description scoring |
|---|---|---|
| `simple` | Classifiers with a usable label | Opt-in, with the tier-1 default of zero |
| `lookup` | Shared metadata that must resolve to an existing row | Disabled; reject a nonzero weight |

`scope_columns` is optional for either value. When present, it lists foreign-key columns to configured parent entities. The generated view and fuzzy query expose readable parent labels as `context` and a normalized `norm_context`. Multiple parent labels are joined in declaration order. Use left joins so a missing parent does not remove the entity row; a null context cannot satisfy a supplied context.

Expose `context` as an OpenRefine property for entries with `scope_columns`. Validate that every scope column resolves to a configured entity label, and reject a nonzero `description_match_weight` on `lookup` entries. Do not treat parent labels as unique keys: duplicate candidates within the selected context remain ambiguous.

### 2. Candidate selection and response

When a request supplies the `context` property, filter by its normalized value before ranking candidates or applying the result limit. Determine whether each normalized label is duplicated across the full eligible set after this filter and before the row limit. Rank rows and return at most the requested number of rows. Carry an internal ambiguity flag with each returned row so candidate conversion sets `match: false` when that label is duplicated, even if its duplicate is beyond the row limit. The flag is not part of the API response. The limit caps candidate rows, not distinct labels; the response never expands to include every row for a selected label.

If no candidate matches both the label query and the supplied context, return the usual unfiltered label candidates as suggestions, with `match: false` and `context_match: false` on every result. For candidates found in the supplied context, set `context_match: true`. Omit `context_match` when the request has no context property.

Include `Context: <parent labels>` at the start of the candidate `description`, followed by any existing entity description, within the existing 500-character limit. This makes parent context visible in OpenRefine while the `context_match` field lets clients identify a context fallback. Do not change the candidate `name` or label scoring.

### 3. Lookups

All thirteen label-bearing lookups use `reconciliation: lookup`; `contact` remains excluded. `feature` and `taxa_common_names` also use `scope_columns`. `rdb_system` and `taxa_synonyms` do not: their target-model unique sets include `rdb_version` and `biblio_id`, respectively, so location or taxon labels alone are insufficient context. Duplicate labels for those lookups remain suggestions and cannot auto-match.

An alternate-identity query must return the configured ID column under its configured name, for example `method_id`, not as `id`. Keep public property identifiers such as `method_abbreviation` unchanged so candidate conversion and existing clients continue to work.

### 4. Compatibility

Entities without `scope_columns` keep the tier-1 public result columns, scoring defaults, property behavior, and maximum row count. Their SQL may change to detect duplicate labels before limiting; byte-for-byte SQL identity is not required. An entity with `scope_columns` but no context property follows its existing label-search behavior, except that duplicate suppression checks all eligible rows before limiting. A response may contain one row for an ambiguous label; that row is not an automatic match.

## Alternatives Considered

- **Keep duplicate labels ambiguous without adding context.** This remains the safe fallback, but does not distinguish known parent-scoped classifiers. The proposal keeps it for entities whose full business key is not represented by parent context.
- **Add a strategy class for each entity.** Rejected because the existing configured path can express the required parent relationships without duplicating entity-specific code.
- **Add a generic SQL label expression for `coordinate_method_dimension`.** Rejected. It is not a reconciliation target, so label generation and search support are not proposed.

## Risks And Tradeoffs

- Parent joins add work to generated queries. Context is not a unique key; duplicate labels within the selected context remain non-matches.
- Lookup candidates that need version or bibliography context may remain ambiguous. This is safer than treating an incomplete context as unique.
- Context is added to the existing candidate description, which remains limited to 500 characters. Place context first so it is retained if the entity description is truncated.
- `lookup` entities are exposed through the reconciliation manifest, as are existing supported entities.

## Testing And Validation

- Verify marker and scope validation, including a missing or unresolved scope column.
- Test duplicate labels with `limit: 1`; the response contains at most one row, and that row is not an automatic match when another eligible row has the same normalized label. Test that context filtering occurs before ambiguity detection and the row limit.
- Test matching context, unmatched-context fallback, `context_match`, and visible context in the HTTP response.
- Test that `rdb_system` and `taxa_synonyms` remain ambiguous when their omitted key fields leave duplicate labels.
- Test generated alternate-identity results through candidate conversion, including the configured ID field and unchanged property identifiers.
- Compare no-context behavior for existing entities and verify classifier/lookup configuration parity across production, test, and deployment files.

## Acceptance Criteria

- `P2-AC-1`: `simple` and `lookup` entries with valid `scope_columns` expose the `context` property and normalized parent context; entries without scope remain valid.
- `P2-AC-2`: The thirteen currently unsupported label-bearing lookups use the `lookup` marker and do not score or auto-match on descriptions. Among lookups, only `feature` and `taxa_common_names` use parent context in this tier.
- `P2-AC-3`: Context filters candidates before ranking and limiting. An unmatched context returns at most the requested number of unfiltered suggestions with `match: false` and `context_match: false`; matching results expose context in `description` and set `context_match: true`.
- `P2-AC-6`: Generated alternate-identity results use the configured ID field and preserve existing property identifiers; `method` continues to convert candidates successfully.
- `P2-AC-7`: This change does not modify `dimension` configuration or schema. `coordinate_method_dimension` is not exposed as a supported reconciliation type. `contact`, `abundance_element_group`, `dataset`, `taxa`, and specialized strategies remain unchanged. Exclusion reasons stay in the reconciliation type inventory register tracked by [issue #43](https://github.com/humlab-sead/sead_authority_service/issues/43).
- `P2-AC-8`: Entities without scope preserve the tier-1 public result shape, scoring, and property behavior, apart from corrected duplicate suppression.
- `P2-AC-9`: An unresolved scope target or a lookup without a label fails startup with a named error.
- `P2-AC-10`: Classifier and lookup configuration is identical across production, test, and deployment container configuration files.
- `P2-AC-11`: `limit` remains a maximum number of returned rows. Duplicate normalized labels are detected across all eligible rows before applying that limit, so a `limit: 1` result cannot auto-match when another eligible row has the same label.

## Planning Handoff

Confirmed decisions:

- Keep the configured path; do not add per-entity strategies or a generic derived-label expression.
- Use `simple` and `lookup` markers with optional `scope_columns`; lookups never score on descriptions.
- Filter supplied context before ranking, ambiguity detection, and the row limit. On context fallback, return at most the requested number of suggestions and mark every result as a non-match.
- Keep `limit` as a maximum row count. Detect duplicate labels across all eligible rows before limiting, and do not auto-match a returned row when its duplicate is omitted by the limit. Context labels are display values, not unique keys.
- Leave `rdb_system` and `taxa_synonyms` unscoped until their full unique keys can be represented.
- Keep `dimension` reconciliation and schema repair out of this change; investigate the mismatch between its observed abbreviations and the target model's declared unique set separately.
- Keep specialized strategies and production data unchanged.

Preserve the tier-1 500-character description limit, `description_match_weight` default of zero, label-based automatic-match rule, and declared support status. For entities without scope, preserve the current no-context public behavior except for the duplicate-suppression correction.

Expected validation is a focused endpoint test for context and fallback, a `limit: 1` test proving both the row cap and duplicate-match suppression, generated-schema checks, and candidate-conversion coverage for alternate identity.

## Final Recommendation

Approve context as an optional input to the existing configured path, with ambiguity detected across the full eligible set while `limit` remains a strict row cap. Keep lookups conservative. Leave `dimension` out of this change pending separate investigation of its data/model key mismatch.
