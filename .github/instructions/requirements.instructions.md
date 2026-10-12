---
description: "Use for REQUIREMENTS.md and other requirements-focused documentation: functional requirements, scope and goals, usage scenarios, and high-level API behavior."
applyTo: "docs/SIMS/REQUIREMENTS.md"
---
# Requirements Docs

## Purpose

Keep `docs/SIMS/REQUIREMENTS.md` as the authoritative statement of what SIMS must do: the problem it solves, its scope and goals, the domain concepts it relies on, and the functional requirements (FR-1..27) that implementation must satisfy. Write for readers who need to know the required behavior before touching design, code, or tests.

When editing an existing document, preserve its structure and the existing `FR-*` numbering unless reorganization or renumbering is explicitly requested.

**Constraint priority** (highest to lowest): content scope → writing rules → size expectations.

## What belongs

- Problem statement: why the system exists and the boundaries of the problem
- Scope and goals: what is in and out of scope, and what success looks like
- Domain concepts: core identity concepts, tracked entities, entity subtypes, relationship types
- Functional requirements: numbered `FR-*` requirements grouped by concern
- Usage scenarios: concrete end-to-end situations that the requirements must satisfy
- High-level API behavior: API-visible concepts and API non-goals

## Scope boundaries

- `docs/SIMS/REQUIREMENTS.md` — functional requirements, scope and goals, domain concepts, usage scenarios, API behavior
- `docs/SIMS/CONCEPTUAL_MODEL.md` — conceptual/domain model (concepts, design rules, decision flow, lifecycles)
- `docs/SIMS/DESIGN.md` — implementation/storage design
- `docs/SIMS/DIAGRAMS.md` — visual workflows and state machines
- `docs/SIMS/OPERATIONS.md` — deployment, configuration, troubleshooting
- `docs/SIMS/archived/` — historical reference only; not authoritative for current requirements

## Writing rules

- State each requirement as testable behavior: clear enough that a reader can judge whether an implementation satisfies it.
- Number functional requirements `FR-*`. Do not reuse or silently renumber existing numbers; when adding a requirement, append the next available number.
- Mark out-of-scope items explicitly rather than leaving intent implied.
- Prefer concrete wording: name the entity, rule, input, output, or error directly.
- Distinguish current (Phases 1–2, implemented) from planned (Phases 3–5, outlined but not implemented).
- Do not restate design decisions or implementation detail here; link to the conceptual model or design doc instead.

## Size expectations

No fixed word target; keep the document complete but non-redundant. Each requirement group should state requirements, not rationale. Move rationale and design discussion to the conceptual model or design doc.

## Sources to trust

- `docs/SIMS/CONCEPTUAL_MODEL.md` — the conceptual model that requirements must stay consistent with
- `docs/SIMS/DESIGN.md` — implementation/storage design
- `src/identity/` — SIMS implementation; verify requirement wording against actual behavior
- `config/identity_policy.yml` — identity policy that requirements reference
