**Revision required before phase planning.** Extending the configured strategy is a good fit, and avoiding per-entity classes keeps the design manageable. However, the proposal contains conflicting contracts and two concrete compatibility problems.

I reviewed the supplied draft against Authority Service `dev` at `bc0a051` and the target model. This was a static review; I did not verify the live database schema.

1. **High — Duplicate suppression does not provide the claimed safety guarantee.**  
   **Location:** Summary, §3, inherited guarantees.  
   The SQL applies `LIMIT` before Python checks for duplicate labels. With two identical labels and `limit: 1`, only one reaches duplicate detection and can receive `match: true`. Therefore, “deferring it never produces a wrong automatic match” is unsupported by the implementation. See [candidate conversion](https://github.com/humlab-sead/sead_authority_service/blob/bc0a0513116ebfd569ba836212834dfa3c174b2c/src/strategies/configured_classifier.py#L48) and [SQL template](https://github.com/humlab-sead/sead_authority_service/blob/bc0a0513116ebfd569ba836212834dfa3c174b2c/schema/templates/entity.sql.jinja2#L204).  
   **Recommendation:** Require ambiguity detection across all eligible rows before limiting results. Also state explicitly that context filtering occurs before ranking and limiting; otherwise, the correct parent’s candidate can be excluded prematurely. Add a `limit: 1` acceptance case.  
   **Confidence: High.**

2. **High — Generated alternate-identity SQL breaks the candidate ID contract.**  
   **Location:** §6; `P2-AC-6`.  
   The proposed query returns `<id_column> as id`. Candidate conversion reads the configured field, such as `method_id`, so the proposed replacement would fail when converting an alternate-ID result. The existing [method query](https://github.com/humlab-sead/sead_authority_service/blob/bc0a0513116ebfd569ba836212834dfa3c174b2c/src/resources/method.yml) preserves `method_id`.  
   **Recommendation:** Return the configured ID column without renaming it. Preserve public property identifiers such as `method_abbreviation`, which differ from database column names. Validate through the reconciliation endpoint, including candidate conversion.  
   **Confidence: High.**

3. **High — The derived-label example cannot satisfy its own validation and indexing rules.**  
   **Location:** §4 and §8; `P2-AC-4`, `P2-AC-9`.  
   `coordinate_method_dimension` is marked `scoped` without `scope_columns`, which §8 requires. Separately, its label references joined tables, while the current template creates a trigram index on the base table. Substituting that expression into the existing index cannot work. See the [index template](https://github.com/humlab-sead/sead_authority_service/blob/bc0a0513116ebfd569ba836212834dfa3c174b2c/schema/templates/entity.sql.jinja2#L70).  
   **Recommendation:** Choose a valid marker and explicitly decide how joined labels are searched and indexed. For this small classifier, an ordinary view without a label index may be sufficient; otherwise, define materialization and refresh behavior.  
   **Confidence: High.**

4. **Medium — `scoped` and `lookup` represent overlapping concepts as mutually exclusive markers.**  
   **Location:** §1, §5, Planning Handoff; `P2-AC-1–2`.  
   Scope and the criteria register four lookups as `scoped`, but §5 registers all thirteen as `lookup`. This affects behavior: `scoped` permits description scoring, whereas lookups must reject it. `dimension` is also described as scoped while explicitly needing no scope columns.  
   **Recommendation:** Define one unambiguous rule. The smallest adjustment is to let `lookup` entries declare optional `scope_columns`, retaining their description-scoring prohibition. Update the criteria accordingly.  
   **Confidence: High.**

5. **Medium — Some proposed scopes omit parts of the stated business key.**  
   **Location:** §2 and §5.  
   The target model defines `rdb_system` by location, system name, **and version**; the proposed context includes only location. Likewise, `taxa_synonyms` has a composite unique set containing taxon, **bibliographic reference**, and synonym. Parent-label context therefore cannot reliably distinguish all intended records. See the [target model](https://github.com/humlab-sead/sead_shape_shifter/blob/dev/resources/target_models/sead_standard_model.yml).  
   **Recommendation:** Either include these distinguishing fields or explicitly retain such cases as ambiguous suggestions. Do not describe parent labels alone as sufficient to establish uniqueness.  
   **Confidence: High.**

6. **Medium — Context is added to SQL results without a defined client-visible contract.**  
   **Location:** §2–3; `P2-AC-3`.  
   The current candidate converter discards context fields. Returning them from SQL therefore does not make identical labels distinguishable in candidate lists. Similarly, `match: false` alone does not explain that the supplied context failed and fallback results are being shown.  
   **Recommendation:** Specify how candidate responses and previews present context, and how callers recognize context fallback. Add HTTP acceptance criteria for both visible outcomes.  
   **Confidence: High.**

7. **Medium — The SQL preservation criterion conflicts with promoting fourteen existing entities.**  
   **Location:** `P2-AC-8`, Testing and Validation, Planning Handoff.  
   Requiring unchanged generated SQL for **every existing `simple` entity** conflicts with changing fourteen of those entities to scoped views and functions. Requiring all regression tests to remain unmodified can also preserve assertions that those registrations are still `simple`.  
   **Recommendation:** Limit byte-identical SQL preservation to entities that **remain `simple`**. For promoted entities, require unchanged behavior when context is absent, with explicit allowances for the new SQL shape and property metadata.  
   **Confidence: High.**

**Planning readiness: Revision required.** Resolve candidate selection and ambiguity, marker semantics, derived-label generation, and response behavior first. Those are design decisions that would otherwise be left to implementation. The live `dimension` column check can remain an explicit implementation gate.