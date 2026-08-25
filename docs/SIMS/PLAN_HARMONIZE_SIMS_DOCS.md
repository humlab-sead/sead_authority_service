# Plan: Harmonize docs/SIMS with docs/ conventions (sead_authority_service)

## Scope
Repo: sead_authority_service. Folder: docs/SIMS/.

## Decisions (locked)
- Keep `CONCEPTUAL_MODEL.md` as-is (no fold into DESIGN.md, no deletion).
- Skip `DEVELOPMENT.md` until needed (deferred).
- Rename `IMPLEMENTATION_VIEW.md` → `DESIGN.md`.
- Do not extend `readme.instructions.md` (stays scoped to repo-root README only).
- No content merges: one rename + instruction-file alignment + cross-reference updates.
- H1 for the renamed doc: `# Design`.

## Target inventory
- README.md — doc map / index (no instruction coverage; readme.instructions.md stays root-only)
- REQUIREMENTS.md — keep; covered by new requirements.instructions.md
- CONCEPTUAL_MODEL.md — keep; covered by design.instructions.md (extended)
- DESIGN.md — renamed from IMPLEMENTATION_VIEW.md; covered by design.instructions.md (extended)
- DIAGRAMS.md — keep; already covered (diagrams.instructions.md is global)
- OPERATIONS.md — keep; covered by operations.instructions.md (extended)
- TRACKED_ENTITIES.md — auto-generated, leave as-is
- TLDR.md — leave untouched
- archived/ — historical, leave as-is
- proposals/ — out of scope

## Existing instructions (sead_authority_service/.github/instructions/)
- design.instructions.md — applyTo: "docs/DESIGN.md" (single path string) → extend (step 1)
- development.instructions.md — applyTo: "docs/DEVELOPMENT.md" — no change (DEVELOPMENT.md deferred)
- diagrams.instructions.md — NO applyTo (applies globally to all Mermaid diagrams) — no change
- operations.instructions.md — applyTo: "docs/OPERATIONS.md" → extend (step 3)
- readme.instructions.md — applyTo: "README.md" (root only) — no change (per decision)
- No requirements.instructions.md exists — create one (step 6)
- Convention for multi-path applyTo: comma-separated glob string, e.g. `"path/a.md,path/b.md"` — not YAML list.

## Steps

### Phase 1 — Instruction files (extend applyTo + add requirements.instructions.md)
1. Edit `design.instructions.md`: `applyTo` `"docs/DESIGN.md"` → `"docs/DESIGN.md,docs/SIMS/DESIGN.md,docs/SIMS/CONCEPTUAL_MODEL.md"`. Add a scope note: CONCEPTUAL_MODEL.md = conceptual/domain model; DESIGN.md = implementation/storage design.
2. `development.instructions.md`: no change (DEVELOPMENT.md deferred).
3. Edit `operations.instructions.md`: `applyTo` `"docs/OPERATIONS.md"` → `"docs/OPERATIONS.md,docs/SIMS/OPERATIONS.md"`.
4. `diagrams.instructions.md`: no change.
5. `readme.instructions.md`: no change (per decision).
6. Create `.github/instructions/requirements.instructions.md`, modeled on `design.instructions.md` structure (Purpose / What belongs / Scope boundaries / Writing rules / Size expectations / Sources to trust), derived from the actual content of `docs/SIMS/REQUIREMENTS.md`. Set `applyTo: "docs/SIMS/REQUIREMENTS.md"`.

Steps 1, 3, 6 are independent and can run in parallel. Do all before Phase 2 so the renamed doc is governed from the start.

### Phase 2 — Rename IMPLEMENTATION_VIEW.md → DESIGN.md
7. `git mv docs/SIMS/IMPLEMENTATION_VIEW.md docs/SIMS/DESIGN.md`.
8. Update H1 `# Implementation View` → `# Design`; adjust the Purpose opening ("implementation-level view" → "design view") and the "It sits after REQUIREMENTS.md and CONCEPTUAL_MODEL.md…" paragraph so it describes DESIGN.md's role.

### Phase 3 — Update cross-references (grep-verified, non-archived, non-graphify)
9. Update `IMPLEMENTATION_VIEW` references in:
   - `AGENTS.md` — doc list: `…CONCEPTUAL_MODEL, IMPLEMENTATION_VIEW, DIAGRAMS…` → `…CONCEPTUAL_MODEL, DESIGN, DIAGRAMS…`
   - `docs/DESIGN.md` — same list reference.
   - `docs/SIMS/README.md` — doc-map row `[IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md)` → `[DESIGN.md](./DESIGN.md)`; description stays "Storage design, rollout strategy, SQL structures".
   - `docs/SIMS/DIAGRAMS.md` — intro link `[IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md)` → `[DESIGN.md](./DESIGN.md)`.
   - `src/identity/models.py` — docstring `docs/SIMS/IMPLEMENTATION_VIEW.md § Storage Design` → `docs/SIMS/DESIGN.md § Storage Design`.
   - `src/identity/service.py` — docstring `IMPLEMENTATION_VIEW § Core Operations` → `DESIGN.md § Core Operations`.
   - `schema/sql/identity/008_seed_scopes.sql` — comment `per IMPLEMENTATION_VIEW § Internal Origins` → `per DESIGN § Internal Origins`.
10. Leave `docs/SIMS/archived/*` untouched. Regenerate graph: run `.venv/bin/graphify update .` (never hand-edit graphify-out).

### Phase 4 — Verification
11. `grep IMPLEMENTATION_VIEW` across the repo → zero hits outside `docs/SIMS/archived/` and `graphify-out/`.
12. Confirm each edited instructions file's `applyTo` is a valid comma-separated glob string (no YAML array).
13. Read `docs/SIMS/DESIGN.md` and `docs/SIMS/README.md` end-to-end for link/anchor consistency.

## Relevant files
- `.github/instructions/design.instructions.md` — extend applyTo + scope note
- `.github/instructions/operations.instructions.md` — extend applyTo
- `.github/instructions/requirements.instructions.md` — new file
- `docs/SIMS/IMPLEMENTATION_VIEW.md` → `docs/SIMS/DESIGN.md` — rename + H1 edit
- `docs/SIMS/README.md`, `docs/SIMS/DIAGRAMS.md` — cross-links
- `AGENTS.md`, `docs/DESIGN.md` — doc-list references
- `src/identity/models.py`, `src/identity/service.py` — docstrings
- `schema/sql/identity/008_seed_scopes.sql` — comment

## Decisions
- Keep `CONCEPTUAL_MODEL.md`; skip `DEVELOPMENT.md`; rename `IMPLEMENTATION_VIEW.md` → `DESIGN.md`; `readme.instructions.md` unchanged.
- `requirements.instructions.md` is authority_service-only; sead_shape_shifter's `docs/REQUIREMENTS.md` stays uncovered — out of scope.
- applyTo multi-path convention: comma-separated string, not YAML array.

## Further Considerations
1. Deferred: whether a future `DEVELOPMENT.md` is ever needed for "Rollout Approach"/"Internal Origins"; keep those sections inside `DESIGN.md` for now.
2. `docs/SIMS/README.md` remains without dedicated instruction coverage (readme.instructions.md stays root-only) — acceptable unless the doc map grows beyond a simple index.
