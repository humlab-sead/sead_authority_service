# Proposal: Tier 2 — Context-Scoped Classification and Lookup Reconciliation

## Status

- Proposed feature / change request
- Tier 2 of a two-tier change. Tier 1, [Fuzzy Reconciliation for Classifier Entities](../done/CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION.md), is implemented and validated across Phases 1–3. Its completion records include disposable-database and HTTP checks; production deployment was out of scope. See the [Phase 1](../done/CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION_PHASE_1_TASK_PLAN.md), [Phase 2](../done/CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION_PHASE_2_TASK_PLAN.md), and [Phase 3](../done/CLASSIFIER_FUZZY_RECONCILIATION/CLASSIFIER_FUZZY_RECONCILIATION_PHASE_3_TASK_PLAN.md) task plans. This proposal depends on the completed tier-1 baseline and does not restate its contracts.
- The completed [One Contract for Simple Classifiers](../done/SIMPLE_CLASSIFIER_CONTRACT/SIMPLE_CLASSIFIER_CONTRACT.md) supersedes the earlier `reconciliation: simple` view and function shapes. Its [Phase 1 task plan](../done/SIMPLE_CLASSIFIER_CONTRACT/SIMPLE_CLASSIFIER_CONTRACT_PHASE_1_TASK_PLAN.md) records 1,336 passing tests, 50 skips, and a successful disposable PostgreSQL 17 bundle apply; deployment to a real environment was not part of that work. Tier 2 uses this completed contract as its baseline.
- Acceptance criteria use the `P2-AC-<N>` prefix so they stay distinguishable from tier-1 `P-AC-<N>` criteria in phase plans.
- Scope: `sead_authority_service` reconciliation for classifiers whose label is unique only within a parent, for lookups that have no reconciliation strategy, and for `dimension`
- Goal: extend the tier-1 configured path with parent-context matching, derived labels, and lookup reconciliation, without adding per-entity Python classes

## Summary

Tier 1 registers flat classifiers where the label identifies a row and declines automatic matches when two rows share a label. That is safe but not accurate for 14 classifiers whose label is only unique inside a parent: `colour` inside `method`, `site_type` inside `site_type_group`, `value_type_item` inside `value_type`, and similar pairs. Tier 1 also leaves 14 lookups unreconcilable and defers `dimension`.

The recommendation is to extend the same configured path with two additions: `reconciliation: scoped`, which adds parent context to matching, and `reconciliation: lookup`, which enables label matching for shared metadata that must resolve to an existing row. A derived-label option covers entities with no text label. No new per-entity Python class, resource YAML, or hand-written SQL is introduced.

Because tier 1 already suppresses automatic matches on duplicate labels, tier 2 is an accuracy improvement rather than a correctness fix. Deferring it never produces a wrong automatic match.

## Problem

- 14 classifier entities have a label that repeats across parents, so tier 1 can only offer them as ambiguous suggestions. Verified against `sead_standard_model.yml` unique sets and foreign keys:
  - scoped by a classifier parent: `abundance_element` (record_type), `colour` (method), `data_type` (data_type_group), `ecocode_definition` (ecocode_group), `ecocode_group` (ecocode_system), `horizon` (method), `property_type` (property_type_group), `rdb_code` (rdb_system), `season` (season_type), `site_type` (site_type_group), `taxa_tree_family` (taxa_tree_order), `taxa_tree_genus` (taxa_tree_family), `value_class` (value_type + method), `value_type_item` (value_type).
- 14 lookups have no reconciliation strategy: `chronology`, `contact`, `data_provider`, `dating_lab`, `dating_material`, `ecocode_system`, `feature`, `master_dataset`, `project`, `rdb_system`, `relative_ages`, `taxa_common_names`, `taxa_synonyms`, `taxonomic_order_system`. Only `site`, `location`, and `citation` are covered by specialized strategies.
- Several lookups are also context-scoped: `feature` is unique by type and name, `taxa_common_names` and `taxa_synonyms` under `taxa`, and `rdb_system` by location, system, and version.
- `dimension` is unusable today: it is declared supported in `src/metadata.py`, but `config/entities.yml` has no entry, no `schema/generated/dimension.sql` exists, and `src/resources/dimension.yml` queries `authority.dimension` plus a `dimension_description` column that the standard model does not list.
- `coordinate_method_dimension` has no text label at all; its columns are `method_id`, `dimension_id`, `limit_upper`, and `limit_lower`.
- `src/resources/method.yml` and `src/resources/dimension.yml` hand-write `alternate_identity_sql`, although `config/entities.yml` already records the same column in `alternate_identity_column`.

