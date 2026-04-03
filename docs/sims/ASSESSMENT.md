# SEAD Identity System Assessment

## Scope

This assessment evaluates the implementation-readiness of the SEAD Identity System based on the current state of:

- [REQUIREMENTS.md](./REQUIREMENTS.md) — functional requirements (25 FRs, 4 scenarios)
- [DESIGN_VIEW.md](./DESIGN_VIEW.md) — design rules and architectural decisions
- [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md) — storage design, core operations, rollout strategy

It replaces the earlier assessment. The documents have been substantially revised since that assessment was written.

---

## Overall Assessment

The proposal has moved from a loose collection of ideas to a **coherent three-layer specification**: requirements define what the system must do, the systems design constrains how, and the implementation view specifies concrete structures.

The document chain is internally consistent and largely free of redundancy. Identity terminology is now precise (five identity types, three entity subtypes, three relationship types). The design rules are crisp. The Resolve → Allocate → Map decision flow is well defined. The implementation view provides concrete DDL, operation interfaces, and a phased rollout.

**However, the proposal is not yet implementation-ready.** Several structural design questions remain unresolved, and until they are answered, the implementation structures in the third document cannot be validated against the real SEAD schema.

The remaining gaps cluster into two categories:

1. **Domain modeling gaps** — which SEAD objects are tracked entities, what their aggregate boundaries are, and how reconciliation works in practice.
2. **Identity model gaps** — where the SEAD universal identity (UUID) actually lives, and how it relates to the external_id stored in the allocation registry.

---

## What Is Now Strong

### 1. Clean document chain with no redundancy

Each document has a clear role. Requirements does not leak implementation. Systems design does not restate requirements. Implementation view does not restate design rules. Cross-references are correct.

### 2. Precise identity vocabulary

The five identity types (SEAD internal, SEAD universal, business key, provider key, authority key) are now defined with clear characteristics. The earlier assessment flagged blurred terminology as the most important unresolved issue. That is largely fixed.

### 3. Entity subtypes grounded in DDD

The provider-owned / shared-metadata / relationship distinction is new and directly addresses the earlier gap around classifiers and shared metadata. The mapping to Shape Shifter terminology (fact, classifier/lookup, bridge) creates a useful bridge between the two systems.

### 4. Administrable identity policy

FR-11 now explicitly requires an administrable policy governing when a provider UUID is accepted as the SEAD universal identity. The earlier assessment identified this as the critical missing governance rule. It is now a stated requirement with design support (policy boundary between Resolve and Allocate).

### 5. Unresolved reconciliation state

FR-20 now requires the system to surface unresolved state rather than silently allocating a new identity for shared metadata. This directly addresses the earlier concern about classifier duplication.

### 6. Many-to-many relationship support

FR-18 and the association relationship type address the site/location modeling problem. The design no longer forces all relationships into parent-child ownership hierarchies.

### 7. The implementation view is concrete

DDL exists for the allocation registry and submission tracker. Core operations are specified as interfaces with clear behavior contracts. The submission lifecycle is an explicit state machine. The API surface is defined as a table of endpoints. The rollout is phased.

---

## Remaining Gaps

### Gap 1: The SEAD universal identity has no clear home

This is the most significant structural issue remaining.

The requirements define two distinct identity types for every tracked entity:

- **SEAD internal identity** — the integer PK (`{entity}_id`)
- **SEAD universal identity** — a stable UUID (`{entity}_uuid`)

The implementation view's central table (`identity_allocations`) maps `external_id` → `alloc_integer_id`. The entity table extensions add `{entity}_external_id` columns. But `external_id` is the *provider's* identifier, not the SEAD universal identity.

This leaves an unresolved question: **where does the SEAD-minted UUID live?**

Consider the case where a provider supplies only a business key and identity policy does not accept it as the SEAD universal identity. Per FR-7, the system mints a new SEAD UUID. That UUID needs to be stored somewhere — but the current implementation has no column for it. The `external_id` field holds the business key. The `alloc_integer_id` holds the integer PK. The SEAD UUID itself has no column in the allocation table and no column in the entity table extension pattern.

Additionally, some SEAD tables already have `{entity}_uuid` columns (e.g. `tbl_sites.site_uuid`, `tbl_sample_groups.sample_group_uuid`). The earlier assessment flagged the risk of parallel identity columns (`{entity}_uuid` alongside `{entity}_external_id`). That risk remains.

