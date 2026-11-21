# Proposal: One Contract for Simple Classifiers

## Status

- Accepted feature / change request
- Accepted: 2026-11-21
- Scope: `reconciliation: simple` entities, record selection, and classifier registration
- Schema regeneration and deployment: owned outside this change; this proposal records the required shapes and deploy order only
- Goal: make the generated database objects the single definition of a simple classifier, so enabling one is configuration-only
- Amends the generated view contract in [CLASSIFIER_FUZZY_RECONCILIATION](../CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION.md), which omits `description` for seven entities
- Extends the pilot record selection delivered by [RECONCILIATION_IDENTITY_CONTRACT](../RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md)
- Revised from [REVIEW.md](./REVIEW.md)
- Next step: phase task plan for the single delivery phase

## Summary

Every `reconciliation: simple` entity already gets a generated `authority.<key>` view and `authority.fuzzy_<key>` function. Make that pair a complete and uniform contract: always expose `label` and `description`, never expose OpenRefine property mappings, and never require a `description_column` source to exist.

Then derive record selection from `table_specs` instead of from hardcoded type lists. After the change, enabling a simple classifier for browse, details, search, or verification is a YAML edit plus the generated objects. No Python change is needed.

## Problem

Record selection currently supports exactly two types, and both are hardcoded. `src/record_selection.py` names them in five separate structures:

| Location | What is encoded |
|---|---|
| `PILOT_TYPES` | The two selectable keys; read by policy loading, the discovery loop, and `src/api/candidate_verification.py` |
| `_PROJECTION_BUILDERS` and its two builders | Table name, id column, label column, description presence, membership filter |
| `_DISPLAY_FIELDS` | Display fields, indexed directly by `discovery_types()` |
| `_text_filter_fields`, `_field_filters` | `if entity_type == "feature_type"` branches |
| `search_interactive`, `_feature_type_candidates`, `_country_candidates` | Per-type search dispatch |

Adding a third simple classifier therefore means editing five unrelated structures. Missing one fails at request time (`_DISPLAY_FIELDS` raises `KeyError`) or at startup (`load_record_selection_policy()` rejects any enabled type outside `PILOT_TYPES`).

The second problem is that `country` is not a classifier at all, so it bypasses the generated objects. The country subset is declared three times:

- `config/entities.yml` `location.filter_params` defines `location_type_ids`
- `src/resources/country.yml` calls `authority.fuzzy_location(..., 1)` with a literal
- `record_selection.COUNTRY_FUZZY_SQL` calls the same function again with a different parameter style

The same literal duplication appears in `src/resources/administrative_region.yml` with `7`.

The third problem is the contract gap that motivates the first two. `schema/generated/location.sql` exposes no `description` column, because the `location` spec sets `description_column: null`. Both `src/resources/country.yml` and `src/resources/administrative_region.yml` select `description as "Description" from authority.location`. Against the checked-in generated schema, that select cannot succeed. No live database was reachable while drafting, so confirm this against a deployment before relying on it, but the generated file is the declared source of truth.

## Scope

- The generator template and SQL helpers that define the contract for `reconciliation: simple` entities: columns, function signature, and returned columns
- Validation of that contract
- Record selection: discovery, list, details, interactive search, and candidate verification for simple classifiers
- `country` as a configured simple classifier over tracked location types
- Classifier registration driven by configuration rather than a static key list
- Documentation and tests that describe current pilot behaviour

## Non-Goals

- Regenerating `schema/generated/`, rebuilding `schema/__deploy__.sql`, and deploying the result; that work is owned outside this change
- Redesigning SEAD location or place storage
- Converting complex strategies (`site`, `method`, `location`, `taxon`) to simple classifiers
- Changing candidate scoring, thresholds, or the `match` flag
- Changing SIMS identity behaviour, `site` verification, or match readiness
- Converting `administrative_region` (same literal duplication, but a strategy rather than a simple classifier)
- Deciding which entities should be enabled in a given deployment

## Current Behavior

`make generate-schema` renders `schema/templates/entity.sql.jinja2` from `table_specs`. For a simple entity it produces:

- a view `authority.<key>` with `<id_column>`, `label`, and `norm_label`; `description` and `norm_description` only when `description_column` is set
- a function `authority.fuzzy_<key>(text, integer, double precision, double precision)` that always takes four parameters, and returns `description` only when the spec declares one
- additionally `label_sim` when description scoring is enabled; `ConfiguredClassifierStrategy` reads it to decide `match`, falling back to `name_sim` when absent

45 entities declare `reconciliation: simple`. Seven have no description source and therefore produce the three-column shape: `taxa_tree_author`, `taxa_tree_order`, `taxa_tree_family`, `taxa_tree_genus`, `colour`, `language`, `season`.

No simple spec declares `properties`, `filter_params`, `where_clause`, `materialized`, or an `alternate_identity_column`. `data_type` is the only simple spec with `details_columns`, and `data_type`, `taxa_tree_order`, `taxa_tree_family`, and `taxa_tree_genus` declare `extra_columns`/`joins` that feed the view.

Registration is static. `src/strategies/configured_classifier.py` holds `CLASSIFIER_KEYS` and validates configuration in both directions: every listed key must be configured, and every marked key must be listed.

## Proposed Design

### 1. Generator invariant: label and description for every simple classifier

Change the template so a simple entity always produces the same shape:

```sql
create or replace view authority.colour as
select
  t.colour_id,
  t.colour_name as label,
  authority.immutable_unaccent(lower(t.colour_name)) as norm_label,
  null::text as description,
  null::text as norm_description
from public.tbl_colours as t;
```

Rules:

- `description` and `norm_description` are always present; they are `null` when the spec declares no `description_column`.
- The function always takes `(text, integer, double precision, double precision)` and always returns `<id_column>, label, description, label_sim, name_sim`.
- `label_sim` stays. `ConfiguredClassifierStrategy` decides `match` from it and falls back to `name_sim` only when the column is absent, so dropping it would let a description-boosted `name_sim` promote a candidate to an automatic match. `rdb_code` is in exactly that position today.
- For an entity with no description, `label_sim` is the same label expression that already produces `name_sim`, so ranking and `match` decisions do not change.
- `description_match_weight > 0` requires a real `description_column`. Validation rejects the combination, because scoring a null description has no meaning.
- `label` remains the display name and the id column keeps its physical name.

Consequences for the existing helpers, all simplifications:

- `build_classifier_details_sql` and `build_classifier_prefix_sql` stop branching on `description_column`
- `classifier_view_columns` always includes `description`
- `record_selection` stops branching on whether a description exists

### 2. No OpenRefine property mappings on a simple classifier

A simple classifier is defined in the OpenRefine API by its label and description only. It publishes no additional property IDs and accepts no property hints.

- `build_classifier_specification` already sets `properties: []` and `property_settings: {}`; keep that and state it as a rule.
- Validator: a simple spec that declares `properties` or `property_settings` fails startup. This prevents drift rather than adding behaviour.
- Discovery fields (`display_fields`, `text_filter_fields`, `field_filters`) are UI hints about the record payload, not OpenRefine property mappings. Keep them, and derive them from the spec.
- An entity that needs property mappings is not a simple classifier. Keep it as a strategy instead of relaxing this rule. The same applies to any future need the generated contract cannot express: add entity-specific logic or a new configuration element there, not here.

### 3. One definition of a valid simple classifier

`validate_classifier_configuration()` checks every simple spec, whether or not record selection uses it:

- non-empty text `id_column` and `label_column` (already checked)
- no `properties`, no `property_settings`
- `description_match_weight > 0` only with a `description_column`
- `filter_params`, `where_clause`, `extra_columns`, and `joins` limited to what the generator supports

A violation fails startup. One definition avoids the alternative where a malformed spec warns, is still registered for reconciliation, and then fails at request time.

Configuration checks cannot prove that deployed views and functions match the configuration, because they do not read the database. Treat the regenerated schema as a prerequisite: the new application expects the shapes in §1 to be deployed first. Regenerating and deploying them is owned outside this change, so this proposal records the requirement rather than enforcing it at startup.