## Scope

- Add `reconciliation: scoped` to the 14 context-dependent classifiers and to the 4 context-dependent lookups.
- Add `scope_columns` to the table spec, and expose the parent context in the generated view and fuzzy function.
- Add an optional `context` OpenRefine property that narrows candidates when supplied.
- Add `reconciliation: lookup` for the 9 flat lookups, so all 13 lookups with a usable label become reconcilable.
- Add a derived-label option for `coordinate_method_dimension`.
- Derive alternate-identity SQL from `alternate_identity_column` instead of hand-written resource SQL.
- Repair `dimension`: table spec, generated view, and verified description column.
- Extend tier-1 startup validation and deployment parity to the new marker values.

## Non-Goals

- Completed `reconciliation: simple` contracts: uniform view and function shapes, no OpenRefine property mappings, the 500-character candidate limit, the opt-in `description_match_weight` default of `0`, the `label_sim`-only `match` rule, duplicate-label suppression, and declared support status. Existing simple entities keep these contracts unchanged; the optional `context` property is specific to scoped entities in tier 2.
- Specialized strategies: `site`, `location`, `method`, `taxon`, `modification_type`, `bibliographic_reference`, `administrative_region`, `country`, `geonames`, and `sampling_context`. `taxon` keeps its current registration and remains excluded from `supportedTypes`.
- `contact`, which has no label column and no unique set.
- `abundance_element_group`, which has no target table.
- `dataset`, which is a tracked aggregate rather than a reconciliation target.
- Embeddings, semantic search, LLM disambiguation, SIMS identity allocation, and OpenRefine UI changes.
- Production data changes or deployment.

## Current Behavior

The completed simple-classifier path publishes `authority.<key>` views with `label`, `norm_label`, `description`, and `norm_description`; the description columns are null when no source description is configured. Each `authority.fuzzy_<key>` function takes four parameters and returns `<id_column>, label, description, label_sim, name_sim`. Label scoring is the default, description scoring is opt-in, and duplicate normalized labels never auto-accept.

Against that baseline, tier 2 differs in three verified ways:

- No generated artifact carries parent context, so `colour_name` "dark brown" from two different methods is indistinguishable in a candidate list.
- The fuzzy function has the fixed four-parameter signature and five result columns described above; it has no context columns.
- Lookups without a strategy are rejected by `src/reconcile.py` as an unknown type before any query runs.

## Proposed Design

### 1. Two additional markers on the same path

`reconciliation` becomes a three-value capability marker handled by the existing `ConfiguredClassifierStrategy`:

| Value    | Use                                                  | Candidate source                    |
|----------|------------------------------------------------------|-------------------------------------|
| `simple` | Flat classifiers and flat lookups                    | Tier-1 generated view and function  |
| `scoped` | Entities whose label repeats across parents          | Generated view with context columns |
| `lookup` | Shared metadata that must resolve to an existing row | Tier-1 generated view and function  |

`lookup` differs from `simple` in defaults, not in code: description scoring stays disabled regardless of `description_match_weight`, and `reconciliation: lookup` is reported distinctly in diagnostics. A lookup therefore can never rank on description text.

### 2. Scope columns and context

A scoped entry names the parent columns that make its label unique:

```yaml
colour:
  name: "Colours"
  table_name: "tbl_colours"
  id_column: "colour_id"
  label_column: "colour_name"
  description_column: null
  reconciliation: scoped
  scope_columns: ["method_id"]
```

Generated view adds a display context and a normalized context:

```sql
create or replace view authority.colour as
select
  t.colour_id,
  t.colour_name as label,
  authority.immutable_unaccent(lower(t.colour_name)) as norm_label,
  null::text as description,
  null::text as norm_description,
  m.method_name as context,
  authority.immutable_unaccent(lower(m.method_name)) as norm_context
from public.tbl_colours as t
join public.tbl_methods m using (method_id);
```

Rules:

