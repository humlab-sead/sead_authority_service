# SIMS Documentation Suite — Implementation Readiness Assessment

## Overall Verdict

**Ready for Phase 1 implementation**, with a short list of gaps to address before or during coding.

---

## 1. Cross-Document Consistency

**Strengths:**
- The 4-document hierarchy is clean: CONCEPTUAL_MODEL (what) → REQUIREMENTS (must) → DESIGN_VIEW (rules) → IMPLEMENTATION_VIEW (how). Each stays in its lane.
- All 8 core concepts are consistently named and defined across documents.
- Binding Set was cleanly threaded through all four documents — the concept-to-structure mapping, lifecycle, FR-26, design rule #3, and DDL are all aligned.
- Every functional requirement (FR-1 through FR-27) is traceable to at least one storage structure or operation.

**Issues found:**

| # | Issue                                                                                                     | Severity       | Location            |
|---|-----------------------------------------------------------------------------------------------------------|----------------|---------------------|
| 1 | ~~README references ASSESSMENT.md — file did not exist at time of review~~                                | ~~Minor~~ Fixed | README.md           |
| 2 | ~~TRACKED_ENTITIES.md §2.3 has duplicate rows — entities #37–43 appear twice in the SEAD-Administered table~~ | ~~Bug~~ Fixed | TRACKED_ENTITIES.md |
| 3 | ~~TRACKED_ENTITIES.md §8 Summary has `-2` for Provider-owned aggregate roots count — should be `2`~~      | ~~Bug~~ Fixed  | TRACKED_ENTITIES.md |
| 4 | ~~TRACKED_ENTITIES.md cross-references ASSESSMENT.md which did not exist at time of review~~              | ~~Minor~~ Fixed | TRACKED_ENTITIES.md |

---

## 2. Requirements Coverage

All 27 FRs map to implementation structures:

| FR Range                           | Coverage in IMPLEMENTATION_VIEW                                                | Status   |
|------------------------------------|--------------------------------------------------------------------------------|----------|
| FR-1–5 (identity model)            | `tracked_identities`, `source_identities` tables, identity type columns        | Complete |
| FR-6–11 (identifier intake)        | UUID intake, BK intake, authority-key intake rules, policy config              | Complete |
| FR-12–14 (idempotency)             | Uniqueness constraint on source_identities, resolve operation                  | Complete |
| FR-15–20 (domain modeling)         | Entity subtypes, reconciliation design decision (Shape Shifter owns), rejection with diagnostics for unmatched shared metadata in Resolve operation | Complete |
| FR-21–23 (submission/traceability) | `submissions` table, `submission_source_identities` junction, audit columns    | Complete |
| FR-24–25 (update foundation)       | Detect Change operation, content hash stored on tracked_identity               | Complete |
| FR-26 (binding sets)               | `binding_sets` table, lifecycle states                                         | Complete |
| FR-27 (CR completeness)            | Design rule #3, Internal Origins section                                       | Complete |