### 4. Record selection derived from `table_specs`

Replace the hardcoded structures with spec-derived functions in `src/record_selection.py`:

| Today | Replacement |
|---|---|
| `PILOT_TYPES` | `selectable_types()`: simple keys with usable `id_column`, `label_column` |
| `_PROJECTION_BUILDERS` | one builder that reads `table_specs.<key>` and returns table `authority.<key>`, `id_column`, `label_column="label"`, `description_column="description"` |
| `_DISPLAY_FIELDS` | fields derived from the projection: `name`, `target_id`, and `description` when the spec declares one |
| `_text_filter_fields`, `_field_filters` | same derivation, no type-name branches |
| `_feature_type_candidates`, `_country_candidates`, `search_interactive` dispatch | one classifier path: `strategy.find_candidates(...)` then `strategy.as_candidates(...)` |

Behaviour to preserve:

- `GET /records/types` lists only keys present under `options:record_selection:types`. A simple classifier that is not configured stays absent and does not grow the discovery document to 45 mostly-disabled entries.
- `browse_max_rows`, `browse_max_bytes`, and `interactive_search_max_results` stay global, with the same defaults and the same 500 cap.
- A configured key that is not a valid simple spec fails startup. This replaces the current "enables unsupported type" error with the same outcome and a more useful message.
- Error semantics split cleanly: not simple, not configured, or not registered returns `unsupported_type`; simple and configured but with the switch off returns `unsupported_capability`.
- `src/api/candidate_verification.py` asks the policy for membership instead of importing `PILOT_TYPES`. The `site` branch and its SIMS policy gate are untouched.

### 5. `country` as a configured simple classifier

Add a spec so the country subset uses the generated objects and the literal disappears:

```yaml
country:
  name: "Country"
  table_name: "tbl_locations"
  id_column: "location_id"
  label_column: "location_name"
  description_column: null
  reconciliation: simple
  where_clause: "location_type_id = 1"
```

- `location_type_id = 1` is acceptable because `location_type` is itself a tracked simple classifier. The id is stable reference data, not a label lookup that can drift.
- `where_clause` filters the generated view, so list, details, and search share one membership rule. This is the existing generator configuration element, not new machinery.
- `country` adopts simple-classifier search semantics. That is an acknowledged behaviour change, not a parity claim: `fuzzy_location` filters with the `%` operator, while simple classifiers compare against `label_sim >= p_label_threshold`, and candidate conversion adds accent normalization and duplicate-label match suppression. The country set is small, so the loss of index acceleration does not matter.
- `description_column: null` is correct here: `tbl_locations` has no description column, so the `description as "Description"` select in `src/resources/country.yml` cannot resolve against the generated view either.
- Delete `src/resources/country.yml`, `src/strategies/country.py`, `COUNTRY_FUZZY_SQL`, `COUNTRY_LOCATION_TYPE_IDS`, and `_country_projection`. The resource file must go, because `resolve_specification()` prefers `src/resources/<key>.yml` over the configured spec and would otherwise bypass the generated function.
- `country` stays `support="supported"`, so `supportedTypes` is unchanged.

### 6. One initialization entry point

Registration currently happens at import, before configuration exists, so a static key list is the only option. Replace both with one explicit entry point:

```python
def initialize_classifiers() -> None:
    """Validate every simple spec, then register one strategy per configured key."""
```

- Application startup calls it after `setup_config_store()`. Scripts and tests call the same function instead of relying on an import side effect.
- `CLASSIFIER_KEYS` and the import-time `_register_configured_classifiers()` are removed. The three test modules that import the tuple iterate the registered keys instead, which is what they actually assert.
- `Strategies.register` is a dictionary write and the call is idempotent, so repeated initialization within one process is harmless.
- Tooling that builds strategies without calling the entry point sees no classifiers. That is an explicit contract rather than a hidden import-order dependency.
- Validation and registration stay in one function so a malformed spec cannot be registered. If they need to diverge later, split them then, not now.

## Alternatives Considered