- `scope_columns` are foreign keys to other configured entities, so the context is a readable label, not a numeric id. With two or more scope columns, the parent labels are concatenated with `' / '` in declaration order; `value_class` yields `<value type name> / <method name>`, and the entity's own label is never part of the context.
- The fuzzy function adds `context` and `norm_context` to the completed five-column result (`<id_column>, label, description, label_sim, name_sim`). `label_sim` remains the automatic-match input, and `name_sim` remains the ranking score.
- Entities without `scope_columns` keep the tier-1 signature. An unmarked entity is unchanged.

### 3. Context matching behavior

Context affects matching only when there is something to compare:

- **Context supplied** through the optional `context` property: candidates whose `norm_context` does not equal the normalized supplied value are excluded. If that removes every candidate, the unfiltered result is returned with `match: false` on all rows.
- **Context absent**: behavior is exactly tier 1. Label similarity decides the score, and duplicate normalized labels already suppress automatic matches.

The fallback exists because a property value is free text. Returning an empty result would hide usable suggestions; silently ignoring a wrong context value would risk a wrong automatic match. Narrowing with a visible fallback keeps the failure mode obvious.

### 4. Derived labels for entities with no text label

A spec may declare `label_expression` instead of `label_column`:

```yaml
coordinate_method_dimension:
  name: "Coordinate Method Dimensions"
  table_name: "tbl_coordinate_method_dimensions"
  id_column: "coordinate_method_dimension_id"
  label_expression: "m.method_name || ' / ' || d.dimension_name"
  joins:
    - "join public.tbl_methods m using (method_id)"
    - "join public.tbl_dimensions d using (dimension_id)"
  reconciliation: scoped
```

Rules:

- `label_column` and `label_expression` are mutually exclusive; both configure the same `label` and `norm_label` columns in the generated view.
- The expression is rendered into the existing template, so indexes, functions, and details queries follow the standard generated shape.
- This covers `coordinate_method_dimension` and gives a future option for label-less entities without a new code path.

### 5. Lookups

The 13 lookups with a usable label become `reconciliation: lookup`. Entries reuse `label_column`, optional `description_column`, and `scope_columns` where the business key is composite:

- flat: `chronology`, `data_provider`, `dating_lab`, `dating_material`, `ecocode_system`, `master_dataset`, `project`, `relative_ages`, `taxonomic_order_system`
- scoped: `feature` (`feature_type`), `taxa_common_names` (`taxa`), `taxa_synonyms` (`taxa`), `rdb_system` (`location`)

`sample_group` is not included: its role in the target model is `fact`, not `lookup`, so it is outside tier 2.

Lookup candidates follow tier-1 shape. `alt ref`-style identity columns are handled by the next section rather than by description scoring.

### 6. Alternate identity from configuration

`alternate_identity_column` becomes the source for `alternate_identity_sql`:

```sql
select <id_column> as id, label, 1.0 as name_sim
from authority.<key>
where <alternate_identity_column> = %(alternate_identity)s
limit 1
```

Rules:

- The generated query replaces the hand-written version in `src/resources/method.yml` and `src/resources/dimension.yml`.
- An entry without `alternate_identity_column` gets no alternate query, which is the current base-repository behavior.
- The property list gains the alternate identity as a declared property, matching how `method` and `dimension` expose abbreviations today.

### 7. `dimension` repair

`dimension` moves here from tier 1 and becomes a scoped lookup-style entry:

- Add the `config/entities.yml` entry with `label_column: dimension_name` and `alternate_identity_column: dimension_abbrev`. The model's unique set is `dimension_abbrev` alone, so no `scope_columns` are needed.
- Generate the view and function, then delete `src/resources/dimension.yml` and `src/strategies/dimension.py`.
- Verify the description column against the live schema before choosing `description_column`. The standard model does not list `dimension_description`, and `src/resources/dimension.yml` uses it.

### 8. Inherited guarantees

Tier 2 preserves the completed simple-classifier contract: views include `description` and `norm_description` even when both are null; fuzzy functions keep the four-parameter signature and five base result columns; and simple entities publish no OpenRefine property mappings. Scoped functions and views add context, and scoped types may declare the optional `context` property. The path also retains the 500-character candidate description limit, opt-in `description_match_weight` with a default of `0`, `label_sim`-only `match`, duplicate-label suppression, explicit `support` declaration on every registration, startup validation of `table_specs`, and `deployment/container/config/entities.yml` parity.

Extending startup validation: a `scoped` entry must declare at least one `scope_column` that resolves to a configured entity label, and a `lookup` entry must declare a label. Either failing is a startup error, not a runtime surprise. A `lookup` entry that also sets `description_match_weight` above `0` is rejected, because lookups must resolve on label.

