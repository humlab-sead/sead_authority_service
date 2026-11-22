# Proposal: Fuzzy Reconciliation for Classifier Entities

## Status

- **Implemented and validated** (Phases 1–3; production deployment was out of scope).
- Scope: `sead_authority_service` reconciliation for target-model entities whose role is `classifier`
- Goal: enable trigram fuzzy matching on classifier name and, where a description column exists, on description, without adding per-entity Python classes, resource YAML, or hand-written SQL
- Validation: Disposable-schema details and fuzzy queries passed for all 45 marked types; representative HTTP checks and the `rdb_code` generated-view population recheck passed. See the [Phase 1 task plan](./CLASSIFIER_FUZZY_RECONCILIATION_PHASE_1_TASK_PLAN.md), [Phase 2 task plan](./CLASSIFIER_FUZZY_RECONCILIATION_PHASE_2_TASK_PLAN.md), and [Phase 3 task plan](./CLASSIFIER_FUZZY_RECONCILIATION_PHASE_3_TASK_PLAN.md).
- Follow-up: Production deployment remains separate work.

## Summary

The Shape Shifter standard target model (v2.8.0) declares 53 classifier entities. Only a few are registered reconciliation types today, and each one currently needs three hand-maintained artifacts plus generated SQL. Missing classifiers return `Unknown query type` from `POST /reconcile`, so OpenRefine users cannot reconcile most controlled vocabularies.

The recommendation is a single configured-classifier path driven by `config/entities.yml`. Marked entities get a stable view column contract, a fuzzy function that returns description and can optionally score it, and one shared strategy class. Description scoring is off by default and enabled for `rdb_code`, the only proposed code-label classifier that passed the population gate. When enabled it only reorders candidates, because automatic matching is always decided from label similarity. Unmarked entities keep their current generated views, functions, and resource SQL unchanged.

Support status becomes an explicit registration declaration, so the reconciliation manifest no longer depends on a hand-maintained tuple and a new registration cannot become supported by default.

The existing simple classifier implementations `feature_type` and `data_type` move to this path. `feature_type` currently has a broken details query and is used as the reference case. `dimension` is deferred to the tier-2 proposal, which owns its missing table spec, view, and unverified column. `sampling_context` stays on its current path because it has a custom details query.

## Problem

- 53 target-model entities have `role: classifier`. 52 have a target table; `abundance_element_group` is project-local and has no table.
- 45 classifier entities with tables have no registered strategy and cannot be reconciled at all.
- Adding one classifier currently requires: an `entities.yml` table spec, a `src/resources/<key>.yml` specification, a `src/strategies/<key>.py` registration class, and regenerated schema. Copying that pattern for the remaining classifiers produces more than 120 small files.
- The three-artifact pattern already drifts. The generated views and the resource SQL disagree:
  - `src/resources/feature_type.yml` selects `description` from `authority.feature_type`, but the generated view exposes `feature_type_description`.
  - `src/resources/data_type.yml` selects `dt.description` and joins on `data_type_group_id`; the generated `authority.data_type` view exposes `definition` and no `data_type_group_id`.
  - `src/resources/location.yml` selects `description`, but `location` has no configured `description_column`, so the generated view has no such column. `location` is a specialized strategy and is outside this change, but it shows the same failure mode.
  - `config/entities.yml` declares `description_column: description` for `dating_uncertainty`, but the standard model lists only `uncertainty` on `tbl_dating_uncertainty`. A read-only staging schema check on 2026-11-14 confirmed the physical `description` column exists there; verify each deployment target before using it.
  - `src/resources/dimension.yml` selects from `authority.dimension`, but no `schema/generated/dimension.sql` exists and `config/entities.yml` has no `dimension` entry. `dimension` is nevertheless listed in `SUPPORTED_RECONCILIATION_TYPES`. Tier 1 does not repair this; the tier-2 proposal owns it.
- Generated `authority.fuzzy_<key>` functions score only the label. Description text is unused, even where the view already carries it.
- `SUPPORTED_RECONCILIATION_TYPES` in `src/metadata.py` is a hand-maintained tuple. A new strategy stays invisible until someone edits the tuple, and the tuple can name a type whose matcher does not work.

## Scope