**To resolve:** decide whether `{entity}_external_id` is renamed to `{entity}_uuid`, whether the allocation table gains a `sead_uuid` column alongside `external_id`, or whether existing `{entity}_uuid` columns serve as the canonical SEAD universal identity. This must be settled before the DDL is final.

### Gap 2: Tracked entity enumeration is still deferred

The requirements correctly state that determining which SEAD objects qualify as tracked entities is a domain-modeling task. The implementation view picks five pilot tables for Phase 2, but that is rollout planning, not a design decision.

Until the tracked entity list exists, no one can:

- verify that the aggregate boundaries make sense,
- define business-key rules per entity type,
- write the entity table extension migrations,
- test reconciliation for shared metadata entities.

This is the single largest prerequisite blocking implementation.

### Gap 3: Aggregate boundaries are undefined

The design rules say value objects are aggregate state, not identity targets (Design Rule 1). The requirements define the entity/value-object distinction. But no document says which SEAD tables are aggregate roots and which are owned children.

Without this:

- update semantics ("replace children") cannot be implemented,
- content hashing cannot define its scope,
- the system cannot distinguish an entity that needs identity from a child row that does not.

### Gap 4: Reconciliation mechanics are unspecified

FR-17 requires reconciliation of shared metadata. FR-20 requires surfacing unresolved state. But the implementation view contains no reconciliation operation.

The core operations are: allocate, resolve, commit, rollback, detect-change. None of these describes how reconciliation actually works:

- What matching rules apply? (exact match, fuzzy, configurable per entity type?)
- Who resolves unresolved state? (automated retry, manual curation queue, API callback?)
- Where is unresolved state stored? (a status on the allocation record, a separate table?)

For provider-owned entities, the allocate-or-resolve flow is sufficient. For shared metadata entities, it is not. Reconciliation is a different operation that needs its own specification.

### Gap 5: Business-key serialization rules are undefined

The implementation view acknowledges this (Open Question 1) and provides a placeholder format (`"LAB_123|SITE_A|2024"`). But for business-key resolution to work, serialization rules must be defined per entity type: which fields, what order, what delimiter, what normalization (case, whitespace, encoding).

Without these rules, two submissions of the same entity with the same business key could produce different serialized representations, defeating idempotency.

### Gap 6: Content-hash aggregate scope is undefined

The implementation view acknowledges this (Open Question 3). The detect-change operation compares hashes, but there is no specification of what gets hashed.

The earlier assessment identified the required decisions: which child rows, which fields, normalization rules, ordering, and whether associations count. Those decisions still need to be made against actual SEAD aggregate definitions — which depend on Gap 3.

### Gap 7: Identity policy model is unspecified

FR-11 requires administrable identity policy. The systems design says policy is applied at the boundary between Resolve and Allocate and may vary by entity type. But no document specifies how policy is represented, stored, or administered.

Is it a configuration file? A database table? An API-managed resource? What are the policy parameters? This does not need to be over-engineered, but it needs at least a candidate structure.

### Gap 8: Entity metadata storage is undecided

SIMS needs to know which SEAD tables are tracked entities, their subtypes, aggregate boundaries, and FK relationships. This metadata is required for topological sorting, submission validation, allocation ordering, and reconciliation rules.

Shape Shifter's target model (`sead_standard_model.yml`) already catalogues 47 SEAD entities with role, foreign keys, identity columns, column specs, and unique sets. That metadata overlaps substantially with what SIMS needs.

The design question is: **should SIMS maintain its own entity registry, or consume Shape Shifter's target model spec?**

An earlier design produced a three-table aggregate model (entity_types, aggregate_definitions, entity_dependencies) with views and PL/pgSQL functions. That design was retired as premature and largely redundant with the target model. The associated SQL was removed from this repository (it referenced retired aggregate model tables and was not applicable to the new design).

This decision affects Gaps 2 (tracked entity enumeration), 3 (aggregate boundaries), and 5 (business-key rules). It should be resolved early.

See [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md) § Entity Metadata for the candidate options.

---

## What Has Improved Since The Earlier Assessment