~~**Gap: FR-24 content hash storage.** The Detect Change operation (§ Core Operations #4) references "the stored hash for the Tracked Identity" but the `tracked_identities` table DDL does not include a `content_hash` column.~~ Fixed — `content_hash` column added to `tracked_identities` DDL.

---

## 3. DDL Readiness

The IMPLEMENTATION_VIEW provides column-level detail for 6 tables + 1 junction table.

| Table                          | Columns   | PK/FK             | Uniqueness                                            | Lifecycle States | Ready?                   |
|--------------------------------|-----------|-------------------|-------------------------------------------------------|------------------|--------------------------|
| `source_scopes`                | 5         | PK + self-FK      | —                                                     | —                | Yes                      |
| `submissions`                  | 5+ audit  | PK + FK           | —                                                     | pending/completed/failed                           | Yes                      |
| `source_identities`            | 6+ audit  | PK + FK           | `(scope, entity_type, identity_type, identity_value)` | —                                                  | Yes                      |
| `submission_source_identities` | 3         | Composite PK (2 FK) | `(submission_uuid, source_identity_uuid)`             | —                                                  | Yes                      |
| `tracked_identities`           | 6+ audit  | PK                | —                                                     | allocated/pending/materialized/invalidated         | Yes                      |
| `binding_sets`                 | 5+ audit  | PK + FK(nullable) | —                                                     | proposed/confirmed/rejected/superseded/invalidated | Yes                      |
| `bindings`                     | 6         | PK + 3 FK         | —                                                     | — (governed by set)                                | Yes                      |

**Gaps for DDL generation:**
~~1. `submission_source_identities` junction table needs explicit column definitions~~
~~2. `tracked_identities` needs a `content_hash` column (or a separate `identity_hashes` table) for FR-24~~
~~3. No indexes are specified — will matter for resolution performance but can be added during implementation~~

---

## 4. Operations Readiness

Four core operations are defined with input/output/behavior:

| Operation         | Defined? | Input specified? | Output specified?                   | Idempotency?              | Edge cases?                  |
|-------------------|----------|------------------|-------------------------------------|---------------------------|------------------------------|
| Resolve Identity  | Yes      | Yes              | 2 outcomes (matched/new); shared metadata rejected on failure | FR-12/13 referenced       | Shared metadata → reject |
| Bind              | Yes      | Yes              | Proposed Binding Set                | —                         | Policy enforcement detailed  |
| Associate with CR | Yes      | Yes              | Updates binding_set record          | FR-25 noted               | —                            |
| Detect Change     | Yes      | Yes              | 3 outcomes (insert/update/skip)     | Hash determinism required | —                            |

Sufficient for implementation. The operations are described at the right level — detailed enough to code, not over-specified.

---

## 5. Responsibility Boundaries

Every potential SIMS/Shape-Shifter confusion point has been resolved with explicit design decisions:

| Concern                          | Owner                 | Where Documented                       |
|----------------------------------|-----------------------|----------------------------------------|
| BK serialization                 | Submitting system     | IMPLEMENTATION_VIEW § BK intake        |
| Content hash computation         | Submitting system     | IMPLEMENTATION_VIEW § Detect Change    |
| Reconciliation procedure         | Shape Shifter         | IMPLEMENTATION_VIEW § Resolve Identity |
| Identity policy enforcement      | SIMS (config file)    | IMPLEMENTATION_VIEW § Bind             |
| CR lifecycle                     | Sqitch/Change Control | CM + DV + IMPL                         |
| Internal entity curation tooling | Out of scope          | DV rule #3 + IMPL § Internal Origins   |

---

## 6. Deferred Items

From CONCEPTUAL_MODEL.md § Deferred Issues — 7 items.

| # | Deferred Issue                                     | Blocks Phase 1?                                                                                |
|---|----------------------------------------------------|------------------------------------------------------------------------------------------------|
| 1 | Source Identity Observation (per-submission state) | No — junction table handles M:N                                                                |
| 2 | ~~Unresolved case handling~~                       | **No** — Removed. Unmatched shared metadata entities are rejected with diagnostics;            |
| 3 | Merge and split semantics                          | No — future concern                                                                            |
| 4 | Binding evidence model                             | No — `provenance` JSONB is sufficient for now                                                  |
| 5 | CR integration details                             | No — association is by name, deliberately loose                                                |
| 6 | Materialized SEAD entity modeling                  | No — `sead_internal_id` on tracked_identities is sufficient                                    |
| 7 | Detailed binding review policy                     | No — auto-confirm for provider-owned, review for shared metadata                               |

Only #2 is worth addressing before coding. Where do unresolved cases get recorded? The Resolve operation returns "unresolved" but there's no table or queue for these. A lightweight `unresolved_cases` table or a status on the Binding Set could handle this.

**Update:** Deferred issue #2 is now resolved. The `unresolved` intermediate state has been removed from the design. Unmatched shared metadata entities cause submission rejection with diagnostic information. No separate storage structure is needed.

---

## 7. TRACKED_ENTITIES.md Quality

This is the weakest document in the suite:
- **Duplicate rows** in §2.3 (entities 37–43 listed twice)
- **Summary count error** (`-2` instead of `2`)
- **References deprecated ASSESSMENT.md** (now restored)
- **Open question #4** (classifier extensibility) is correctly deferred to Phase 3
- The reconciliation strategy table in §5 is excellent and directly actionable

---

## 8. What's Missing for Implementation

| Gap                                         | Priority                  | Recommendation                                       |
|---------------------------------------------|---------------------------|------------------------------------------------------|
| ~~Content hash column on `tracked_identities`~~ | ~~Must fix~~ Fixed    | ~~Add `content_hash TEXT NULL` column to DDL~~       |
| ~~`submission_source_identities` junction DDL~~ | ~~Must fix~~ Fixed    | ~~Add explicit column definitions~~                  |
| ~~Unresolved case storage~~                 | **Resolved**              | Removed — unmatched entities are rejected, no intermediate state |
| API endpoint contracts                      | **Phase 1 task**          | Not a doc gap — stated as deferred in REQUIREMENTS   |
| Index strategy                              | **During implementation** | Can be specified in DDL scripts                      |
| TRACKED_ENTITIES.md data errors             | **Should fix**            | Duplicate rows, summary count                        |

---

## 9. Recommendation

The documentation is **implementation-ready for Phase 1** (infrastructure + pilot per the Rollout plan). The conceptual model, requirements, design rules, and storage design are internally consistent and sufficiently detailed to write DDL + service code.

**Before starting code, fix these 3 items:**
1. **Resolved** Add `content_hash` column to `tracked_identities` table specification
2. **Resolved** Add `submission_source_identities` junction table DDL
3. **Resolved** Fix TRACKED_ENTITIES.md data errors (duplicate rows, summary count)