## Alternatives Considered

- **Keep the 14 scoped classifiers as tier-1 ambiguous suggestions.** Rejected. It is safe but leaves the highest-volume vocabularies unhelpful: `colour`, `site_type`, and `value_type_item` all repeat labels by design.
- **Move the 14 scoped classifiers out of tier 1 and into tier 2.** Rejected. Tier 1 is implemented, and duplicate-label suppression keeps its current behavior safe. Tier 2 upgrades accuracy in place rather than rewriting the completed scope.
- **Add a bespoke strategy class per scoped entity.** Rejected. It reintroduces the artifact duplication tier 1 removes.
- **Treat a supplied context as a score boost instead of a narrowing filter.** Rejected. A boost can still auto-accept a candidate from the wrong parent, while narrowing with a visible fallback cannot.
- **Reconcile lookups through the classifier path with description scoring enabled.** Rejected. Lookups must resolve to an existing row, so a lookup ignores `description_match_weight` and can never rank on description text.
- **Fold `feature`, `rdb_system`, and `taxa_common_names` into their parent aggregates instead of reconciling them.** Deferred. That is the right long-term identity model, but it depends on SIMS work outside this service.

## Risks And Tradeoffs

- Joins to parent tables make generated views depend on parent tables having rows. A colour whose method is missing would disappear from the view if the join is inner. Use a left join and accept null context rather than dropping rows.
- Concatenated context strings are display aids, not keys; two parents with the same name still produce the same context text. The duplicate-label rule keeps that safe.
- `lookup` semantics differ from `simple` only in defaults, which is a small conceptual difference for reviewers to hold. The diagnostic label in the manifest is the mitigation.
- Adding joins to generated views increases regeneration and deployment surface. Schema snapshots for tier-1 entities must confirm their output is unchanged from the completed simple-classifier contract baseline.
- `label_expression` allows arbitrary SQL fragments in configuration. It is restricted to identifier and `||` usage by review, and must never interpolate user input.
- Repairing `dimension` may require correcting an unverified column name, which cannot be confirmed without database access. This is a phase-1 gate, not an assumption.
- Lookup reconciliation exposes admin-maintained vocabularies through the public manifest. That is the same exposure `site` and `location` already have.

## Testing And Validation

- Marker parsing: `simple`, `scoped`, and `lookup` entries produce the expected view and function shapes; an unknown marker fails startup validation.
- Scope generation: a scoped entry produces `context`, `norm_context`, and readable parent names; a missing scope target fails startup.
- Context behavior: supplied context narrows; a supplied context matching nothing returns the unfiltered set with `match: false` on every row; absent context matches tier-1 behavior exactly.
- Derived label: `label_expression` renders into `label` and `norm_label`, and declaring both `label_column` and `label_expression` fails validation.
- Alternate identity: generated SQL replaces the hand-written queries for `method` and `dimension`; an entity without `alternate_identity_column` returns no alternate candidates.
- Lookups: each registered lookup ignores `description_match_weight` and never returns a description-driven score or match.
- `dimension`: details and fuzzy queries succeed against the regenerated schema, and the description column is verified before merge.
- Schema snapshots: tier-1 entities generate identical SQL before and after tier 2 relative to the completed simple-classifier contract baseline, including `authority.site`, `authority.feature_type`, and `authority.fuzzy_method`.
- HTTP level: `POST /reconcile` for `colour` with and without a `context` property returns the expected `match` flags.
- Database smoke test on a disposable schema: one scoped classifier, one scoped lookup, one flat lookup, and `dimension`.
- Deployment parity: classifier and lookup entries plus markers match across `config/entities.yml`, `tests/config/entities.yml`, and `deployment/container/config/entities.yml`.

## Acceptance Criteria