| Earlier finding | Current status |
|-----------------|----------------|
| Identity terminology is blurred | Fixed. Five identity types clearly defined. |
| No entity subtypes for shared metadata | Fixed. Provider-owned / shared metadata / relationship subtypes defined. |
| No requirement for administrable identity policy | Fixed. FR-11 added. |
| No requirement for surfacing unresolved state | Fixed. FR-20 added. |
| Location/site forced into ownership hierarchy | Fixed. Association relationship type introduced, FR-18 supports many-to-many. |
| Documents redundant and inconsistent | Fixed. Three-document chain is clean, DRY, and properly cross-referenced. |
| Implementation detail mixed with design | Fixed. Clear separation across three documents. |
| Aggregate model metadata tables premature | Fixed. Retired; associated SQL removed (referenced retired tables). Design question recorded as Gap 8. |
| NFRs more mature than domain model | Fixed. NFR material stashed. Implementation view is proportionate to design maturity. |

---

## What Remains From The Earlier Assessment

| Earlier finding | Current status |
|-----------------|----------------|
| Tracked entity list not defined | Still deferred (Gap 2). |
| Aggregate boundaries not grounded in DDL | Still undefined (Gap 3). |
| Existing UUID columns risk parallel identity mechanisms | Still unresolved (Gap 1). |
| Content-hash serialization unspecified | Still open (Gap 6). |
| Rollback vs identity permanence unclear | Partially addressed. Implementation view defines soft/hard delete. But the design-level permanence rule is still unstated. |

---

## Implementation-Readiness Verdict

The proposal is now at a **late design** stage. The conceptual model is sound and internally consistent. The implementation structures are concrete and plausible. But the design depends on domain-modeling inputs that do not yet exist.

**Ready for implementation:**

- The allocation registry schema and operations (modulo Gap 1).
- The submission lifecycle and API surface.
- Phase 1 infrastructure deployment (schema, functions, API shell).
- The rollout phasing strategy.

**Not ready for implementation:**

- Entity table extensions (depends on tracked entity list and UUID column strategy).
- Business-key resolution (depends on serialization rules per entity type).
- Reconciliation for shared metadata (not yet specified).
- Content-hash change detection (depends on aggregate boundary definitions).
- Identity policy administration (no candidate structure).

**Recommended path to implementation-readiness:**

1. Enumerate tracked entities against the real SEAD DDL.
2. Define aggregate boundaries (which tables are roots, which are owned children, which are associations).
3. Resolve the UUID column question: reuse existing `{entity}_uuid`, rename `{entity}_external_id`, or add `sead_uuid` to the allocation table.
4. Specify reconciliation mechanics for shared metadata entities.
5. Define business-key rules for at least the five pilot entity types.
6. State the identity permanence rule (are issued identities ever reusable?).

Steps 1–3 are prerequisites for any entity-table work. Steps 4–6 can proceed in parallel with Phase 1 infrastructure.

---

## Readiness Checklist

Each item must be completed and recorded in the appropriate document before the system can be considered implementation-ready. Items are grouped by dependency: complete each group before starting the next.

### Group A: Domain Modeling (prerequisites for everything else)

- [x] **A1. Enumerate tracked entities.** Produce a table listing every SEAD table that qualifies as a tracked entity (aggregate root). For each, state: table name, entity subtype (provider-owned, shared metadata, or relationship), and rationale for inclusion. **Recorded in [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) §2.**
- [x] **A2. Define aggregate boundaries.** For each tracked entity, list the child tables whose rows are owned value objects (replaced on update, no independent identity). State which child tables are excluded and why. **Recorded in [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) §3.**
- [x] **A3. Identify associations.** For each tracked entity, list relationships that are associations (many-to-many or cross-aggregate references) rather than ownership. Include the join table and both referenced entities. The site/location relationship via `tbl_site_locations` is the canonical example. **Recorded in [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) §4.**
- [x] **A4. Classify shared metadata entities.** For each shared-metadata entity (locations, bibliographies, taxa, methods, sample types, etc.), state whether it is reconciled against existing SEAD records, allocated fresh per submission, or handled by a different rule. **Recorded in [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) §5.**

### Group B: Identity Model (depends on A1)

