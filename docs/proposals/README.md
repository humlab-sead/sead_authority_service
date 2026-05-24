# Proposal Backlog

## Overview

This folder contains proposal and handoff material for changes that belong in `sead_authority_service`.

Current focus:

- return target-facing SEAD integer IDs from `POST /identity/resolve` so downstream Shape Shifter change-request generation can complete Delivery 1 PK/FK materialization

## Documents

- [SIMS_TARGET_ID_CONTRACT.md](./SIMS_TARGET_ID_CONTRACT.md) — main proposal for the optional `ResolutionOutcome.target_id` contract change
- [SIMS_TARGET_ID_CONTRACT_ISSUE.md](./SIMS_TARGET_ID_CONTRACT_ISSUE.md) — ready-to-file GitHub issue draft for the same change
- [SIMS_TARGET_ID_CONTRACT_PR.md](./SIMS_TARGET_ID_CONTRACT_PR.md) — ready-to-file PR description draft for the same change

## Current Status

- proposal status: drafted
- downstream Shape Shifter support: already prepared for optional `target_id`
- remaining work: implement and validate the authority-service response change