- Add a `reconciliation: simple` marker to the `config/entities.yml` entries that qualify for generic classification.
- For marked entities only, expose `description` and `norm_description` in the generated view.
- For marked entities only, return `description` from the generated fuzzy function, and score it only when a non-zero description weight is configured.
- Enable description scoring for `rdb_code`; keep `age_type`, `relative_age_type`, and `value_qualifier` on the generic label-only path until they pass a new population check and a separate enablement decision.
- Make automatic matching depend on label similarity alone, so no threshold setting can turn a description hit into an automatic match.
- Make match thresholds service configuration passed as function parameters, so no database setting can change reconciliation results.
- Add one shared configured-classifier strategy and register it for every approved classifier key.
- Generate reconciliation details SQL from the table spec so no per-entity SQL is required.
- Apply a 500-character candidate description limit and an ambiguity rule for duplicate exact labels.
- Replace the hand-maintained supported-type tuple with a declared status on every registration.
- Migrate `feature_type` and `data_type` to the generic path, and defer `dimension` to tier 2.
- Validate classifier configuration at startup and keep deployment configuration templates in sync.

## Non-Goals

- The existing specialized strategies: `site`, `location`, `method`, `taxon`, `modification_type`, `bibliographic_reference`, `administrative_region`, `country`, and `geonames`.
- Classifiers without a usable text label: `coordinate_method_dimension` and `value_qualifier_symbol`.
- `abundance_element_group`, which has no target table.
- `dimension`. Deferred to [tier 2](../../CLASSIFIER_FUZZY_RECONCILIATION_TIER_2.md), which owns its table spec, generated view, and column verification.
- Alternate-identity matching beyond the existing `alternate_identity_column` behavior.
- Embeddings, semantic search, LLM disambiguation, SIMS identity allocation, and OpenRefine UI changes.
- Renaming existing reconciliation type IDs; Shape Shifter project configuration references them.
- Production data changes or deployment.

## Current Behavior

Reconciliation requires a registered strategy. `src/reconcile.py` rejects an unregistered type before any candidate query runs. `src/metadata.py` publishes two lists:

- `defaultTypes`: every key in `Strategies.items`, built from static `@Strategies.register` decorators loaded at import time.
- `reconciliation.supportedTypes`: the hard-coded `SUPPORTED_RECONCILIATION_TYPES` tuple, which currently lists 10 types.

Registration is import-time static. Configuration is only available after `setup_config_store()` runs at application startup, so registration cannot read `table_specs` at import time without a lifecycle change.

Two further constraints shape the design:

- `GET /reconcile` instantiates every registered strategy to build `defaultTypes` and property settings. A strategy whose specification cannot resolve therefore breaks the manifest for every type, not only its own.
- `ReconCandidate.description` is limited to 500 characters, and the candidate model applies to every reconciliation type. A description returned without truncation can fail response validation.

Classifiers with a registered strategy today: `data_type`, `dimension`, `feature_type`, `method`, `modification_type`, `sampling_context`, and `taxon`. `method`, `modification_type`, and `taxon` are specialized and stay as they are. `taxon` is registered but intentionally excluded from `supportedTypes` because its matcher returns no candidates.

## Proposed Design

### 1. One table-spec marker

A classifier qualifies for the generic path when its `config/entities.yml` entry declares `reconciliation: simple` and defines a text `label_column`. The existing `id_column`, `label_column`, and `description_column` fields remain the source for generated SQL. The marker also gates every generated change in this proposal, so an unmarked entry generates exactly what it generates today.

```yaml
feature_type:
  name: "Feature Types"
  table_name: "tbl_feature_types"
  id_column: "feature_type_id"
  label_column: "feature_type_name"
  description_column: "feature_type_description"
  reconciliation: simple
```

Optional fields:

- `description_match_weight`: defaults to `0`. A value greater than `0` enables description scoring with that coefficient. `0` returns description but never matches, scores, or scans on it.
- `details_columns`: extra columns already exposed by the generated view to add to the details response. Default is ID and Name, plus Description when configured.

Thresholds are not per-entity. They are service configuration under `options:reconciliation` in `config/config.yml`, alongside the existing `auto_accept_threshold`:

```yaml
options:
  auto_accept_threshold: 0.90
  reconciliation:
    label_threshold: 0.30
    description_threshold: 0.50
```

