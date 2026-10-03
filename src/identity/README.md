# `src/identity/` — SIMS Identity Module

The SEAD Identity Management System (SIMS) implemented as a FastAPI sub-module of `sead_authority_service`. Provides stable UUID-based identities for tracked SEAD entities and resolves provider submissions to those identities.

**Design context:** `docs/SIMS/` · **Operations:** `docs/SIMS/OPERATIONS.md`

---

## Submodules

| File | Responsibility |
|---|---|
| `types.py` | Enums: `IdentityType`, `SubmissionStatus`, `TrackedIdentityState`, `BindingSetState`, `BindingMethod`, `ChangeOutcome` |
| `models.py` | Pydantic domain models (`SourceScope`, `Submission`, `SourceIdentity`, `TrackedIdentity`, `BindingSet`, `Binding`) and request/response DTOs (`ResolutionRequest`, `ResolutionOutcome`, `BindingSetResponse`, `ChangeDetectionRequest`, `ChangeDetectionResult`) |
| `repository.py` | Async DB repositories — one per table, using `get_connection()` from `src.configuration`. All are injectable for testing. |
| `policy.py` | `IdentityPolicy` — loads `config/identity_policy.yml` at startup, returns per-entity `EntityPolicy` snapshots, and publishes per-entity `EntityCapability` snapshots for `GET /identity/capabilities` |
| `service.py` | `IdentityService` — core operations: `get_or_create_scope`, `create_submission`, `resolve_identity`, `bind`, `resolve_and_bind`, `confirm_binding_set`, `associate_change_request`, `detect_change`, `get_binding_set`, `list_scopes` |

The API layer lives in `src/api/identity_router.py` (registered in `main.py`).

Endpoints include `GET /identity/capabilities`, which lists the supported identity
operations for each configured entity type.

---

## Core Operations

```
resolve_identity()  →  ResolutionOutcome (outcome: "new" | "matched")
bind()              →  BindingSetResponse (lifecycle_state: proposed | confirmed)
confirm_binding_set()       — proposed → confirmed (manual review path)
associate_change_request()  — link confirmed set to a SEAD CR name
detect_change()     →  ChangeDetectionResult (outcome: insert | update | skip)
```

`resolve_and_bind()` is a convenience shorthand for the common resolve-then-bind flow.

---

## Capabilities And Operation Checks

`GET /identity/capabilities` returns a versioned list of configured entity types and
which operations each supports:

- `bind_existing` — accept `approved_aggregate_id` to bind an existing tracked identity.
- `allocate_new` — mint a new tracked aggregate after an approved miss.

Capabilities come from validated `operations` blocks in `config/identity_policy.yml`,
not from entity-specific code or an implicit default. `POST /identity/resolve` rejects an
unconfigured entity type or an unsupported operation with HTTP `422` before writing any
scope, submission, source identity, or tracked identity record.

---

## Running Tests

```bash
# Unit tests (no database required)
uv run pytest tests/identity/ -v

# Integration tests (live DB required)
SIMS_INTEGRATION_DB=1 ENV_FILE=tests/.env uv run pytest tests/identity/test_service_integration.py -v
```

Test coverage: 132 unit tests + 15 integration tests (all passing as of 2026-04-06).
