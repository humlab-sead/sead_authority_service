# Verify Reconciliation Candidates and Match Readiness

## Status

- Proposed change request — draft for review, revised after the [Shape Shifter reconciliation review](https://github.com/humlab-sead/sead_shape_shifter/blob/main/docs/proposals/RECONCILIATION_MVP/RECONCILIATION_MVP_REVIEW.md)
- Scope: Authority Service contracts for read-only checking of reconciliation candidates, database-backed match readiness, and a SIMS state rule for approved IDs.
- Goal: Let a consumer check that a candidate identifies an existing SEAD row before it commits a link, without creating any binding during review.

## Summary

This proposal is the **single normative definition** of the candidate check. The companion [Shape Shifter proposal](https://github.com/humlab-sead/sead_shape_shifter/blob/main/docs/proposals/RECONCILIATION_MVP/RECONCILIATION_MVP.md) links here and does not restate these rules.

Add a read-only operation next to `/reconcile` that accepts a batch of OpenRefine candidates (candidate `id` plus the strategy that produced it), validates the candidate URI itself, and reports whether the SEAD row exists. The service returns the canonical `(entity_type, aggregate_id)` so the consumer does no URI parsing. Add a type-specific readiness check that exercises the database-backed match path. Separately, make SIMS reject non-`materialized` identities when it resolves and binds an approved ID.

The candidate check does not look at SIMS. Existing SEAD rows are not adopted into SIMS and no adoption work is planned, so a SIMS-gated check would reject every candidate. SIMS keeps enforcing its own rules at binding time.

## Problem

An OpenRefine candidate is a search suggestion. Its `match` flag reflects search similarity, and its `id` is a URI whose integer suffix a consumer cannot safely extract: a wrong origin, type path, or malformed value would pass a bare `/(\d+)/?$` match. The current manifest can advertise an entity type even when its database-backed match route fails. A consumer has no read-only way to learn whether a candidate's SEAD row exists.

Separately, SIMS rejects an `approved_aggregate_id` with no tracked identity but does not reject one whose lifecycle state is `invalidated`. `POST /identity/resolve` also creates or reuses source identities, a submission, and a Binding Set, so it cannot be used as a review-time lookup.

## Scope

- A read-only, batch candidate check for the entity types in the reconciliation MVP (`site` first).
- Candidate URI validation inside the service, with a closed set of outcome codes.
- A database-backed readiness check per reconciliation type.
- A SIMS rule: approved-ID resolution and binding require a `materialized` identity.
- Small OpenRefine compatibility fixes, kept as a separate item (see below).

## Non-Goals

- Review, approval, or persistence of Shape Shifter decisions.
- Binding, allocating, or writing identities during candidate checks, or replacing `POST /identity/resolve`.
- Checking SIMS state or `bind_existing` capability in the candidate check.
- Making SIMS inspect SEAD tables.
- Adopting existing SEAD rows into SIMS. That is separate operational work with no owner yet, described in [SIMS target ID contract](../SIMS_TARGET_ID_CONTRACT/SIMS_TARGET_ID_CONTRACT.md).
- Supporting every advertised reconciliation strategy in the first MVP.

## Current Behavior

- `GET /reconcile` serves OpenRefine metadata and `POST /reconcile` returns candidates from registered strategies ([API](../../../src/api/router.py#L58), [matching](../../../src/reconcile.py#L9)). A candidate's `match` flag is based on search similarity ([strategy](../../../src/strategies/strategy.py#L79)).
- A candidate `id` is built from the configured `id_base`, the strategy type path, and the aggregate ID. A missing `id_base` yields a relative `id` because it is resolved with `or ""` ([strategy](../../../src/strategies/strategy.py#L71)).
- `GET /identity/capabilities` lists operations per entity type. `POST /identity/resolve` checks an approved ID against SIMS and creates binding records ([identity API](../../../src/api/identity_router.py#L132), [identity service](../../../src/identity/service.py#L194)).
- SIMS tracks `allocated`, `pending_materialization`, `materialized`, and `invalidated` states. Aggregate-ID lookup and approved-ID resolution do not filter by state ([states](../../../src/identity/types.py#L19), [lookup](../../../src/identity/repository.py#L373)).
- The configured default query limit overrides the per-query `limit`, and an unknown type becomes HTTP 500 after validation ([matching](../../../src/reconcile.py#L11), [API](../../../src/api/router.py#L226)).
- In the assessed local environment, `GET /reconcile` listed 13 types but a real `site` match failed with HTTP 500 because `authority.fuzzy_site` was missing. This is a local observation, not a claim about all deployments.

## Proposed Design

### Read-only candidate check

Add `POST /reconcile/verify-candidates`. The consumer sends each candidate `id` exactly as returned by `POST /reconcile`, with the reconciliation type that produced it, and no parsed or typed values.

Request:

```json
{"items": [{"type": "site", "id": "<candidate id>"}]}
```

A request holds 1 to 100 items. A consumer with more candidates sends several requests.

For each item the service:

1. Validates the `id`: an absolute URI with the configured origin and `id_base`, exactly one type path that matches `type`, one positive decimal aggregate ID, and no query or fragment.
2. Maps `type` to its SEAD entity type, for supported types only.
3. Checks that the SEAD row exists.

Response: one result per item, in request order, each echoing the input `type` and `id`:

```json
{"results": [{"type": "site", "id": "<candidate id>", "outcome": "exists", "entity_type": "site", "aggregate_id": 123}]}
```

`entity_type` and `aggregate_id` appear only when the outcome is `exists`. The outcome is one of a closed set:

| Outcome | Meaning |
|---|---|
| `exists` | Valid candidate; the SEAD row exists. |
| `not_found` | Valid candidate; no SEAD row. |
| `invalid_candidate` | Wrong origin, type path, shape, or a `type` mismatch. |
| `unsupported_type` | The `type` is not a configured reconciliation type, or the identity policy does not enable `bind_existing` for it. |

Status codes:

| Status | When |
|---|---|
| 200 | The batch was processed. Per-item problems are outcomes, not errors. |
| 422 | The request is malformed, empty, or has more than 100 items. |
| 503 | The SEAD database is unavailable. No partial results are returned, and the failure is never reported as `exists` or `not_found`. |

The check performs no writes: no identities, submissions, or Binding Sets. It does not use the candidate's score or `match` flag. Access: the new endpoints add no authentication. Neither `/reconcile` nor `/identity` has application-level authentication today, so access is controlled by the deployment network, as for the existing endpoints. The type gate above limits what the check reports, and the response contains only the fields above.

A consumer that needs the result at the moment of use must call the check again; a result is not a lasting guarantee.

### Readiness

Add `GET /reconcile/readiness?type=<type>`. It runs the configured strategy's database-backed match path with a minimal query. The response is `{"type": "site", "ready": true, "reason": null}`, or `ready: false` with a `reason` such as a missing schema function or a missing `id_base`; both are HTTP 200. An unknown type is HTTP 422. `GET /reconcile` remains OpenRefine metadata and does not claim readiness.

### SIMS state rule for approved IDs

`POST /identity/resolve` must reject an approved aggregate ID whose identity is not `materialized`, including when the ID is reached through an existing confirmed binding. The state is checked inside the same database transaction that creates or reuses the binding (for example with a row lock on the identity), so a state change between lookup and binding cannot slip through. This change is independent of the candidate check and can ship separately. It does not make SIMS query SEAD.

### Independent OpenRefine fixes

Kept as a separate low-risk item that does not gate the contract above:

- Honor the validated per-query `limit`.
- Return a client error (4xx) for an unsupported type instead of HTTP 500.

Existing form-encoded and JSON query formats and the response shape do not change.

## Alternatives Considered

- **Use `POST /identity/resolve` as a review-time lookup:** Rejected; it writes identity and binding state.
- **Trust the candidate URI or `match` flag:** Rejected; neither shows that the SEAD row exists.
- **Check SIMS `materialized` state in the candidate check:** Deferred; with no planned adoption of existing rows, all candidates would be rejected. The SIMS state rule at binding still applies.
- **Consumer parses the URI and sends a typed pair:** Rejected; it copies URI and type rules into every consumer. The service owns the format.
- **Place the endpoint under `/identity/*`:** Rejected; the check is read-only and carries no binding meaning, so it sits beside `/reconcile`.
- **Rely on the manifest as a readiness check:** Rejected; the manifest succeeded while `site` matching failed.

## Risks And Tradeoffs

- A SEAD row can be removed after a check. The consumer must repeat the check when it matters; SIMS cannot detect this.
- Row existence depends on the strategy's backing data. Adding a type needs an explicit strategy-to-entity mapping.
- A read-only lookup reveals whether an ID exists. The batch limit, the type gate, and the minimal response limit this. The endpoints have the same exposure as `/reconcile`; the service has no application-level authentication, and `main.py` allows all CORS origins. Neither is changed here.
- Rejecting non-`materialized` identities at binding can exclude IDs accepted before. Review existing data before enabling the rule.
- Without adoption of existing SEAD rows into SIMS, change requests that bind existing `site` IDs fail at SIMS even when the candidate check passes. This proposal does not fix that.

## Testing And Validation

Use unit and API tests for outcome classification, URI validation (wrong origin, type, path, query, fragment, malformed ID), unsupported types, database outage, absence of writes, per-query limit, and OpenRefine compatibility. In a disposable environment with SEAD and SIMS data, verify an existing `site`, a missing row, a wrong-type candidate, a missing `id_base`, and a missing database function for readiness. Separately test that `POST /identity/resolve` binds a `materialized` identity, rejects each non-`materialized` state including through an existing binding, and rejects a state change made between lookup and binding.

## Acceptance Criteria

- `AS-AC-1` One batch request returns one ordered result per candidate, with an outcome from the closed set, and `exists` only when the candidate URI is valid and the SEAD row exists. A type without `bind_existing` in the identity policy returns `unsupported_type`.
- `AS-AC-2` The service rejects wrong-origin, wrong-type, malformed, query-or-fragment, and strategy-mismatch candidates as `invalid_candidate` without a lookup, and returns the canonical `entity_type` and `aggregate_id` for valid ones.
- `AS-AC-3` A SEAD database failure fails the operation instead of returning `exists` or `not_found`. The check performs no identity or binding writes.
- `AS-AC-4` `GET /reconcile/readiness` fails with a reason when a required match dependency is missing for the type, while `GET /reconcile` keeps serving metadata.
- `AS-AC-5` `POST /identity/resolve` rejects non-`materialized` approved identities, including through an existing binding, and checks state in the same transaction as the binding.
- `AS-AC-6` Disposable database-backed tests for `site` cover the check, readiness, and approved binding, including absent-row, mismatch, invalid-state, and state-change cases.
- `AS-AC-7` (independent item) A validated per-query `limit` is honored and an unsupported type returns a client error, with existing request and response formats unchanged.

## Planning Handoff

**Confirmed decisions**

- Pilot type is `site`; its SEAD row lookup is the strategy's backing data.
- The candidate check covers SEAD row existence only. The service parses and validates the candidate URI and returns the canonical type and ID.
- Endpoints add no authentication and serve only types that are configured reconciliation types and enable `bind_existing` in the identity policy.
- Endpoints sit next to `/reconcile`: `POST /reconcile/verify-candidates` and `GET /reconcile/readiness`. Request and response formats, status codes, and the batch limit of 100 items are fixed in Proposed Design.
- This proposal is the normative contract; Shape Shifter links here. Criteria use the `AS-AC-` prefix, and Shape Shifter uses `SS-AC-`.
- The SIMS state rule and the OpenRefine fixes are independent items and can ship in any order.

**Preserve**

- SIMS does not query SEAD, and the OpenRefine response shape does not change.
- Candidate checking never writes; resolve-and-bind remains the only binding path.

**Phase ordering**

- Readiness and the candidate check first, because Shape Shifter's export phase depends on them.
- The SIMS state rule and OpenRefine fixes follow independently.

**Validation**

- Run the database-backed match path and the candidate check together against a disposable database, not manifest checks or mocks alone.

## Open Questions

- **Existing-data adoption into SIMS for `site`:** Tracked in [Adopt Existing `site` Rows into SIMS as `materialized`](../SIMS_EXISTING_SITE_ADOPTION.md). It does not block the candidate check but blocks binding existing `site` IDs through SIMS. Its owner must be named before end-to-end import is validated.

## Final Recommendation

Add a read-only candidate check that owns URI validation and SEAD row existence, a real match-readiness check, and a `materialized` rule at SIMS binding. Leave operator approval to Shape Shifter and binding to SIMS.
