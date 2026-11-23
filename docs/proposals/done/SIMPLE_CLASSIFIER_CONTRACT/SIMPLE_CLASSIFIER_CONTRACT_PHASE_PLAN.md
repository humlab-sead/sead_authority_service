# One Contract for Simple Classifiers — Phase Plan

## Summary

This plan sequences the accepted [SIMPLE_CLASSIFIER_CONTRACT](./SIMPLE_CLASSIFIER_CONTRACT.md) into a single delivery phase. The phase makes the generated `authority.<key>` view and `authority.fuzzy_<key>` function the complete definition of a `reconciliation: simple` entity, then derives record selection and classifier registration from `table_specs` so that enabling a simple classifier is a configuration edit.

One phase is deliberate. The parts are coupled: the template shape is what the record-selection derivation relies on, and both depend on one registration entry point. Splitting them would produce intermediate states where the code assumes a contract the schema does not yet provide.

Schema regeneration and deployment are outside this plan. This phase records the required shapes and the deploy order; an external owner produces and applies the artifacts.

## Problem

Record selection supports exactly two hardcoded types. `src/record_selection.py` names them in five structures — the type tuple, the projection builders, the display-field map, the filter helpers, and the search dispatch — so a third simple classifier needs five coordinated edits, and a missed edit fails at request time or startup.

`country` compounds this. It is not a classifier, so it bypasses the generated objects and declares the same subset three times, including `COUNTRY_FUZZY_SQL` in Python and a literal in `src/resources/country.yml`.

Registration is also static: `src/strategies/configured_classifier.py` holds a key tuple, so configuration cannot introduce a classifier that the list does not already name.

## Scope

In scope:

- The generator template rules for `reconciliation: simple` entities: view columns, function signature, returned columns
- One unconditional validation definition for a valid simple classifier
- Record selection derived from specs: discovery, list, details, interactive search, verification membership
- `country` as a configured simple classifier over tracked location types
- One classifier initialization entry point replacing the static key tuple

Out of scope:

- Regenerating `schema/generated/`, rebuilding `schema/__deploy__.sql`, and deploying it
- `administrative_region` conversion and complex strategy changes
- Candidate scoring, thresholds, SIMS behaviour, and `site` verification
- Which classifiers a given deployment enables

## Current Position

- Every simple entity already gets a generated view and function; `description` is conditional and `label_sim` appears only when description scoring is enabled.
- 45 entities declare `reconciliation: simple`. Seven have no description source: `taxa_tree_author`, `taxa_tree_order`, `taxa_tree_family`, `taxa_tree_genus`, `colour`, `language`, `season`.
- `fuzzy_rdb_code` returns both `label_sim` and a description-boosted `name_sim`, and candidate conversion uses `label_sim` to decide `match`.
- `country` reconciliation runs through `authority.fuzzy_location` with a literal type id; `country` also has a resource spec in `src/resources/country.yml` that `resolve_specification()` prefers over configuration.
- `authority.location` exposes no `description` column, and `tbl_locations` has no description column in the SEAD schema.
- `validate_classifier_configuration()` runs from `main.py` startup and from the router's config dependency.
- Record selection ships with all pilot capabilities disabled in `config/config.yml` on this branch; the deployment copy under `sead-tools/` enables them.

Assumption: the checked-in generated snapshots still match the current template. Verify before the task plan assumes they can be left untouched.

## Phase Plan

### Phase 1: One contract, one selection path

**Goal**

Make the generated view and function the complete definition of a simple classifier, and drive record selection and registration from configuration.

**Focus**

- Template: always emit `description` and `norm_description`, null when no source column is declared; always return `<id_column>, label, description, label_sim, name_sim` from the four-parameter function.
- Simplify the SQL helpers that currently branch on `description_column`, and stop record selection branching on description presence.
- One validation definition: reject `properties` and `property_settings` on a simple spec, and reject `description_match_weight` without a `description_column`.
- Record selection: replace the type tuple, projection builders, display-field map, filter helpers, and search dispatch with spec-derived equivalents.
- `country`: add a configured spec with `where_clause` on the tracked `location_type_id`, then remove the resource spec, the strategy module, and the duplicated SQL constants.
- Registration: one initialization entry point that validates then registers; remove the static key tuple and the import-time registration.
- Record the required generated shapes and the schema-before-application order for the external regeneration owner.

**Depends On**

- Accepted proposal decisions in [SIMPLE_CLASSIFIER_CONTRACT](./SIMPLE_CLASSIFIER_CONTRACT.md)
- No blocking decision outstanding; `administrative_region` stays out by default

**Outputs**

