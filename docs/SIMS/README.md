# SIMS — SEAD Identity Management System

Design documentation for the identity management layer integrated into the SEAD Authority Service.

SIMS provides stable identity tracking for SEAD entities: UUID allocation, identity evidence mapping, reconciliation policy, and change detection support.

## Documents

- [REQUIREMENTS.md](./design/REQUIREMENTS.md) — Functional requirements and entity/identity taxonomy
- [DESIGN_VIEW.md](./design/DESIGN_VIEW.md) — System design view: intent, rules, decision flow
- [IMPLEMENTATION_VIEW.md](./design/IMPLEMENTATION_VIEW.md) — Storage design, rollout strategy, SQL structures
- [ASSESSMENT.md](./design/ASSESSMENT.md) — Design readiness assessment and open issues
- [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) — Entity register: aggregate boundaries, associations, reconciliation strategies, business keys

## Reference Material

- [existing_examples/](./archived/existing_examples/) — Existing SEAD identity patterns (BugsCEP, allocation SQL)
- [sead_model/](../../docs/SEAD/) — Current SEAD database schema reference (tables, sequences, constraints)

## Boundary to Shape Shifter

- **Authority Service** owns identity resolution, allocation, mapping, tracing, and policy enforcement.
- **Shape Shifter** owns the target model specification (source of truth for entity metadata, including SIMS properties), the ETL pipeline, reconciliation client UI, and SQL generation.
- Shape Shifter's SEAD ingester treats the Authority Service as an external dependency with a stable API contract.

## Source of Truth

Entity metadata (roles, identity tracking, reconciliation strategies, aggregate boundaries) is defined in Shape Shifter's `sead_standard_model.yml`. The Authority Service consumes these properties at runtime to drive identity policy decisions. The `TRACKED_ENTITIES.md` document is generated from that target model.
