# Proposal Backlog

## Overview

This folder contains proposal and handoff material for changes that belong in `sead_authority_service`.

Approved identity-ownership decision; generic identity allocation and the approved-miss-to-artifact integration are implemented:

- SIMS owns tracked aggregate identities and is the sole minter of entity-scoped identity values. It uses generic allocation driven by validated configuration and guarantees uniqueness only within its own identity store. SEAD consumes SIMS-issued values under the trust contract; cutover and adoption of existing data are separate operational work.

## Documents

- [SIMS_TARGET_ID_CONTRACT.md](./SIMS_TARGET_ID_CONTRACT/SIMS_TARGET_ID_CONTRACT.md) — Authority Service contract for the generic SIMS identity value response
- [Completed cross-system identity allocation phase plan](https://github.com/humlab-sead/sead_shape_shifter/blob/main/docs/proposals/CHANGE_REQUEST_INGESTER/done/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md) — implementation and validation record for Phases 1–3
- [SIMS_TARGET_ID_CONTRACT_ISSUE.md](./SIMS_TARGET_ID_CONTRACT/SIMS_TARGET_ID_CONTRACT_ISSUE.md) — issue draft aligned with the generic SIMS identity contract; verify API details before filing
- [SIMS_TARGET_ID_CONTRACT_PR.md](./SIMS_TARGET_ID_CONTRACT/SIMS_TARGET_ID_CONTRACT_PR.md) — PR draft aligned with the generic SIMS identity contract; update implementation and test evidence before use

## Current Status

- identity ownership decision: approved 2026-10-01
- site allocation and `target_id` response path: prototype verified against a disposable database; not the generic target design
- downstream Shape Shifter support: already prepared for optional `target_id`
- generic configuration-driven allocation, SIMS-store uniqueness, and approved-miss-to-artifact integration: implemented and validated in Phases 1–3
- separate operational work: existing-data migration, production validation, deployment, and cutover