**Keep the per-type maps and add entries for each new classifier.** Smallest diff today, and rejected: it keeps the work per entity proportional to the number of maps, which is exactly the cost this proposal removes.

**Require every simple spec to declare a real description source.** Rejected: data modelling on `colour`, `season`, `language`, and the four taxa levels would either invent descriptions or demote those entities to strategies. The contract exists so the code can stop branching, not to assert that every classifier has something to describe.

**Convert `country` by keeping `fuzzy_location` with a filter parameter.** Rejected: it keeps a second membership mechanism, and the filter already exists in the generator, so the view covers it without a special call.

**Leave `country` as a location strategy and change only record selection.** Rejected: the country subset would keep three declarations, and the duplication this proposal exists to remove would survive for the one type record selection already ships.

**Advertise all 45 classifiers in `/records/types`.** Rejected for now: it grows a discovery document that clients fetch per session and blurs which types are actually available. Reversible later without changing the enablement model.

## Risks And Tradeoffs

- **Schema regeneration and deployment sit outside this change.** The template change is in scope; producing `schema/generated/` and `schema/__deploy__.sql` and applying them is not. `make generate-schema` skips files that already exist, so whoever owns that step must use `make generate-schema-force`. Until it lands, the checked-in snapshots keep the old shape and `country` cannot run, because it needs `authority.country` and `authority.fuzzy_country`.
- **Function result types change.** Adding `label_sim` and the nullable `description` changes every simple function's result type, so PostgreSQL requires dropping and recreating the functions. The template's `drop function ... cascade` and the `drop schema if exists authority cascade` at the top of `schema/__deploy__.sql` already do this, which is why the external deploy replaces the whole schema rather than patching it.
- **Backward compatibility is an expectation, not a claim.** View columns are additive and queries select by name, so the previous application version is expected to work against the regenerated schema. Record that expectation for the external upgrade check instead of asserting it here.
- **Checked-in snapshots lag the template** until the external regeneration lands. Contract tests render the template directly, so they do not depend on that timing.
- **Validation is now unconditional.** A downstream `config/entities.yml` that declares `properties` on a simple spec, or a description weight without a description column, fails startup. No current spec does either, so the shipped configuration is unaffected.
- **Registration timing.** Scripts and tests that build strategies without calling the initialization entry point see no classifiers. This is the riskiest change for tooling, so it lands as its own commit with the affected tests updated.
- **`country` responses change.** The row set stays the same, but candidate ordering, accent handling, duplicate-label match suppression, and the presence of `description` in list and details responses can differ. Comparison tests cover this; matching row counts is not evidence.
- **Record-selection error codes shift** for types that are simple but unconfigured. Clients relying on `unsupported_type` for those cases see `unsupported_type` still, so no client change is expected; the new `unsupported_capability` only covers configured-but-off.
- **`administrative_region` keeps its duplicated literal.** Named as a non-goal so it is not mistaken for an oversight.
- **`country` and `location` share one trigram index name.** Both spec entries derive the index name from `table_name`, so `tbl_locations_norm_trgm` is created once and the second `create index if not exists` is a no-op. Harmless because the index is on the same table and column, but it should be expected in the generation diff.

## Testing And Validation

- Unit: a spec-driven test that adds a third `reconciliation: simple` entity to the test `table_specs`, enables one switch, and exercises discovery, list, details, and search. This is the test that proves the goal, because no Python for that key exists.
- Unit: render the template for two representative specs, one with a `description_column` and one without, and assert the view exposes `<id_column>`, `label`, `norm_label`, `description`, and `norm_description`, and the function takes `(text, integer, double precision, double precision)` and returns `<id_column>, label, description, label_sim, name_sim`. Render from the template rather than the checked-in snapshots, because regeneration is owned elsewhere.
- Unit: `match` decisions are unchanged for a description-boosted classifier (`rdb_code`) and for a label-only classifier (`colour`).
- Unit: validation rejects `properties` on a simple spec and `description_match_weight` without `description_column`, regardless of record-selection switches.
- Unit: `unsupported_type` versus `unsupported_capability` distinction, and `site` verification unchanged in a mixed batch.
- Handoff check: record the two rendered shapes as the contract the external regeneration must produce, and confirm `authority.site` and `authority.method` are unaffected by the template rules.
- Integration, read-only, when a database with the regenerated schema is available: assert `SET TRANSACTION READ ONLY`, resolve `authority.fuzzy_country` and one newly enabled classifier, compare country row counts and a small set of fuzzy queries by `location_type_id` before and after, and confirm unchanged target and SIMS row counts.
- Style: `ruff check --no-cache src tests main.py` and `black --check src tests main.py`.

