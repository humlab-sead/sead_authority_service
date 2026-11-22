The core direction is sound from a **KISS perspective**: one generated contract, one record-selection path, and configuration-driven registration should reduce maintenance. Nullable descriptions are a useful simplification.

The proposal adds avoidable complexity around validation, registration, and compatibility, however. I checked the relevant code on `dev` at `3cd1e6d`; deployed database behaviour remains unverified.

1. **High — Proposed Design §1 / P-AC-2: the uniform result drops `label_sim`.**  
   `fuzzy_rdb_code` currently returns both `label_sim` and the description-boosted `name_sim`. The [candidate conversion](https://github.com/humlab-sead/sead_authority_service/blob/3cd1e6d0b146031d3cced1fd490d4ed9da19a266/src/strategies/configured_classifier.py#L114) uses `label_sim` to decide `match`, falling back to `name_sim` when absent. Removing it could therefore turn a description-assisted candidate into an automatic match, contradicting the non-goal of preserving match behaviour.

   **Recommendation:** retain the separate label score. If uniform results are important, expose `label_sim` consistently alongside `name_sim`, preserving existing scoring semantics. **Confidence: High.**

2. **High — Risks / Testing / P-AC-4 and P-AC-10: deployment is understated.**  
   The current [Makefile](https://github.com/humlab-sead/sead_authority_service/blob/3cd1e6d0b146031d3cced1fd490d4ed9da19a266/Makefile#L19) makes `generate-schema` skip existing files; regeneration requires `generate-schema-force`. Neither command deploys SQL.

   The migration also changes function return types. PostgreSQL requires dropping and recreating those functions; nullable additions alone do not establish backward compatibility. [postgresql.org](https://www.postgresql.org/docs/16/sql-createfunction.html?utm_source=chatgpt.com) The existing SQL already uses cascading drops, and the deployment script drops the entire `authority` schema.

   **Recommendation:** explicitly require forced regeneration and database deployment. Replace the blanket compatibility claim with an upgrade test that applies the SQL to an existing disposable database and exercises the previous application version. **Confidence: High; deployment compatibility unverified.**

3. **High — Proposed Design §5 / P-AC-7: country conversion changes more than membership.**  
   The [current location function](https://github.com/humlab-sead/sead_authority_service/blob/3cd1e6d0b146031d3cced1fd490d4ed9da19a266/schema/generated/location.sql#L59) uses the trigram `%` operator; simple classifiers use an explicit label threshold. Country also moves from the base candidate converter to one with accent normalization and duplicate-label match suppression. Equal row counts cannot demonstrate equivalent search responses.

   **Recommendation:** decide explicitly whether country adopts simple-classifier search semantics. That is the cleaner KISS choice, but it needs an acknowledged behaviour change and comparison tests for fuzzy queries, accents, and duplicate labels. Avoid reintroducing country-specific branches merely to satisfy an overly broad parity promise. **Confidence: High.**

4. **Medium — Proposed Design §3: validation depends on an unrelated capability switch.**  
   A malformed simple classifier only warns when record selection is disabled, yet §6 still registers it for reconciliation. This creates two meanings of “valid classifier” and postpones failures until requests arrive. It also conflicts with P-AC-8’s unconditional validation requirement.

   Separately, configuration checks cannot prove that deployed views and functions have been updated; the [current startup validator](https://github.com/humlab-sead/sead_authority_service/blob/3cd1e6d0b146031d3cced1fd490d4ed9da19a266/src/record_selection.py#L158) does not inspect database objects.

   **Recommendation:** validate simple-classifier configuration consistently, independently of record-selection switches. If outdated schemas must fail startup, specify a small read-only database check; otherwise describe schema compatibility as a deployment prerequisite. **Confidence: High.**

5. **Medium — Proposed Design §6: registration introduces unnecessary transitional machinery.**  
   Making `validate_classifier_configuration()` mutate the registry obscures its responsibility. Keeping `CLASSIFIER_KEYS` as a fallback also retains the second classifier definition that this proposal aims to eliminate. Two internal test imports do not establish a compatibility requirement.

   **Recommendation:** use one explicit initialization entry point that validates configuration and then registers classifiers. Share it between application startup, scripts, and tests. Remove the static list unless an actual external consumer requires it. **Confidence: High for the complexity finding; external consumers unverified.**

6. **Low — P-AC-3: prohibit hardcoded dispatch, rather than individual names.**  
   “No module names an individual simple classifier key” would also prohibit useful regression tests and legitimate entity-specific assertions.

   **Recommendation:** require that adding a valid simple classifier needs no changes to runtime dispatch, registration lists, or projection maps. Keep the proposed third-entity test as the observable proof. **Confidence: High.**

**Planning readiness: Revision required.** Keep the shared SQL and record-selection design, simplify initialization and validation, and resolve scoring, country behaviour, and deployment compatibility before phase planning.