The marked set is a closed inventory. Enabling a classifier requires two edits: its `entities.yml` entry and its key in the static `CLASSIFIER_KEYS` tuple. A drift test compares the two in both directions; the proposal states the two-location change rather than claiming configuration-only enablement. Keeping this set aligned with `role: classifier` in the Shape Shifter standard model is a maintenance check, not a runtime dependency.

### 2. Generated view contract for marked entities only

The template applies the alias contract only when `reconciliation: simple` is set. Specialized views keep their current column names.

```sql
create or replace view authority.feature_type as
select
  t.feature_type_id,
  t.feature_type_name as label,
  authority.immutable_unaccent(lower(t.feature_type_name)) as norm_label,
  t.feature_type_description as description,
  authority.immutable_unaccent(lower(t.feature_type_description)) as norm_description
from public.tbl_feature_types as t;

create index if not exists tbl_feature_types_norm_desc_trgm
  on public.tbl_feature_types
  using gin ((authority.immutable_unaccent(lower(feature_type_description))) gin_trgm_ops);
```

Rules:

- The description column is aliased to `description`. The physical name disappears from the view for marked entities only.
- The ID column keeps its physical name. `label` stays the display label.
- Entities without a description column get no `description` or `norm_description` column.
- The description trigram index is generated only when `description_match_weight` is greater than `0`, so the default path adds no index and no write cost.
- Unmarked entities generate exactly today's output. `authority.site` keeps `site_description`, which `src/resources/site.yml` selects, and `authority.method` keeps its current shape.
- `alternate_identity_column` and `extra_columns` behavior is unchanged.

### 3. Fuzzy function contract and scoring (marked entities only)

A marked entity with a description column returns it, so the repository row carries it whether or not description scoring is enabled. Thresholds are explicit parameters with defaults, and the comparisons are explicit:

```sql
create or replace function authority.fuzzy_feature_type(
  p_text text,
  p_limit integer default 10,
  p_label_threshold double precision default 0.30,
  p_description_threshold double precision default 0.50
) returns table (
  feature_type_id integer,
  label text,
  description text,
  name_sim double precision
) ...
```

With a non-zero `description_match_weight`, the body adds description scoring as a secondary term:

```sql
with params as (
  select authority.immutable_unaccent(lower(p_text))::text as q
),
scored as (
  select
    s.feature_type_id,
    s.label,
    s.description,
    case when s.norm_label = pq.q then 1.0
         else similarity(s.norm_label, pq.q) end as label_sim,
    coalesce(strict_word_similarity(pq.q, s.norm_description), 0) as description_sim
  from authority.feature_type as s
  cross join params pq
  where similarity(s.norm_label, pq.q) >= p_label_threshold
     or strict_word_similarity(pq.q, s.norm_description) >= p_description_threshold
)
select
  feature_type_id,
  label,
  description,
  label_sim,
  description_sim,
  least(1.0, label_sim + 0.15 * description_sim) as name_sim
from scored
order by name_sim desc, label_sim desc, label
limit p_limit;
```

The `or strict_word_similarity(...) >= p_description_threshold` predicate and the `description_sim` terms are emitted only when the weight is non-zero. With the default weight of `0`, the body is the current label-only query.

Scoring rules:

- An exact normalized label match scores `1.0`.
- Label similarity is used unchanged.
- The weight is fixed at generation time and defaults to `0`; typical enabled values are `0.10` to `0.20`. Above roughly `0.2`, a description hit can outrank a usable label match, which is wrong where the label is the identity.
- Description similarity uses `strict_word_similarity` (`<<%`). Plain `similarity` is diluted by description length, so a short query against a long description scores near zero, and `word_similarity` (`<%`) additionally matches fragments inside longer words.
- Automatic matching is decided from `label_sim`, never from `name_sim`. Description can therefore only reorder candidates; no `auto_accept_threshold` value can promote a description-only hit to an automatic match.
- The label and description predicates compare against `p_label_threshold` and `p_description_threshold` rather than relying on `pg_trgm` GUCs. Thresholds are service configuration, so they appear in review, are identical across environments, and are assertable in a test.
- The cost of an explicit comparison is that these predicates are not index-accelerated. Classifier tables are small, so the scan is trivial. If an entity's base table grows large, add the `%` or `<<%` operator as a prefilter alongside the parameterized comparison and record a database-setting requirement for that entity only.
- `order by name_sim desc, label_sim desc` breaks ties toward label evidence.
- OpenRefine re-sorts candidates by `score` on the client, so `score` carries the combined value. A row can therefore display a high score with `match: false`.
- Entities without a description column keep the current three-column signature.
- Unmarked entities keep their current function body and signature. `src/resources/method.yml` calls `authority.fuzzy_method`, so its scoring must not change.

