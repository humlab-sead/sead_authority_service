# SIMS — SEAD Identity Management System

Design and reference documentation for the identity management layer integrated into the SEAD Authority Service.

SIMS provides stable identity tracking for SEAD entities: UUID allocation, identity evidence mapping, reconciliation policy, and change detection support.

## Current Status

- **Phases 1–2 (Infrastructure + Pilot): complete and live** (since 2026-04-06)
- **Phases 3–5 (Shared metadata, Entity table integration, CR integration): outlined, not implemented**
- Implementation: `src/identity/` · Deployment: [OPERATIONS.md](./OPERATIONS.md)

## Documentation Map

### System reference (long-term, frozen)

| Document | Contents |
|---|---|
| [REQUIREMENTS.md](./REQUIREMENTS.md) | Functional requirements (FR-1..27) and entity/identity taxonomy |
| [CONCEPTUAL_MODEL.md](./CONCEPTUAL_MODEL.md) | Domain concepts, relations, lifecycles |
| [DESIGN_VIEW.md](./DESIGN_VIEW.md) | System design: intent, rules, decision flow |
| [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md) | Storage design, rollout strategy, SQL structures |
| [SEQUENCE_DIAGRAMS.md](./SEQUENCE_DIAGRAMS.md) | Visual reference of core workflows |
| [OPERATIONS.md](./OPERATIONS.md) | Deployment, configuration, troubleshooting |
| [TRACKED_ENTITIES.md](./TRACKED_ENTITIES.md) | Entity register (generated from Shape Shifter) |

### Working docs (active)

- [proposals/](./proposals/) — Phase 3+ planning and design change proposals (empty for now)

### Archived (historical)

- [IMPLEMENTATION_PLAN.md](./archived/IMPLEMENTATION_PLAN.md) — Phase 1–5 work breakdown (Phases 1–2 done)
- [ASSESSMENT.md](./archived/ASSESSMENT.md) — pre-implementation readiness assessment
- [POST_IMPL_DOCS_CHECKLIST.md](./archived/POST_IMPL_DOCS_CHECKLIST.md) — post-implementation documentation checklist
- [existing_examples/](./archived/existing_examples/) — Existing SEAD identity patterns (BugsCEP, allocation SQL)

## Reference Material

- [sead_model/](../../docs/SEAD/) — Current SEAD database schema reference (tables, sequences, constraints)

## Boundary to Shape Shifter

- **Authority Service** owns identity resolution, allocation, mapping, tracing, and policy enforcement.
- **Shape Shifter** owns the target model specification (source of truth for entity metadata, including SIMS properties), the ETL pipeline, reconciliation client UI, and SQL generation.
- Shape Shifter's SEAD ingester treats the Authority Service as an external dependency with a stable API contract.

## Source of Truth

Entity metadata (roles, identity tracking, reconciliation strategies, aggregate boundaries) is defined in Shape Shifter's `sead_superset_model.yml`. The Authority Service consumes these properties at runtime to drive identity policy decisions. The `TRACKED_ENTITIES.md` document is generated from that target model.
