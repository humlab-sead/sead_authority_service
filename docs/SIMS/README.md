# SIMS — SEAD Identity Management System

Design and reference documentation for the identity management layer integrated into the SEAD Authority Service.

SIMS owns tracked aggregate identities and their source-identity associations. It mints configured, entity-scoped identity values and guarantees uniqueness within its own identity store.

## Current Status

- **Phases 1–2 (Infrastructure + Pilot): complete and live** (since 2026-04-06)
- **Phases 3–5 (Shared metadata, Entity table integration, CR integration): outlined, not implemented**
- Implementation: `src/identity/` · Deployment: [OPERATIONS.md](./OPERATIONS.md)

## Documentation Map

### System reference

| Document | Contents |
|---|---|
| [REQUIREMENTS.md](./REQUIREMENTS.md) | Functional requirements (FR-1..27) and entity/identity taxonomy |
| [CONCEPTUAL_MODEL.md](./CONCEPTUAL_MODEL.md) | Domain concepts, design rules, decision flow |
| [DESIGN.md](./DESIGN.md) | Storage design, rollout strategy, SQL structures |
| [DIAGRAMS.md](./DIAGRAMS.md) | Visual reference of core workflows and state machines |
| [OPERATIONS.md](./OPERATIONS.md) | Deployment, configuration, troubleshooting |
| [SHAPE_SHIFTER_TARGET_MODEL_ENTITY_REPORT.md](./SHAPE_SHIFTER_TARGET_MODEL_ENTITY_REPORT.md) | Generated, read-only Shape Shifter target-model reference; not the SIMS capability registry |

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

- **Authority Service (SIMS)** owns tracked aggregate identities, source-identity associations, generic configured allocation, and uniqueness within the SIMS identity store. SIMS does not map identity values to SEAD tables or columns or enforce SEAD database integrity.
- **Shape Shifter** owns its target model, reconciliation and approval, and translation of SIMS-issued values into artifacts for that model. Its model does not define SIMS capabilities.
- Shape Shifter's SEAD ingester treats the Authority Service as an external dependency with a stable API contract.

## Source of Truth

SIMS capabilities and allocation behavior come from validated SIMS configuration. Shape Shifter's `sead_standard_model.yml` describes the consumer's target model and intended artifact behavior; SIMS does not consume it to discover SEAD tables, columns, primary keys, or relationships. [SHAPE_SHIFTER_TARGET_MODEL_ENTITY_REPORT.md](./SHAPE_SHIFTER_TARGET_MODEL_ENTITY_REPORT.md) is generated from that model for read-only reference. In particular, `site_location` is an untracked bridge in Shape Shifter, not a SIMS Tracked Identity.
