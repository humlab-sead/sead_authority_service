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
| `contracts.py` | Provider-scope business-key contracts: scope rules, caller authorization, and the conflict/required error types |
| `policy.py` | `IdentityPolicy` — loads `config/identity_policy.yml` at startup, returns per-entity `EntityPolicy` snapshots, and publishes per-entity `EntityCapability` snapshots for `GET /identity/capabilities` |
| `service.py` | `IdentityService` — core operations: `get_or_create_scope`, `create_submission`, `resolve_identity`, `bind`, `resolve_batch`, `resolve_and_bind`, `confirm_binding_set`, `associate_change_request`, `detect_change`, `get_binding_set`, `list_scopes`, `register_scope_contracts`, `list_scope_contracts`, `require_registered_contracts` |

The API layer lives in `src/api/identity_router.py` (registered in `main.py`).

Endpoints include `GET /identity/capabilities`, which lists the supported identity
operations for each configured entity type.

---

## Core Operations

```
resolve_identity()  →  ResolutionOutcome (outcome: "new" | "matched")
resolve_batch()     →  ResolveBatchResult — atomic, idempotent batch (scope_name + run_id)
bind()              →  BindingSetResponse (lifecycle_state: proposed | confirmed)
confirm_binding_set()       — proposed → confirmed (manual review path)
associate_change_request()  — link confirmed set to a SEAD CR name
detect_change()     →  ChangeDetectionResult (outcome: insert | update | skip)
register_scope_contracts()    — register the ordered business keys of a provider scope
require_registered_contracts() — reject provider-scope work without a contract
```

`resolve_batch()` is the endpoint entry point: it wraps scope, submission, resolution,
and binding in one transaction, replays the stored result for an identical `run_id`, and
rejects a reused `run_id` whose payload differs. `POST /identity/resolve` requires a `run_id`.

`resolve_and_bind()` is a convenience shorthand for the common resolve-then-bind flow.

---

## Provider-Scope Business-Key Contracts

A provider scope (`provider://<code>/<schema>`) registers the ordered business-key
list it uses for each entity type. The contract is stored in
`sead_identity.scope_entity_contracts` and is the single place that decides which key
list is valid for that provider. Two projects that share a provider scope cannot
declare different key lists.

- `POST /identity/scope-contracts` registers one or more entity contracts.
- `GET /identity/scope-contracts?scope_name=...` lists the registered contracts.
- Registration is idempotent: an exact ordered match returns `state: "existing"`.
- A different key list or key order returns HTTP `409` with the registered and
  submitted lists, and writes nothing.
- Registration requires the `X-SIMS-Caller` and `X-SIMS-Caller-Token` headers. The
  caller must appear in `identity.contract_registration.callers` in the runtime
  config, and the scope must start with one of the caller's `scope_prefixes`. The
  allowlist lives in SIMS, so a caller cannot claim an arbitrary scope.
- `POST /identity/resolve` rejects a `provider://` batch whose entity types have no
  registered contract with HTTP `409` before any scope, submission, source identity,
  or binding row is written.
- Internal scopes such as `sead://admin`, `sead://migration`, and
  `sead://reconciliation` do not need a contract.

Callers still validate the delivered key values before they call SIMS. The contract
check answers whether an entity type may be resolved in that provider scope, not
whether one row's values are valid.

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
SIMS_INTEGRATION_DB=1 ENV_FILE=tests/.env uv run pytest tests/identity/test_scope_contracts_integration.py -v
```

Contract coverage lives in `tests/identity/test_contracts.py` (rules and
authorization), `test_scope_contracts_service.py` (service behavior),
`test_scope_contracts_repository.py` (SQL mapping), `test_scope_contracts_api.py`
(endpoint behavior), and `test_scope_contracts_integration.py` (live database).

Test coverage: 132 unit tests + 15 integration tests (all passing as of 2026-04-06).
