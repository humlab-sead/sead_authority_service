# SIMS Post-Implementation Documentation Checklist

## Goal
Replace planning/design artifacts with lean, maintainable operational docs.
Complete after Phase 1 is deployed to staging.

---

## Step 1 — Freeze Design Docs

- [x] Add a `> **Status: Frozen (2026-04-06)**` notice to the top of each design doc:
  - `docs/SIMS/design/REQUIREMENTS.md`
  - `docs/SIMS/design/CONCEPTUAL_MODEL.md`
  - `docs/SIMS/design/DESIGN_VIEW.md`
  - `docs/SIMS/design/IMPLEMENTATION_VIEW.md`
  - `docs/SIMS/design/SEQUENCE_DIAGRAMS.md`
  - `docs/SIMS/design/ASSESSMENT.md`
- [x] Move `docs/SIMS/design/IMPLEMENTATION_PLAN.md` to `docs/SIMS/archived/` once Phase 2 planning begins (it's a live planning doc until then).

---

## Step 2 — Write `docs/SIMS/OPERATIONS.md`

Create the file with these three sections:

- [x] **Deployment**
  - List of SQL files in `schema/sql/identity/` to apply and their order
  - Required PostgreSQL extensions (`pgcrypto` / `uuid-ossp`)
  - Required env vars / ConfigStore keys
  - Staging vs. production differences (if any)

- [x] **Configuration**
  - What `config/identity_policy.yml` controls (entity tracking values, reconciliation flags)
  - How to refresh it from Shape Shifter's `sead_standard_model.yml` (manual step, document the procedure)
  - Which keys are required vs. optional

- [x] **Troubleshooting**
  - Scope not found → resolution
  - UUID extension missing → resolution
  - Duplicate source identity on re-submit → expected behaviour vs. error
  - Policy file stale after Shape Shifter release → refresh procedure
  - At least 2–3 more from test failures encountered during Phase 1

---

## Step 3 — Write `src/identity/README.md`

Keep it to 4–6 paragraphs:

- [x] One-sentence module purpose
- [x] Submodule map: `models.py`, `policy.py`, `repository.py`, `service.py`, `types.py` — one line each
- [x] How to run the identity test suite (`uv run pytest tests/identity/ -v`)
- [x] Pointer to `docs/SIMS/` for design context, `docs/SIMS/OPERATIONS.md` for deployment

---

## Step 4 — Audit Endpoint Docstrings

- [x] Check every endpoint in `src/api/router.py` that touches `/identity/` routes
- [x] Ensure each endpoint has: summary, error codes (400/404/409/422), and a one-line example payload reference
- [x] Verify FastAPI's `/docs` renders correctly after the audit

---

## Step 5 — Update `docs/SIMS/TRACKED_ENTITIES.md`

- [x] Confirm the entity table matches current `config/identity_policy.yml`
- [x] Add a header note: *"This file mirrors `config/identity_policy.yml`. Update both together when onboarding new entities."*
- [x] Mark Phase 1 entities as `live` and Phase 3–5 entities as `planned`

---

## Done When

All five steps are checked off and `docs/SIMS/OPERATIONS.md` + `src/identity/README.md` exist with non-placeholder content.