- A template that produces one uniform shape for every simple entity
- A record-selection module with no per-type structures
- `country` served by generated objects
- One initialization entry point used by application startup and tooling
- A recorded contract for the external regeneration step

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`, `P-AC-2`, `P-AC-10`) Rendering the template for a spec with and without a `description_column` produces the same view columns and the same four-parameter function returning `<id_column>, label, description, label_sim, name_sim`; non-simple entities keep their current output.
- `PH1-AC-2` (from `P-AC-3`) No runtime dispatch, registration list, or projection map names an individual simple classifier.
- `PH1-AC-3` (from `P-AC-4`) Enabling a simple classifier needs only its `options:record_selection:types` entry and the generated objects.
- `PH1-AC-4` (from `P-AC-5`) `GET /records/types` lists exactly the configured types, with limits, fields, and filters derived from the spec.
- `PH1-AC-5` (from `P-AC-6`) A configured key that is not a valid simple spec fails startup; a configured simple key with its switch off returns `unsupported_capability`.
- `PH1-AC-6` (from `P-AC-7`) `country` reads the tracked `location_type_id` subset through the generated objects, with the reviewed differences in search semantics, ordering, and payload description covered by comparison tests.
- `PH1-AC-7` (from `P-AC-8`) A simple spec declaring OpenRefine property mappings fails validation, and simple types publish no properties in the manifest.
- `PH1-AC-8` (from `P-AC-9`) `site` candidate verification and match readiness are unchanged, including the SIMS policy gate.

**Validation Milestones**

- `VM-1` Template rendering for both representative specs produces identical shape, and non-simple output is unchanged — covers `PH1-AC-1`.
- `VM-2` A third simple entity added to the test specs works end to end through discovery, list, details, and search with no Python change for that key — covers `PH1-AC-2`, `PH1-AC-3`, `PH1-AC-4`.
- `VM-3` Validation and error-code tests reject property mappings and a weight without a description column, and distinguish unsupported types from disabled capabilities — covers `PH1-AC-5`, `PH1-AC-7`.
- `VM-4` `match` decisions are unchanged for a description-boosted classifier and a label-only classifier, and country comparisons record the reviewed differences — covers `PH1-AC-6`.
- `VM-5` `site` verification regression and the full unit suite pass — covers `PH1-AC-8`.

**Task-Plan Handoff**

- Source criteria: `PH1-AC-1` through `PH1-AC-8`, tracing to `P-AC-1` through `P-AC-10`.
- Fixed decisions: `description` is nullable and always present; `label_sim` stays in the uniform result; discovery lists configured types only; `country` adopts simple-classifier search semantics; validation is unconditional; the static key tuple is removed rather than deprecated.
- Constraints: keep record selection read-only and the interactive cap at 500; keep the error envelope shape; keep `site` verification routed through SIMS policy; do not regenerate snapshots in this phase.
- Sequencing constraint: `country` cannot respond until the regenerated objects exist, so code can land before the external deploy but enablement must follow it.
- Blocking question: none for this phase. Confirm `administrative_region` remains a follow-up so the release note is accurate.

**Readiness**

Ready for a task plan.

## Cross-Phase Rules

- Change the template and the code that reads its output in the same phase; a template change alone leaves `country` non-functional.
- Never regenerate `schema/generated/` or `schema/__deploy__.sql` here. Record the expected shapes for the external owner instead.
- Do not reintroduce a per-type branch to make one entity fit. If the contract cannot express an entity's needs, keep it as a strategy or add a generator configuration element.
- Keep validation single-valued: no warn-only paths for a spec that the system will later serve.
- Preserve behaviour that is not part of the decision: scoring, thresholds, `match`, SIMS interaction, and `site` verification.

## Validation Strategy

Layered, matching the phase order inside the single phase:

- Template-level tests render the template directly rather than reading checked-in snapshots, so they do not depend on when regeneration happens.
- Contract tests then exercise the spec-derived record selection through HTTP for a newly added third classifier, which is the observable proof that enablement is configuration-only.
- Validation tests cover the two rejection rules and the error-code split.
- Comparison tests cover `country` behaviour and `match` decisions for both a description-boosted and a label-only classifier.
- Regression tests cover `site` verification in a mixed batch.
- An optional read-only integration run, when a database with regenerated objects is available, confirms the country function resolves and row counts are unchanged.

Exact commands, fixtures, and assertions belong in the phase task plan.

## Final Recommendation

Proceed with the single phase. It is the smallest sequence that leaves no intermediate state depending on a contract that has not landed, and it delivers the goal directly: a new simple classifier becomes configuration plus generated objects, with no Python edit.