- `P2-AC-1`: The 14 context-dependent classifiers and the 4 context-dependent lookups are registered as `scoped` and expose `context` and `norm_context` in their generated view and fuzzy function.
- `P2-AC-2`: The 9 flat lookups are registered as `lookup`, and a lookup never scores or matches on description text.
- `P2-AC-3`: A supplied `context` property narrows the candidate set to the matching parent, and an unmatched supplied context returns the unfiltered set with `match: false` on every row.
- `P2-AC-4`: `coordinate_method_dimension` is reconcilable through a configured `label_expression`, and a spec declaring both `label_column` and `label_expression` fails validation.
- `P2-AC-5`: `dimension` has a table spec, a generated view and function, verified column names, and no remaining `src/resources/dimension.yml` or `src/strategies/dimension.py`.
- `P2-AC-6`: Alternate-identity SQL is generated from `alternate_identity_column`, and `method` behaves as before with no hand-written query.
- `P2-AC-7`: `contact`, `abundance_element_group`, `dataset`, `taxa`, and the specialized strategies are unchanged, and their exclusion reasons appear in the reconciliation type inventory register tracked by [issue #43](https://github.com/humlab-sead/sead_authority_service/issues/43).
- `P2-AC-8`: Generated SQL for every existing `simple` entity is unchanged from the completed simple-classifier contract baseline, and that contract's regression tests pass without modification.
- `P2-AC-9`: A `scoped` entry without a resolvable scope target, or a `lookup` entry without a label, fails startup with a named error.
- `P2-AC-10`: Classifier and lookup configuration is identical across production, test, and deployment container configuration files.

## Planning Handoff

Confirmed decisions:

- Extend the tier-1 configured path; do not add per-entity classes.
- Keep the 14 scoped classifiers registered by tier 1; tier 2 upgrades their accuracy in place.
- `reconciliation` values are `simple`, `scoped`, and `lookup`, each handled by the same strategy class.
- Context is a narrowing filter with a visible fallback, never a score boost.
- `lookup` ignores description scoring entirely; `scoped` inherits the tier-1 opt-in `description_match_weight` and its `label_sim`-only `match` rule.
- `label_expression` and `label_column` are mutually exclusive.
- Parent joins use a left join so rows without a parent are not silently dropped.
- `dimension` is repaired here and removed from tier 1.

Constraints and behavior to preserve:

- Preserve the completed simple-classifier contract: uniform view columns, the four-parameter/five-result fuzzy function contract, and no OpenRefine properties on existing `simple` entities. Scoped entities add only the optional `context` property defined here.
- Preserve the tier-1 500-character candidate limit, opt-in `description_match_weight` with a default of `0`, `label_sim`-only `match`, duplicate-label suppression, support declaration, startup validation, and deployment parity.
- `Strategies.items` remains a plain dict; the manifest is derived from declared support status.
- Generated schema remains authoritative and produced by `src/scripts/generate_entity_schema.py`.
- Generated SQL for existing `simple` entities must remain identical to the completed simple-classifier contract baseline.
- Do not write to production data.
- Exclusion reasons for tier-2 entities are recorded in the reconciliation type inventory register tracked by [issue #43](https://github.com/humlab-sead/sead_authority_service/issues/43), not in `entities.yml` or in registration metadata.

Expected validation outcomes:

- One schema generation command produces scoped views and functions with readable context.
- A disposable-database smoke test reconciles a scoped classifier, a scoped lookup, a flat lookup, and `dimension`.
- The completed simple-classifier contract's schema snapshots and regression tests pass unchanged.

Open questions to resolve during phase planning:

- Does `tbl_dimensions.dimension_description` exist in the live schema, and if not, which column should `dimension` use as its description? Resolve before the `dimension` migration task.
- Should the taxonomy chain (`taxa_tree_order`, `taxa_tree_family`, `taxa_tree_genus`, `taxa`) be treated as one scoped hierarchy in this tier, or keep its current split between tier 1 and the specialized `taxon` strategy?
- Should `contact` become reconcilable through a derived `first_name || ' ' || last_name` label, or stay out of scope?
- Should `value_qualifier_symbol` be reconciled through its parent `value_qualifier`, or stay excluded?
- Is a cross-repository sync check against `sead_standard_model.yml` required, or is the checked-in `entities.yml` snapshot sufficient? Tier 2 adds parent-context and lookup coverage, which multiplies the places where a target-model change silently diverges from service configuration, so the answer decides whether that drift is detected or only documented.
- Where should the cross-repository check run: a test that reads a vendored copy of the model, a scheduled comparison against the Shape Shifter repository, or a manual review step at release?

## Final Recommendation

Adopt tier 2 as an additive layer on the implemented tier-1 path and its completed simple-classifier contract. Parent context, derived labels, and lookup markers fit the same configured strategy, so the work stays configuration and template work rather than new per-entity code. Deferring tier 2 remains safe: duplicate-label suppression prevents wrong automatic matches, leaving only less precise candidate lists.