#### Which entities enable it

Enable description scoring only where the label is a code, abbreviation, or symbol. A short code produces few trigrams, so a user who types the meaning can never match the label, and the description carries all the recall. Where the label is already a descriptive name, description scoring adds no recall and only dilutes ranking.

| Entity | Label column | Label content | Description column | Scoring decision |
|---|---|---|---|---|
| `age_type` | `age_type` | `AD`, `BC`, `BP` | `description` | Off: 1 distinct description and 1 distinct label |
| `relative_age_type` | `age_type` | `AD`, `BC`, `BP`, `cal BP` | `description` | Off: 10 of 14 rows have descriptions |
| `rdb_code` | `rdb_category` | `EN`, `VU`, `NT`, `LC` | `rdb_definition` | On: 27 of 27 described; 27 descriptions, 20 labels |
| `value_qualifier` | `symbol` | `+`, `-`, `?`, `ca.` | `description` | Off: 13 distinct descriptions and 13 distinct labels |

Read-only checks on 2026-11-14 through the `SEAD TNG (9023)` profile's `sead_staging` database returned these physical-table counts (the separate `SEAD Staging (5433)` profile was unavailable):

| Entity | Rows | With description | Distinct labels | Distinct descriptions |
|---|---:|---:|---:|---:|
| `age_type` | 1 | 1 | 1 | 1 |
| `relative_age_type` | 14 | 10 | 14 | 10 |
| `rdb_code` | 27 | 27 | 20 | 27 |
| `value_qualifier` | 13 | 13 | 13 | 13 |

The generated view was unavailable for three of the four keys, so each count used the same physical label and description columns specified for its planned view. Recheck `rdb_code` against the generated view before merge. The other 44 tier-1 classifiers keep the default weight of `0`. Four need a label choice rather than description scoring:

- `identification_level` uses `identification_level_name` ("Species", "Genus") as its label; the abbreviation is the unique key, not the label.
- `unit` uses `unit_name` ("millimetre") as its label; matching an abbreviation such as `mm` is alternate-identity behavior, which tier 2 owns.
- `ecocode_definition` and `ecocode_group` use `name` as the label and keep `definition` as a returned description without scoring it.

Seven tier-1 classifiers have no description-like column in the standard model and cannot enable scoring: `colour`, `language`, `season`, `taxa_tree_author`, `taxa_tree_family`, `taxa_tree_genus`, and `taxa_tree_order`. The model also omits `dating_uncertainty.description`, although it exists on the checked staging table; leave its weight at zero.

Enablement requires a data-population check against the generated view before merge:

```sql
select count(*) as rows,
       count(description) as with_description,
       count(distinct label) as distinct_labels,
       count(distinct description) as distinct_descriptions
from authority.<key>;
```

Enable the weight only when descriptions are present on more than 80% of rows and the descriptions are more distinct than the labels. Otherwise the weight adds scan cost and no recall, so the entry keeps `description_match_weight: 0`.

### 4. One configured classifier strategy

Add `ConfiguredClassifierStrategy(ReconciliationStrategy)` with no entity-specific logic. A single registration module creates one dynamically named subclass per key, because `Strategies` stores one `_registry_key` per class:

```python
# One entry per approved classifier. A matching table spec is required.
CLASSIFIER_KEYS = ("abundance_element", "activity_type", "...")

for key in CLASSIFIER_KEYS:
    strategy_cls = type(f"{key.title().replace('_', '')}ReconciliationStrategy", (ConfiguredClassifierStrategy,), {})
    Strategies.register(key=key, repository_cls=BaseRepository, support="supported")(strategy_cls)
```

Behavior:

- `resolve_specification(key)` falls back to `table_specs.<key>` when no `src/resources/<key>.yml` exists, building `id_field`, `label_field`, `display_name`, and `sql_queries`.
- The fuzzy query defaults to `authority.fuzzy_<key>(%(q)s::text, %(n)s::int)`. The base repository returns the function's columns unchanged, so `description` reaches the candidate step without a repository change.
- The details query is generated from the spec and reads untruncated text:

