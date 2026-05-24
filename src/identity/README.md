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
| `policy.py` | `IdentityPolicy` — loads `config/identity_policy.yml` at startup and returns per-entity `EntityPolicy` snapshots |
| `service.py` | `IdentityService` — core operations: `get_or_create_scope`, `create_submission`, `resolve_identity`, `bind`, `resolve_and_bind`, `confirm_binding_set`, `associate_change_request`, `detect_change`, `get_binding_set`, `list_scopes` |

The API layer lives in `src/api/identity_router.py` (registered in `main.py`).

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

## Running Tests

```bash
# Unit tests (no database required)
uv run pytest tests/identity/ -v

# Integration tests (live DB required)
SIMS_INTEGRATION_DB=1 ENV_FILE=tests/.env uv run pytest tests/identity/test_service_integration.py -v
```

Test coverage: 132 unit tests + 15 integration tests (all passing as of 2026-04-06).
