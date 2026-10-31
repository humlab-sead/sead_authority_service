# Verify Reconciliation Candidates and Match Readiness — Phase 4 Task Plan

## Phase Summary

**Phase:** 4 — Authority Service: Readiness, Candidate Check, and SIMS Binding Rule. **Readiness:** Validated for implementation. This phase lives in the Authority Service repository as directed by the [Shape Shifter phase plan](https://github.com/humlab-sead/sead_shape_shifter/blob/reconciliation-mvp/docs/proposals/RECONCILIATION_MVP/RECONCILIATION_MVP_PHASE_PLAN.md#phase-4-authority-service--readiness-candidate-check-and-sims-binding-rule). Its normative contract is the local [Authority Service proposal](RECONCILIATION_IDENTITY_CONTRACT.md). No earlier Shape Shifter phase is an implementation dependency. Deliver the candidate check and readiness first for Shape Shifter Phase 5, followed by the independent SIMS and OpenRefine changes.

**Acceptance criteria**

1. [x] `PH4-AC-1` (from `AS-AC-1`, `AS-AC-2`): A batch returns one ordered result per candidate; `exists` requires a valid URI and an existing SEAD row; invalid candidates are `invalid_candidate`; types without `bind_existing` are `unsupported_type`.
2. [x] `PH4-AC-2` (from `AS-AC-3`): A SEAD database failure returns HTTP 503 with no partial results, and candidate checking makes no identity or binding writes.
3. [x] `PH4-AC-3` (from `AS-AC-4`): Readiness reports a reason when a match dependency is missing while the OpenRefine metadata endpoint keeps working.
4. [x] `PH4-AC-4` (from `AS-AC-5`): `POST /identity/resolve` rejects approved IDs without a `materialized` identity, including through an existing binding, with the state checked in the binding transaction.
5. [x] `PH4-AC-5` (from `AS-AC-7`): A validated per-query `limit` is honored and an unsupported type gets a client error without changing OpenRefine request or result formats.

**Fixed contract:** `POST /reconcile/verify-candidates` accepts `{"items":[{"type":"site","id":"<candidate URI>"}]}` with 1–100 items. HTTP 200 returns ordered `results` with the input `type` and `id`, one of `exists`, `not_found`, `invalid_candidate`, or `unsupported_type`, and `entity_type` plus `aggregate_id` **only** for `exists`. Invalid request size/shape is 422; a SEAD database failure is 503. `GET /reconcile/readiness?type=site` returns `{"type":"site","ready":true|false,"reason":null|"<reason>"}` (200); an unknown type is 422. Add no authentication. Candidate verification checks SEAD only; it neither accesses SIMS nor binds IDs. SIMS does not query SEAD. `AS-AC-6` requires the disposable-database tests in `VM-8`–`VM-10`; Phase 7 also depends on those results.

## Repository Findings

**Repository basis:** Authority Service branch `dev`, commit `35dc8eb`, inspected 2026-10-30. An existing modified `docs/proposals/README.md` and untracked proposal files were read only and left untouched. The local companion proposal is untracked; the phase plan is in the separate Shape Shifter repository. Graphify identified the strategy/route and identity service paths; the following findings were checked against current code, configuration, SQL, and tests. The reported failure of `authority.fuzzy_site` is an earlier local observation, **not** a newly verified database result.

| Verified source | Current behavior | Planning implication |
| --- | --- | --- |
| `src/strategies/strategy.py::{ReconciliationStrategy.as_candidate, get_id_path}`; `config/config.yml`; `src/resources/site.yml` | Candidates use configured `options:id_base` plus strategy path and ID. Missing `id_base` produces relative IDs. The `site` strategy queries `authority.site` through `authority.fuzzy_site`. | Validate the entire absolute URI inside the service, using configured origin/base and the registered strategy path; never extract just a numeric suffix. Check row existence against the `site` strategy's backing data, not SIMS. |
| `src/strategies/query.py::BaseRepository.get_details`; `src/resources/site.yml::details_sql` | Detail lookup catches database errors and returns `None`; its SQL also joins other tables. | Do not use this method to determine existence: an outage could become `not_found`. Use a parameterized, minimal `authority.site` lookup with database failures propagated. |
| `schema/generated/site.sql`, `schema/__deploy__.sql`; `docs/DEVELOPMENT.md` | Generated SQL contains the `authority.fuzzy_site(text, integer)` definition. Generated files must not be edited by hand. | Test whether the function is installed in a **disposable** database and run a real match. If missing, repair the database deployment from the existing generated schema through the documented deployment process; do not assume a code/schema change is needed. Retain a negative readiness test for the missing function. |
| `src/api/router.py::{meta, reconcile}`; `src/api/model.py::ReconQuery`; `src/reconcile.py::reconcile_queries` | GET `/reconcile` builds metadata without exercising the match path. POST accepts JSON, form-encoded and double-encoded queries, validates `limit` as 1–500, but uses the default limit. Unknown types raise `ValueError` and fall into a 500 catch. | Add separate typed check/readiness routes without changing GET metadata; use validated query limit and map only unsupported-type errors to a 4xx. Keep all existing OpenRefine forms and response shapes. |
| `src/identity/policy.py::IdentityPolicy.supports`; `config/identity_policy.yml` | `site` enables `bind_existing`; configured types without that operation exist. Strategy registration and policy are separate. | Gate the pilot check on the registered `site` strategy and explicit `bind_existing`. Unsupported types receive per-item outcomes, not row lookups. Do not silently extend the pilot to all advertised types. |
| `src/identity/service.py::{resolve_identity, _reuse_confirmed_bindings, bind, resolve_batch}`; `src/identity/repository.py::TrackedIdentityRepository` | Approved-ID lookup and confirmed-binding reuse check ID/type but not lifecycle state. `resolve_batch` wraps the operation in `get_connection()`, which reuses one transaction; the replay path returns before binding. `bind` currently locks source identities, not tracked identity rows. | Recheck and lock approved tracked identities inside the transaction before creating/reusing bindings; cover the confirmed-binding and replay paths. Preserve allocation for requests without an approved ID. |
| `tests/api/{test_router,test_router_extended,test_model}.py`, `tests/test_reconcile.py`, `tests/identity/{test_api,test_service,test_repository,test_service_integration}.py`, `tests/identity/conftest.py` | Unit/API fixtures mock config and repositories. Integration tests are guarded by `SIMS_INTEGRATION_DB=1` and the helper-owned `127.0.0.1:55432/sead_staging` database. An existing integration test accepts any tracked `site` state for an approved ID. | Add API/unit cases and isolated disposable-DB contract tests; update the old approved-ID fixture to use a `materialized` identity. Do not run live tests against a deployment database. |

## Scope

**In scope:** `site` candidate URI and SEAD-row checks; 1–100 item batch models and HTTP errors; strategy-backed readiness and missing-function handling; transaction-safe SIMS approved-ID state checks; OpenRefine per-query limit and unsupported-type response; focused unit/API and disposable-database tests; related operational, testing, and SIMS documentation.

**Out of scope:** Changes to Shape Shifter, automatic acceptance or binding during review, SIMS lookup in the candidate check, adoption of existing SEAD rows into SIMS, new authentication, production schema repair, or checks for all registered reconciliation types. Existing policy and generated schema are read-only unless a test proves a source/config defect; generated SQL must be regenerated from its source if a change is actually necessary.

## Work Breakdown

### Area 1: Confirm the site match path and add read-only verification

**Objective:** Phase 5 can submit candidate URIs and distinguish existing rows, missing rows, invalid candidates, and unsupported types without any SIMS write.

**Affected code:** `src/api/model.py`, `src/api/router.py`, `src/candidate_verification.py` (**NEW**), `src/strategies/site.py`, `src/resources/site.yml`, `tests/api/test_candidate_verification.py` (**NEW**), `tests/api/test_model.py`, `tests/strategies/test_site.py`, `tests/identity/test_reconciliation_contract_integration.py` (**NEW**).

**Dependencies:** Existing `site` registration, `identity_policy.yml`, and database-backed match SQL. No Shape Shifter implementation dependency.

* [x] `T1.1` **Change:** Verify the deployed `site` match dependency before interpreting candidate-check failures.
  * **Target:** `src/resources/site.yml::fuzzy_find_sql`, `schema/generated/site.sql` (inspect only), and the disposable-DB test in `tests/identity/test_reconciliation_contract_integration.py` (**NEW**).
  * **Current → required:** The generated function exists in source, but a prior local match failed because the deployed function was absent → execute the actual `site` match query with a bounded limit in the helper-owned disposable database, check that `authority.fuzzy_site(text,integer)` exists, and record which deployment step supplies it.
  * **Implementation:** Seed or select a `site` row in the disposable database, assert the match returns the configured candidate URI, and record the absence case separately. If the function is missing, repair **that database's deployment** through the existing generated-schema procedure, then rerun; report a deployment blocker if the helper-owned database cannot be prepared. Do not hand-edit `schema/generated/site.sql` or claim the function is absent from repository SQL.
  * **Constraints:** Do not connect to, modify, or run schema repair on staging/production as part of this plan. Keep the missing-function readiness regression even when the disposable database is repaired.
  * **Validation:** `V-3`: real `site` query and dependency check in an isolated database, not just manifest or mocks.
* [x] `T1.2` **Change:** Validate candidate URIs and perform a minimal read-only row lookup.
  * **Target:** `src/candidate_verification.py` (**NEW**), `src/strategies/site.py::SiteRepository`, `src/resources/site.yml::sql_queries`, `tests/api/test_candidate_verification.py` (**NEW**), `tests/strategies/test_site.py`, `tests/identity/test_reconciliation_contract_integration.py` (**NEW**).
  * **Current → required:** No candidate existence check; detail lookup hides database failures → parse the full candidate ID and query `authority.site` by `site_id` with a bound positive integer, propagating database errors.
  * **Implementation:** Compare absolute scheme/authority and the complete configured `id_base`; require the matching registered strategy's one type segment and one positive decimal ID, with no extra path, query, or fragment. Gate `site` on both registration and `IdentityPolicy.supports("site", "bind_existing")`; treat unknown, disabled, or non-pilot types as `unsupported_type`. Reject wrong origin/base, type/path mismatch, encoded extra path segments, nonnumeric/zero/negative IDs and relative URLs as `invalid_candidate` **without querying**. Return only `(entity_type="site", aggregate_id)` after a row exists; never use score or `match`.
  * **Constraints:** Use `get_connection()` through the existing repository pattern and a parameterized site query. Do not reuse `get_details()` because it converts DB failure to absence. Never call identity services or create a binding.
  * **Validation:** `V-1`, `V-2`, `V-3`: malformed input makes zero DB calls; matching row returns `exists`; valid missing ID returns `not_found`; outage is not `not_found`.
* [x] `T1.3` **Change:** Publish the bounded batch endpoint and exact response contract.
  * **Target:** `src/api/model.py` (typed request/item/result DTOs), `src/api/router.py` (new `POST /reconcile/verify-candidates`), `tests/api/{test_model.py,test_candidate_verification.py}` (**NEW** for the latter).
  * **Current → required:** No route → accept exactly 1–100 items and produce an ordered, echoing result per item with only the four defined outcomes.
  * **Implementation:** Use Pydantic length/field validation for 422, retain duplicate items in request order, and omit `entity_type`/`aggregate_id` on every non-`exists` result. Evaluate all items before sending a response; a database/pool failure at any point returns 503 with no partial `results`. Log failures without returning a successful or missing-row result. Keep the router under `/reconcile` and add no authentication.
  * **Constraints:** For invalid/unsupported items, do not access the database. Test an early `exists` followed by a database failure to prove the batch does not return partial success. Assert no calls to identity/binding repositories, and no identity, submission, or Binding Set rows change in the disposable database.
  * **Validation:** `V-1`, `V-2`, `V-3`: exact 200/422/503 shapes, ordering, limits 1/100/101, no-write behavior.

**Completion evidence:** A real `site` candidate round-trips through match → candidate check in a disposable database; failures and unsupported candidates cannot masquerade as an existing row.

### Area 2: Report database-backed match readiness

**Objective:** Operators can distinguish configured metadata from a working match path.

**Affected code:** `src/api/model.py`, `src/api/router.py`, `tests/api/test_readiness.py` (**NEW**), `tests/identity/test_reconciliation_contract_integration.py` (**NEW**).

**Dependencies:** Area 1's confirmed match path; can be implemented alongside candidate validation.

* [x] `T2.1` **Change:** Add strategy-specific readiness without altering the metadata endpoint.
  * **Target:** `src/api/model.py` (typed readiness DTO), `src/api/router.py` (new `GET /reconcile/readiness`), `tests/api/test_readiness.py` (**NEW**), `tests/identity/test_reconciliation_contract_integration.py` (**NEW**).
  * **Current → required:** `GET /reconcile` succeeds even if `authority.fuzzy_site` is unavailable → readiness checks configured `id_base` and executes the registered strategy's actual database-backed match path with a minimal query and limit 1.
  * **Implementation:** Require `type`; return 422 for unknown/unsupported readiness types; return HTTP 200 with `ready: false` and a clear reason when `id_base`, the database/view, or a required match function is missing. Return `ready: true, reason: null` only after a successful match query (an empty result is still ready). Use the same `site` strategy path as `POST /reconcile`, not a metadata-only SQL probe. Leave `GET /reconcile` and its OpenRefine manifest unchanged.
  * **Constraints:** Do not probe by creating identities or binding IDs. Failures must not be logged as successful readiness or silently treated as an empty match; avoid leaking database credentials in the reason.
  * **Validation:** `V-3`, `V-4`: present/missing function, missing `id_base`, DB failure, unknown type, and unchanged manifest.

**Completion evidence:** Readiness fails with an actionable reason on a database missing the match function while GET metadata still returns its previous format.

### Area 3: Enforce materialized approved identities at binding

**Objective:** Approved existing IDs cannot create or reuse bindings to unmaterialized/invalidated identities, even if their state changes after lookup.

**Affected code:** `src/identity/repository.py`, `src/identity/service.py`, `src/api/identity_router.py` (only if an existing error mapping needs adjustment), `tests/identity/{test_repository,test_service,test_api,test_service_integration}.py`, `tests/identity/test_reconciliation_contract_integration.py` (**NEW**).

**Dependencies:** Independent of Areas 1–2; sequence after their candidate-check/readiness delivery.

* [x] `T3.1` **Change:** Lock and read the tracked identity's current lifecycle state in the binding transaction.
  * **Target:** `src/identity/repository.py::TrackedIdentityRepository` (parameterized `SELECT ... FOR UPDATE` by tracked UUID, checking type and aggregate ID); `tests/identity/test_repository.py`, `tests/identity/test_reconciliation_contract_integration.py` (**NEW**).
  * **Current → required:** `find_by_aggregate_id()` and `get()` do not lock tracked rows → acquire a tracked-row lock and read state on the same connection/transaction used by binding. `get_connection()` already shares the active transaction across nested repository calls.
  * **Implementation:** Make a missing/mismatched row or lifecycle state other than `materialized` a binding conflict; never promote an existing SIMS identity or query SEAD. Validate serialization against a concurrent lifecycle update in the disposable database.
  * **Constraints:** A lock obtained only in an earlier, committed lookup transaction does not satisfy this task. Leave unapproved allocation and SIMS policy capability checks intact.
  * **Validation:** `V-5`, `V-6`: inspect locking SQL/parameters and demonstrate that a state transition cannot pass between the locked check and binding.
* [x] `T3.2` **Change:** Apply the rule to approved-ID lookup, confirmed-binding reuse, and batch replay.
  * **Target:** `src/identity/service.py::{resolve_identity, _reuse_confirmed_bindings, bind, resolve_batch, resolve_and_bind}`, `tests/identity/{test_service,test_api,test_service_integration}.py`, `tests/identity/test_reconciliation_contract_integration.py` (**NEW**).
  * **Current → required:** An approved ID in `allocated`, `pending_materialization`, or `invalidated` can match; an existing confirmed binding or stored replay can bypass a later check → reject any non-`materialized` approved identity with the existing HTTP 409 conflict mapping, including those paths.
  * **Implementation:** Carry which input requests have approved IDs into the locked validation immediately before binding-set creation/reuse, including matches supplied by `_reuse_confirmed_bindings`. In `resolve_batch`, preserve the run-key/fingerprint behavior while checking current approved-ID state before returning a stored replay; for `resolve_and_bind`, ensure a separate early lookup cannot substitute for the locked check in `bind`. For a batch failure, roll back source identities, submission, binding set, and replay record. Update existing unit fixtures that currently expect an `allocated` approved ID to succeed, and select or seed `materialized` identities in the existing live approved-ID test.
  * **Constraints:** Do not reject an unapproved allocation or change how non-approved matches behave. Do not trust a cached lifecycle state from an earlier lookup; keep the HTTP API request and success response shapes unchanged.
  * **Validation:** `V-5`, `V-6`: all three non-materialized states, missing row, existing binding, same-run replay after invalidation, state change between lookup and lock, successful materialized bind, and unchanged new-ID allocation.

**Completion evidence:** Approved-ID resolve returns 409 and no binding write for each disallowed state; a materialized tracked identity succeeds using the existing API.

### Area 4: Preserve OpenRefine compatibility and document deployment checks

**Objective:** Existing OpenRefine clients keep their formats while query limits and unsupported-type errors become correct.

**Affected code:** `src/reconcile.py`, `src/api/router.py`, `tests/test_reconcile.py`, `tests/api/{test_router,test_router_extended}.py`, `docs/OPERATIONS.md`, `docs/TESTING.md`, `docs/SIMS/DESIGN.md`.

**Dependencies:** Can follow Areas 1–2 independently of Area 3; validate all routes together last.

* [x] `T4.1` **Change:** Use the validated per-query limit and return a client error for an unknown query type.
  * **Target:** `src/reconcile.py::reconcile_queries`, `src/api/router.py::reconcile`, `tests/test_reconcile.py`, `tests/api/{test_router,test_router_extended}.py`.
  * **Current → required:** `ReconQuery.limit` validates 1–500 but `reconcile_queries()` always passes the configured default; `ValueError` for unknown type becomes HTTP 500 → honor `query["limit"]` when present, retain the default otherwise, and return a clear 4xx for unsupported type.
  * **Implementation:** Distinguish the known unknown-type validation error from genuine unexpected and database exceptions; do not broadly translate all failures into 4xx. Preserve form-encoded, JSON, double-encoded queries, default type, response keys, and candidate shape.
  * **Constraints:** Do not change the existing per-query 1–500 bounds, status for unrelated malformed requests, or the OpenRefine manifest.
  * **Validation:** `V-7`: two queries with different limits, default fallback, invalid bounds, unknown type 4xx, and unchanged request/response compatibility.
* [x] `T4.2` **Change:** Document and validate the shipped Authority Service contract.
  * **Target:** `docs/OPERATIONS.md`, `docs/TESTING.md`, `docs/SIMS/DESIGN.md`; this task plan's progress tracker.
  * **Current → required:** These guides do not describe the new candidate/readiness responses or the new approved-ID state rule → document the API checks, the helper-owned disposable-DB workflow, missing-function remediation through generated SQL deployment, and the SIMS bind-time rejection.
  * **Implementation:** Record actual test commands/results and any deployment-only dependency in the tracker. If the repository or database state contradicts a fixed proposal decision, stop and report rather than extending the design or modifying unrelated repositories.
  * **Constraints:** Do not describe candidate verification as adoption into SIMS or `GET /reconcile` as readiness; no production DB repair in this task.
  * **Validation:** `V-8`: documentation and quality checks match the implemented API, and internal document paths resolve.

**Completion evidence:** `V-7` passes (67 passed, 1 skipped); the operations/testing/SIMS guides were updated. The disposable-database checks `V-3` and `V-6` pass. `V-8` passes after the checker was changed to compare imports by resolved source module and `populate_embeddings.py` switched to `src.*` imports.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH4-AC-1` (`AS-AC-1`, `AS-AC-2`, `AS-AC-6`; `VM-8`) | `T1.1`, `T1.2`, `T1.3` | `V-1`, `V-2`, `V-3` | One ordered result per candidate; only a valid URI plus a real `site` row yields `exists`; other types/invalid IDs are classified without a lookup. |
| `PH4-AC-2` (`AS-AC-3`, `AS-AC-6`; `VM-8`) | `T1.2`, `T1.3` | `V-2`, `V-3` | Database failure returns 503 without partial results or SIMS writes. |
| `PH4-AC-3` (`AS-AC-4`, `AS-AC-6`; `VM-9`) | `T1.1`, `T2.1` | `V-3`, `V-4` | Missing match function returns `ready: false` and a reason; GET metadata remains available. |
| `PH4-AC-4` (`AS-AC-5`, `AS-AC-6`; `VM-10`) | `T3.1`, `T3.2` | `V-5`, `V-6` | All non-materialized approved states and race/confirmed binding/replay reject under a transaction; materialized bind succeeds. |
| `PH4-AC-5` (`AS-AC-7`; `VM-11`) | `T4.1` | `V-7` | Valid query limits reach strategies; unknown type is 4xx; JSON/form formats and result shape remain stable. |

## Validation And Testing

Run commands from the Authority Service repository. `SIMS_INTEGRATION_DB=1` is allowed only with the existing test fixture's helper-owned loopback database and matching environment configuration; if it is unavailable, record `V-3`/`V-6` as not run and do **not** claim `VM-8`–`VM-10` complete. A skipped database test is not a pass.

| ID | Check and target | Exact command or method | Covers | Expected result | Baseline (2026-10-30) |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Typed request/response and URI cases in `tests/api/test_model.py`, `tests/api/test_candidate_verification.py` (**NEW**): empty/1/100/101 items; wrong origin/path/type, query/fragment, missing base, invalid/positive decimal ID | `uv run pytest -o addopts='' -q tests/api/test_model.py tests/api/test_candidate_verification.py` | `PH4-AC-1` | Exact 422 boundary behavior; invalid IDs cause zero row lookups; non-`exists` fields are omitted. | Pass: existing model file included in 164-pass baseline. New tests not run. |
| `V-2` | Candidate endpoint/API and repository unit coverage in `tests/api/test_candidate_verification.py` (**NEW**), `tests/strategies/test_site.py`: mixed order/duplicates, policy gate, missing row, failure after a first success, no identity writes | `uv run pytest -o addopts='' -q tests/api/test_candidate_verification.py tests/strategies/test_site.py` | `PH4-AC-1`, `PH4-AC-2` | Ordered 200 results, unsupported/invalid per-item outcomes, no partial success on 503; no SIMS calls. | Pass: existing site strategy file included in 96-pass/1-skip baseline. New endpoint tests not run. |
| `V-3` | Disposable-DB match and candidate contract in `tests/identity/test_reconciliation_contract_integration.py` (**NEW**): installed vs missing match function, existing/missing/wrong-type candidate, outage and before/after SIMS row counts | On the helper-owned database, set the documented `SIMS_INTEGRATION_DB=1` and connection variables, then run `uv run pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py -k 'site_match or candidate or readiness'`. Also execute `SELECT to_regprocedure('authority.fuzzy_site(text,integer)')` and a bounded real `site` match in that disposable database; record the function result and any deployment repair. | `PH4-AC-1`, `PH4-AC-2`, `PH4-AC-3`; `AS-AC-6` | Real row check and match succeed; missing function makes readiness false with a reason; database failure is 503, and identity/binding counts do not change. | Not run: helper-owned disposable DB not configured for planning; new test does not yet exist. Earlier missing-function report not re-verified. |
| `V-4` | Readiness API in `tests/api/test_readiness.py` (**NEW**) and metadata regression in `tests/api/test_router.py`: missing function/base, empty-but-working query, unknown type, successful manifest | `uv run pytest -o addopts='' -q tests/api/test_readiness.py tests/api/test_router.py` | `PH4-AC-3` | 200 ready true/false with exact keys and reason, 422 unknown type, GET `/reconcile` unchanged. | Pass: existing router file included in 96-pass/1-skip baseline. New readiness tests not run. |
| `V-5` | SIMS locking, state and API conflict tests in `tests/identity/{test_repository,test_service,test_api}.py` | `uv run pytest -o addopts='' -q tests/identity/test_repository.py tests/identity/test_service.py tests/identity/test_api.py` | `PH4-AC-4` | 409 for non-materialized approved IDs, including confirmed binding/replay; locked SQL uses parameters; unapproved allocation and old success shape persist. | Pass: 78 service/API and 164 model/repository/unit tests ran in separate baselines. New state/race assertions not run. |
| `V-6` | Disposable-DB bind transaction test in `tests/identity/test_reconciliation_contract_integration.py` (**NEW**) and existing `tests/identity/test_service_integration.py`: state transition between lookup and bind, replay, approved states and materialized success | On the helper-owned database with `SIMS_INTEGRATION_DB=1`, run `uv run pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py tests/identity/test_service_integration.py -k 'approved or binding_state or materialized'`. | `PH4-AC-4`; `AS-AC-6` | Lock serializes lifecycle changes; rejected batch leaves no new binding/replay; materialized approved ID binds. | Not run: live database guard skipped 1 selected test (32 deselected); new integration file does not exist. |
| `V-7` | OpenRefine limit/error and compatibility tests in `tests/test_reconcile.py`, `tests/api/{test_router,test_router_extended}.py` | `uv run pytest -o addopts='' -q tests/test_reconcile.py tests/api/test_router.py tests/api/test_router_extended.py` | `PH4-AC-5` | Limits 1 and 500 reach strategy; omitted limit uses default; unsupported type 4xx; JSON/form/double-encoded requests and response keys unchanged. | Pass: 78 service/API run includes `test_reconcile.py`; 96-pass/1-skip run includes both route files. New limit/error assertions not run. |
| `V-8` | Formatting, lint, import rules and documentation | `uv run black --check src/api/model.py src/api/router.py src/candidate_verification.py src/reconcile.py src/strategies/site.py src/identity/repository.py src/identity/service.py tests/api/test_model.py tests/api/test_router.py tests/api/test_router_extended.py tests/api/test_candidate_verification.py tests/api/test_readiness.py tests/strategies/test_site.py tests/test_reconcile.py tests/identity/test_repository.py tests/identity/test_service.py tests/identity/test_api.py tests/identity/test_service_integration.py tests/identity/test_reconciliation_contract_integration.py && uv run ruff check src/api/model.py src/api/router.py src/candidate_verification.py src/reconcile.py src/strategies/site.py src/identity/repository.py src/identity/service.py && make check-imports`; review links and current claims in `docs/OPERATIONS.md`, `docs/TESTING.md`, `docs/SIMS/DESIGN.md` | All criteria | Changed sources conform to repository checks and guides match tested behavior. | Not run: new files and contracts do not exist; execute after implementation. |

Focused, read-only baselines: `uv run pytest -o addopts='' -q tests/test_reconcile.py tests/identity/test_api.py tests/identity/test_service.py` **78 passed**; `uv run pytest -o addopts='' -q tests/api/test_router.py tests/api/test_router_extended.py tests/strategies/test_site.py` **96 passed, 1 skipped**; `uv run pytest -o addopts='' -q tests/api/test_model.py tests/identity/test_repository.py tests/strategies/test_query.py` **164 passed**. The guarded database test was **1 skipped, 32 deselected**. These passes demonstrate existing behavior, not Phase 4.

## Execution Results

| ID | Result |
| --- | --- |
| `V-1` | Pass: `uv run pytest -o addopts='' -q tests/api/test_model.py tests/api/test_candidate_verification.py` — 104 passed. |
| `V-2` | Pass: `uv run pytest -o addopts='' -q tests/api/test_candidate_verification.py tests/strategies/test_site.py` — 57 passed. |
| `V-3` | Pass: `scripts/verify_sims_identity_candidates.sh setup` installed the Authority and SIMS schemas; `bootstrap site` materialized 3,462 existing site identities and initialized the allocator. `uv run pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py -k 'site_match or candidate or readiness'` — 2 passed, 3 deselected. The real match, candidate outcomes/no-write check, and missing-function readiness check passed. |
| `V-4` | Pass: `uv run pytest -o addopts='' -q tests/api/test_readiness.py tests/api/test_router.py` — 32 passed. |
| `V-5` | Pass: `uv run pytest -o addopts='' -q tests/identity/test_repository.py tests/identity/test_service.py tests/identity/test_api.py` — 120 passed. |
| `V-6` | Pass: after `bootstrap site`, `uv run pytest -o addopts='' -q tests/identity/test_reconciliation_contract_integration.py tests/identity/test_service_integration.py -k 'approved or binding_state or materialized'` — 4 passed, 34 deselected. Approved states, replay, materialized binding, and row-lock serialization passed against PostgreSQL. |
| `V-7` | Pass: `uv run pytest -o addopts='' -q tests/test_reconcile.py tests/api/test_router.py tests/api/test_router_extended.py` — 67 passed, 1 skipped. |
| `V-8` | Pass: Black check — 22 files unchanged; Ruff — passed; `uv run make check-imports` — no import path inconsistencies; `uv run pytest -o addopts='' -q tests/test_check_imports.py` — 3 passed. Direct and module `populate_embeddings.py --help` invocations both passed. The previously recorded documentation-link, helper syntax, ShellCheck, and whitespace checks passed. |

Full suite: `rtk make test` — 1,140 passed, 43 skipped, 7 warnings; exit status 0. Skipped tests do not replace the required `V-3`/`V-6` database checks.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Candidate models and endpoint | `src/api/model.py`, `src/api/router.py`, `src/candidate_verification.py` (**NEW**), `tests/api/test_model.py`, `tests/api/test_candidate_verification.py` (**NEW**) | `T1.2`, `T1.3` | Exact batch classification, 422/503 response and zero writes. |
| Site existence lookup and match check | `src/strategies/site.py`, `src/resources/site.yml`, `tests/strategies/test_site.py`, `tests/identity/test_reconciliation_contract_integration.py` (**NEW**); `schema/generated/site.sql` (verification only) | `T1.1`, `T1.2` | Real disposable-DB match and positive/negative existence tests. |
| Readiness API and tests | `src/api/model.py`, `src/api/router.py`, `tests/api/test_readiness.py` (**NEW**), `tests/identity/test_reconciliation_contract_integration.py` (**NEW**) | `T2.1` | Missing function yields reason without affecting manifest. |
| SIMS transaction rule and tests | `src/identity/repository.py`, `src/identity/service.py`, `src/api/identity_router.py` (only if needed), `tests/identity/test_repository.py`, `tests/identity/test_service.py`, `tests/identity/test_api.py`, `tests/identity/test_service_integration.py`, `tests/identity/test_reconciliation_contract_integration.py` (**NEW**) | `T3.1`, `T3.2` | Locking/race and state rejection proven with no unapproved-allocation regression. |
| OpenRefine compatibility | `src/reconcile.py`, `src/api/router.py`, `tests/test_reconcile.py`, `tests/api/test_router.py`, `tests/api/test_router_extended.py` | `T4.1` | Valid limit honored, unsupported type 4xx, formats retained. |
| Operating and testing guidance | `docs/OPERATIONS.md`, `docs/TESTING.md`, `docs/SIMS/DESIGN.md`, this task plan | `T4.2` | Contract and disposable-DB procedure match results; progress recorded. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Confirm match and verify candidates | Done | Existing strategy and helper-owned database | `V-1`–`V-3` pass, including a real match and no-write check against the bootstrapped disposable database. |
| Area 2: Report match readiness | Done | Area 1 match path | `V-3` and `V-4` pass, including missing-function behavior and the unchanged metadata endpoint. |
| Area 3: Enforce materialized binding | Done | Existing SIMS service, independent of Areas 1–2 | `V-5` and `V-6` pass; live state, replay, and row-lock checks passed after `bootstrap site`. |
| Area 4: Preserve OpenRefine and document | Done | Existing OpenRefine route; validate after Areas 1–3 | `T4.1`, `T4.2`, and `V-7`–`V-8` complete; guides and helper setup instructions are updated. |

## Definition Of Done

* [x] `PH4-AC-1` and `PH4-AC-2` have unit/API and disposable-database proof (`VM-8`; `V-1`–`V-3`), including one result per item, invalid/unsupported cases, 503, and no SIMS writes.
* [x] `PH4-AC-3` has missing-dependency and unchanged-metadata proof (`VM-9`; `V-3`, `V-4`).
* [x] `PH4-AC-4` has locked-transaction, live state-change, replay, existing-binding, and successful materialized proof (`VM-10`; `V-5`, `V-6`).
* [x] `PH4-AC-5` retains OpenRefine compatibility and honors limits (`VM-11`; `V-7`).
* [x] `AS-AC-6` is backed by the disposable-database tests in `VM-8`–`VM-10`; all deliverables, `V-8` checks, and related docs are complete.
* [x] No planned behavior is reported as shipped without corresponding test output. If the verified source or database differs materially from this plan, stop, record the discrepancy, and seek an explicit decision rather than broadening the work.

## Risks And Open Questions

* **Database readiness:** The SQL for `authority.fuzzy_site` is present in generated files, but the prior missing-function observation was environment-specific. A real match and a missing-function test on disposable databases settle whether deployment repair is needed; production changes are not authorized by this plan.
* **Existing SIMS state:** Previously approved IDs can be tracked but not `materialized`. The new rule will reject those bindings; the separate [existing-site adoption proposal](../SIMS_EXISTING_SITE_ADOPTION.md) is not part of this phase and does not block the candidate/readiness contract. End-to-end import remains dependent on adoption.
* **Time-of-check versus time-of-use:** A verified SEAD row can disappear later. Recheck when needed; SIMS binding enforces its own tracked-identity state, not SEAD row existence.