```sql
select s.feature_type_id as "ID", s.label as "Name", s.description as "Description"
from authority.feature_type as s
where s.feature_type_id = %(id)s::int
```

- `as_candidate` copies `description` into the candidate payload when the row provides it, truncated to 500 characters to satisfy `ReconCandidate.description`. The details response keeps the full value. The `match` flag uses `label_sim`, so a description-driven score can never produce `match: true`.
- Ambiguity rule for marked classifiers: when two or more candidates in one result share the same normalized label, none is marked `match: true`, even at score `100`. The rows stay visible as ranked suggestions, and the duplicate set is computed before candidate conversion.
- Explicit registrations keep precedence. `Strategies.items` is not replaced.
- No config is read at import time. Specification resolution happens when a strategy is instantiated, and startup validation runs after configuration loads. Ambiguity grouping runs per reconciliation query, before candidate conversion.

### 5. Explicit support status

Registration alone does not establish support. Every registration declares it:

```python
@Strategies.register(key="taxon", repository_cls=TaxonRepository, support="excluded")
```

`StrategyRegistry.registered_class_hook` already receives decorator arguments and stores the value on the class. `src/metadata.py` then derives both lists from the declaration instead of a hand-maintained tuple:

```python
SUPPORTED = tuple(sorted(k for k, cls in Strategies.items.items() if cls.support_status == "supported"))
EXCLUDED = tuple(sorted(k for k, cls in Strategies.items.items() if cls.support_status == "excluded"))
```

Rules:

- Every registration must declare `support` as `supported` or `excluded`. A missing or unknown value fails a test that enumerates `Strategies.items`, so a new registration cannot inherit support.
- Generic classifiers declare `supported` because their candidate query, view, and details query are generated and covered by schema and configuration tests.
- Declaring a status is a review decision. An excluded type keeps its `defaultTypes` entry so OpenRefine can still address it, but it is omitted from `supportedTypes`.
- The status stays in registration metadata, because that is what the manifest reads and it cannot drift from the registry. The reason for each exclusion is recorded in the reconciliation type inventory register tracked by [issue #43](https://github.com/humlab-sead/sead_authority_service/issues/43), which also carries the checked-in snapshot of every target-model entity and its disposition.
- This split keeps the two facts where they can be trusted: code answers what the API publishes, and the register answers why an entity is absent.

### 6. `feature_type` as the reference migration

- Delete `src/strategies/feature_type.py` and `src/resources/feature_type.yml`.
- Keep the `feature_type` key through `CLASSIFIER_KEYS` and the `entities.yml` entry.
- Replace feature-type-specific unit tests with generic classifier tests plus one feature-type smoke case.
- Apply the same migration to `data_type`, deleting its resource YAML and Python class.
- Keep `sampling_context` on its current registered path because its details query returns related description types that the generic details query does not reproduce.
- Exclude `dimension` from `CLASSIFIER_KEYS` and from the marked set. It keeps `src/strategies/dimension.py` and `src/resources/dimension.yml` unchanged until tier 2 replaces them.

### 7. Configuration validation and deployment workflow

`GET /reconcile` instantiates every registered strategy, so an unresolvable classifier specification breaks the manifest for all types. Two additions prevent that:

- Startup validation: after configuration loads, confirm every `CLASSIFIER_KEYS` key exists in `table_specs` with `reconciliation: simple`, a text `label_column`, and an integer `id_column`. Fail startup with a named error rather than serving a partial manifest.
- Threshold validation: `options:reconciliation:label_threshold` and `description_threshold` must be present and inside `0 < value <= 1`. Fail startup with a named error otherwise, rather than falling back to a default that nobody reviewed.
- Deployment configuration: the repository root `config/` is the only tracked source for runtime YAML. Setup initializes an empty mounted directory from that source and reports missing or changed files without overwriting them. `--sync-config` explicitly replaces the four managed files. Use the source revision associated with the image unless an intentional mounted override is documented. The required release order is schema, then runtime configuration, then application code.
- Deployment guidance states that reconciliation results do not depend on any `pg_trgm.*` database setting, so a database administrator cannot change match behavior silently.

## Alternatives Considered

- **Copy the current pattern for each classifier.** Rejected. It creates more than 120 files, and the existing drift in four resource files shows the copies are not reliably maintained.
- **Generate per-entity Python and YAML files from a script.** Rejected. It keeps many static artifacts and adds a build step without removing the duplicate sources of truth.
- **Register from configuration after startup.** Viable and closer to a single source of truth, but it couples strategy registration to the configuration lifecycle and requires every entry point (FastAPI startup, tests, scripts) to run the bootstrap. A static key tuple with a drift test is simpler, and the list changes rarely.
- **Use `sead_utility.full_text_search` for all classifiers.** Deferred. It spans tables with heterogeneous ID semantics, needs a refresh step, and gives less control over per-type ranking and limits.
- **Extend only `feature_type`.** Rejected. It fixes one entity and leaves the inventory unsupported.
- **Apply the alias and scoring changes to every entity.** Rejected. `src/resources/site.yml` selects `site_description` from `authority.site`, and `src/resources/method.yml` calls `authority.fuzzy_method`; a global change breaks one details query and silently re-ranks the other. Gating on `reconciliation: simple` keeps both contracts intact.
- **Register classifiers by reading `entities.yml` at import time.** Rejected. The running service can mount an external configuration file, so an import-time read can differ from the configuration the service actually uses. Static registration with startup validation keeps one runtime source of truth.
- **Mark every exact label match as automatic.** Rejected for composite-label classifiers such as `colour`, where identical labels legitimately repeat across rows. Automatic matching would be arbitrary rather than correct.
- **Derive `supportedTypes` as `registered - excluded`.** Rejected. Every new registration would become supported automatically, so the manifest could advertise a matcher nobody reviewed.

## Risks And Tradeoffs

- The template now produces two view and function contracts. Schema tests must cover both branches, including snapshots for unmarked entities such as `authority.site` and `authority.fuzzy_method`.
- Startup validation turns a missing classifier entry into a failed start. That is intentional, but it must ship with deployment parity or an externally mounted configuration can stop a new image from starting.
- Description matching is opt-in and off by default, so the common path is unchanged. When enabled it reorders candidates and can surface loosely related vocabulary; the small weight, the exact-label rule, and per-entity opt-in limit the effect.
- Candidate descriptions are truncated at 500 characters. Users see partial text in the candidate list; the full text stays in details.
- The ambiguity rule suppresses automatic matches for duplicate exact labels. Classifiers with composite keys therefore need manual selection, which is the intended behavior but changes the review effort.
- `score` is the combined value while `match` follows label similarity alone, so OpenRefine can show a high score next to `match: false`. That is intended, but it will be reported as a defect if it is not documented.
- Thresholds live in service configuration rather than the database, so a threshold change is a configuration release, not a database change. That is the intended trade, but it means a threshold experiment needs a config update rather than a `SET` statement.
- Explicit threshold comparisons are not index-accelerated. Classifier tables are small, so this is trivial today; the documented escape hatch is a per-entity prefilter when a base table grows.
- Publishing 45 generic classifier types (43 newly registered) grows `defaultTypes` and `supportedTypes`. A larger OpenRefine type list is noisy but preferable to silent `Unknown query type` errors.
- Some labels are codes or symbols (`value_qualifier`, `rdb_code`, `identification_level`). Description matching carries most of the search value there, and match quality will vary. Only `rdb_code` passed the 2026-11-14 population gate; live-data checks cannot run in CI.
- `config/entities.yml` declares a description column for `dating_uncertainty` that the standard model does not list. The staging table has the column; confirm it exists in the deployment target before returning a description.
- `dimension` stays declared supported in `src/metadata.py` while its details query references a view that does not exist. Tier 1 leaves that pre-existing defect in place; tier 2 owns the repair, so it must not be treated as covered here.
- `CLASSIFIER_KEYS` duplicates the `entities.yml` marker list. A drift test and startup validation are both required; without them the two can diverge silently.
- Regenerating schema changes generated views and functions. Deployment must apply schema, then runtime configuration, then application code.
- The description index is created only for entities that enable description scoring. Classifier tables are small, so the cost is low, and the default path pays nothing.
- Cross-repository alignment with `role: classifier` is manual. Shape Shifter is not a runtime dependency of this service.

## Testing And Validation

- Specification fallback: a key with no resource YAML resolves `id_field`, `label_field`, `display_name`, and the generated details SQL from `table_specs`.
- Registration: every `CLASSIFIER_KEYS` key is registered; every entry in `Strategies.items` declares a valid support status; generic keys declare `supported`; explicit registrations keep their declared status and behavior.
- Drift: `CLASSIFIER_KEYS` and the `table_specs` entries marked `reconciliation: simple` match in both directions.
- Candidate payloads: label match, opt-in description scoring, combined score, `match` derived from label similarity, description passthrough, truncation at exactly 500 characters, and the ambiguity rule with duplicate labels.
- Description default: an entity without `description_match_weight` generates no description predicate and no description index, and a description-only hit returns `match: false` even when its score is high.
- Description weight: a configured weight raises the score of a description match, and an exact label match still outranks a better description match.
- Enable list: only `rdb_code` carries a non-zero weight, and every other tier-1 entry carries `0` or omits the field.
- Population gate: a recorded check per enabled entity shows descriptions present on more than 80% of rows and more distinct descriptions than labels.
- Thresholds: a configured `label_threshold` changes which label candidates are returned, and the same query returns the configured result regardless of any session `pg_trgm` setting.
- Threshold validation: a missing or out-of-range `options:reconciliation` value fails startup with a named error.
- Schema: run `generate_entity_schema.py --all --force` and assert marked entities expose `description`, `norm_description`, and a `description` return column, and that unmarked entities keep today's columns, including `authority.site.site_description` and the `authority.fuzzy_method` signature.
- Specialized regression: snapshot the generated SQL for `site`, `method`, `location`, and the other unmarked strategies and confirm identical output before and after the template change.
- Exclusion: `dimension` has no `entities.yml` entry, is absent from `CLASSIFIER_KEYS`, and its strategy and resource files are unchanged until tier 2.
- Startup validation: a registered classifier with no `table_specs` entry fails startup with a named error; a valid configuration serves the manifest.
- HTTP level: `POST /reconcile` for a classifier whose description exceeds 500 characters returns a valid response with a truncated `description`.
- Database smoke test on a disposable schema: for each marked classifier, run the details query for one row and the fuzzy function with a known label.
- Reconciliation smoke test: `POST /reconcile` for a representative entity from each category (name-only, name+description, code label, duplicate labels) returns the expected ordering and `match` flags.
- Deployment setup: initial mounted configuration comes from root `config/`; later syncs report differences and preserve mounted files unless `--sync-config` is used.

## Acceptance Criteria

- `P-AC-1`: The closed inventory of generic classifier types is registered, appears in `defaultTypes` and `supportedTypes`, and every classifier excluded from the inventory is documented with a reason.
- `P-AC-2`: Enabling a classifier requires one `entities.yml` entry and one `CLASSIFIER_KEYS` entry; no per-entity Python class, resource YAML, or hand-written SQL is required.
- `P-AC-3`: An exact normalized label match returns `score: 100` and `match: true` unless another candidate in the same result shares that normalized label, in which case all such candidates return `match: false`.
- `P-AC-4`: Description scoring is opt-in by `description_match_weight`, and a description-only match ranks below any equal label match when enabled.
- `P-AC-5`: Automatic matching is derived from label similarity alone, so a description-only match never returns `match: true` at any `auto_accept_threshold` value.
- `P-AC-6`: Candidates include `description` truncated to at most 500 characters when the row provides one, and details return the full value.
- `P-AC-7`: Details requests for every generic classifier succeed against the generated schema; no query references a column the generated view does not expose.
- `P-AC-8`: `feature_type` and `data_type` use the generic path with their redundant resource and Python files removed; `sampling_context` keeps its custom details behavior; `dimension` is absent from `CLASSIFIER_KEYS` and deferred to tier 2.
- `P-AC-9`: `coordinate_method_dimension`, `value_qualifier_symbol`, and `abundance_element_group` are not registered and are documented as excluded.
- `P-AC-10`: Every registration declares a support status, the manifest is derived from those declarations, and a registration without a valid status fails a test.
- `P-AC-11`: Unmarked entities keep their current generated views, function signatures, scoring, and resource SQL contracts; snapshots for `site` and `method` are unchanged.
- `P-AC-12`: A registered classifier without a valid `table_specs` entry fails startup with a named error, and deployment setup initializes `entities.yml` from root `config/entities.yml` and reports later differences without overwriting by default.
- `P-AC-13`: An entity with `description_match_weight` of `0` or absent generates no description predicate, no description index, and no description term in its fuzzy function.
- `P-AC-14`: Description scoring is enabled for exactly `rdb_code`, which passes the recorded population check; `age_type`, `relative_age_type`, and `value_qualifier` stay at zero weight pending new data and a separate decision.
- `P-AC-15`: Match thresholds come from `options:reconciliation` in service configuration and are passed to generated functions as parameters; no `pg_trgm.*` database setting affects reconciliation results.
- `P-AC-16`: A missing or out-of-range threshold fails startup with a named error, and deployment setup initializes `config.yml` from root `config/config.yml` and reports later differences without overwriting by default.

## Planning Handoff

Confirmed decisions:

- Use one configured path, not per-entity copies.
- Gate every generated change on `reconciliation: simple` so unmarked entities keep their current contracts.
- Reuse existing type IDs. Do not add aliases for `sample_group_sampling_context` (`sampling_context`) or `taxa` (`taxon`/`taxa_tree_master`) in this change.
- Exclude `dimension` from the simple tier. Its table spec, generated view, and resource SQL are deferred to [tier 2](../../CLASSIFIER_FUZZY_RECONCILIATION_TIER_2.md).
- Keep static registration, and describe enablement as a two-location edit: `entities.yml` plus `CLASSIFIER_KEYS`.
- Return `description` from marked fuzzy functions whether or not description scoring is enabled; truncate candidates at 500 characters and keep full text in details.
- Description scoring is off by default. Enabling it sets `description_match_weight` between `0.10` and `0.20`, uses `strict_word_similarity`, and only reorders candidates.
- Description scoring is enabled only for `rdb_code`. The other three proposed code-label classifiers stay at zero weight; recheck `rdb_code` against the generated view before merge.
- `match` is computed from label similarity alone, so no threshold setting can promote a description hit to an automatic match.
- Thresholds are service configuration under `options:reconciliation`, passed to generated functions as `p_label_threshold` and `p_description_threshold`. No `pg_trgm` GUC affects results. The accepted cost is that those predicates are not index-accelerated.
- Suppress automatic matches when two or more candidates share a normalized label.
- Require an explicit support status on every registration.
- Use the [issue #43 interim inventory](https://github.com/humlab-sead/sead_authority_service/issues/43#issuecomment-6882183123) for excluded-classifier reasons until the checked-in generated register requested in that issue is delivered; do not put those reasons in `entities.yml` or registration metadata.
- Keep specialized strategies and their registration unchanged, including `sampling_context` and its custom details query.

Constraints and behavior to preserve:

- Registry pattern, absolute imports, line length 140, `loguru`, and async repository boundaries.
- `Strategies.items` remains a plain dict; tests, `suggest.py`, and the manifest depend on it.
- Existing `defaultTypes` ordering and public type IDs.
- Generated schema remains authoritative and generated by `src/scripts/generate_entity_schema.py`.
- Keep shared runtime YAML only under root `config/`. `tests/config/config.yml` remains a test-specific fixture with inline test data; deployment setup copies the four managed YAML files from root `config/`.
- `src/metadata.py` reads support status from registration metadata only; it must not read the inventory register, which is a documentation artefact.
- Required release order: schema, then runtime configuration, then application code.
- Do not write to production data.

Expected validation outcomes:

- One schema generation command produces every view and fuzzy function, with unmarked output unchanged.
- Manifest lists all supported classifiers and reflects declared support status.
- A disposable-database smoke test reconciles one classifier per category, including a duplicate-label case.
- Specialized strategy snapshot and regression suite pass unchanged.

Cross-repository drift against `sead_standard_model.yml` is out of scope for this tier. [Tier 2](../../CLASSIFIER_FUZZY_RECONCILIATION_TIER_2.md) decides whether a sync check is required or the checked-in snapshot is sufficient.

## Final Recommendation

Adopt the configured-classifier path, gated on `reconciliation: simple`. It turns a 50-entity copy-paste task into one template branch, one shared strategy, and one configuration marker per classifier, while fixing the existing `feature_type` details breakage as the first proof. Unmarked entities keep their current contracts, description scoring stays opt-in and off by default, automatic matches come from label similarity only, duplicate labels never auto-accept, and every registration must declare whether it is supported.