- [ ] **B1. Resolve the UUID column question.** Decide one of: (a) reuse existing `{entity}_uuid` columns as the canonical SEAD universal identity, (b) rename the proposed `{entity}_external_id` to `{entity}_uuid`, or (c) add a `sead_uuid` column to the allocation table. Document the decision and update IMPLEMENTATION_VIEW.md DDL accordingly.
- [ ] **B2. Reconcile with existing UUID columns.** For tables that already have `{entity}_uuid` columns (`tbl_sites.site_uuid`, `tbl_sample_groups.sample_group_uuid`, etc.), state how existing values are treated: migrated into the allocation registry, kept as-is, or deprecated. Document the migration strategy.
- [ ] **B3. State the identity permanence rule.** Define whether a once-issued SEAD identity (integer PK + UUID) can ever be reused, invalidated, or hard-deleted. State the rule for each of: normal rollback, administrative correction, and entity merge. Record in REQUIREMENTS.md or DESIGN_VIEW.md.

### Group C: Business-Key Resolution (depends on A1, A4)

- [x] **C1. Define business-key fields per entity type.** For each tracked entity, list the fields that constitute its business key. State the field names, their order, and whether each field is required or optional. **Recorded in [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) §2 (business key column).**
- [ ] **C2. Define serialization rules.** Specify the canonical serialization format for business keys: delimiter, encoding, case normalization, whitespace handling, null representation. The format must be deterministic so that identical business data always produces the same serialized key.
- [ ] **C3. Define collision handling.** State what happens when two different submissions produce the same serialized business key for what appears to be different data. Options include: reject the second submission, flag for manual review, or treat as an update.

### Group D: Reconciliation (depends on A4, C1)

- [ ] **D1. Specify reconciliation operations.** Define the reconciliation flow for shared metadata entities as a named operation (distinct from allocate/resolve). State the inputs (entity type, candidate data, matching criteria), outputs (matched SEAD record or unresolved state), and side effects (allocation record creation).
- [ ] **D2. Define matching rules per entity type.** For each shared-metadata entity, state the matching rule: exact match on business key, fuzzy match with threshold, configurable match, or manual curation. If fuzzy, define the similarity metric and threshold.
- [ ] **D3. Specify unresolved-state handling.** Define where unresolved reconciliation state is stored (allocation record status, separate table, or both), who is responsible for resolving it (automated retry, manual curation queue, API callback to provider), and what the submission's status is while the state is unresolved.

### Group E: Change Detection (depends on A2, A3)

- [ ] **E1. Define aggregate payload scope.** For each tracked entity, state exactly which fields and child rows are included in the content hash. State whether association records (e.g., site-location links) are included.
- [ ] **E2. Define hash serialization rules.** Specify canonicalization: field ordering, child-row ordering, null handling, numeric precision, text encoding. The serialization must be deterministic across platforms.
- [ ] **E3. Define change-detection response.** State what the system does when a hash mismatch is detected: flag for review, auto-update, or require explicit update request. State whether partial changes (some children changed, root unchanged) are supported.

### Group F: Identity Policy (can proceed in parallel with B–E)

- [ ] **F1. Define policy representation.** State how identity policy is stored and administered: configuration file, database table, or API-managed resource. Provide a candidate schema or structure with at least the fields needed to express "accept provider UUID as SEAD identity for entity type X."
- [ ] **F2. Define policy parameters.** List the parameters that policy controls, at minimum: UUID acceptance (accept/mint/reject), business-key acceptance, per-entity-type overrides. State default values.
- [ ] **F3. Define policy administration.** State who can modify policy (roles/permissions), how changes take effect (immediate, next submission, versioned), and whether policy changes are audited.

### Group G: DDL and Migration Finalization (depends on A–F)

- [ ] **G1. Finalize allocation registry DDL.** Update `identity_allocations` table definition in IMPLEMENTATION_VIEW.md to reflect B1 (UUID column decision) and any changes from D1 (reconciliation status).
- [ ] **G2. Finalize entity table extensions.** For each pilot entity, produce the `ALTER TABLE` migration adding the required columns. Confirm column names and types against B1 and B2.
- [ ] **G3. Write Sqitch migration plan.** Produce the ordered list of Sqitch change sets for Phase 1 (infrastructure) and Phase 2 (pilot entities). Each change set should reference the design decision it implements.
- [ ] **G4. Validate against real SEAD DDL.** Run the proposed migrations against a copy of the production schema. Confirm no conflicts with existing columns, constraints, or triggers.

---

## Relationship To Other Documents

- [REQUIREMENTS.md](./REQUIREMENTS.md) — what the system must do.
- [DESIGN_VIEW.md](./DESIGN_VIEW.md) — design rules and architectural decisions.
- [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md) — implementation structures, storage design, and rollout strategy.