## Acceptance Criteria

- `P-AC-1` Every generated view for a `reconciliation: simple` entity exposes `<id_column>`, `label`, `norm_label`, `description`, and `norm_description`, with `description` nullable.
- `P-AC-2` Every generated `authority.fuzzy_<key>` for a simple entity has the signature `(text, integer, double precision, double precision)` and returns `<id_column>, label, description, label_sim, name_sim`.
- `P-AC-3` Adding a valid simple classifier changes no runtime dispatch, registration list, or projection map; regression tests may still name individual keys.
- `P-AC-4` Enabling a simple classifier for browse, details, search, or verification requires only `options:record_selection:types` plus the generated objects, which the external regeneration produces.
- `P-AC-5` `GET /records/types` lists exactly the configured types, and each entry's limits, fields, and filters are derived from its spec.
- `P-AC-6` A configured key that is not a valid simple spec fails startup; a simple configured key with a switch off returns `unsupported_capability`.
- `P-AC-7` `country` returns the tracked `location_type_id` subset through the generated objects, and the reviewed differences in search semantics, candidate ordering, and payload description are recorded and covered by comparison tests.
- `P-AC-8` A simple spec declaring OpenRefine property mappings fails validation, and the manifest publishes no properties for simple types.
- `P-AC-9` `site` candidate verification and match readiness behave exactly as before, including the SIMS policy gate.
- `P-AC-10` The template produces the required view and function shapes for a spec with and without a `description_column`, and the proposal records the schema-before-application deploy order for the external owner; regeneration and deployment are not performed by this change.

## Planning Handoff

Delivery is one phase. Decisions that constrain implementation:

- `description` is nullable and always present. Do not require a real source column.
- `label_sim` stays in the uniform result so `match` decisions do not change.
- Discovery lists configured types only, not all simple classifiers.
- `country` becomes a configured simple classifier filtered by `where_clause` on the tracked `location_type_id`, and adopts simple-classifier search semantics.
- Validation of the simple contract is unconditional, independent of record-selection switches.
- `CLASSIFIER_KEYS` is removed, not deprecated, in this phase.
- Schema regeneration and deployment are owned outside this change; record the required shapes and the `generate-schema-force` step for that owner.
- `administrative_region` and complex strategies are out of scope.

Constraints to preserve: pipeline-safe read-only behaviour of record selection, the 500-result interactive cap, existing error envelope shape, `site` verification through SIMS policy, and schema-before-application deploy order.

Expected validation outcomes: the new-entity test passes with no code change for that key; template rendering shows the expected shapes for specs with and without a description column; country comparison results are recorded; full unit suite green.

Open questions:

- Does `administrative_region` convert in this phase or a follow-up? Default is a follow-up; confirm so the release note is accurate.

## Recommended Delivery Order

1. Generator template and SQL helpers, with the required shapes recorded for the external regeneration.
2. Validation for the contract.
3. Record selection derived from specs; delete the pilot constants and per-type branches.
4. `country` conversion, including removal of the resource file and strategy module.
5. One initialization entry point; remove `CLASSIFIER_KEYS` and the import-time registration.
6. Documentation: `docs/OPERATIONS.md`, this proposal's related notes, and the deployment config copies.

## Final Recommendation

Adopt the change. It removes five hardcoded structures and one duplicated SQL call, replaces them with one spec-derived path, and turns onboarding a simple classifier into a YAML edit. The cost inside this project is a template change and configuration checks rather than new machinery; regenerating and deploying the schema is a separate, externally owned step, and an entity that does not fit the contract keeps a strategy instead of stretching the contract.
