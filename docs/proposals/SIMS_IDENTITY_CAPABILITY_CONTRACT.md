# Proposal: SIMS Identity Capability Contract

## Status

Implemented and disposable-validated (2026-10-03). Specifies the Phase 1 generic capability contract.

## Summary

Publish a versioned `GET /identity/capabilities` response that lists, for each configured entity type, the identity operations SIMS supports: binding an approved existing aggregate identity and allocating a new tracked aggregate. SIMS derives these capabilities from validated entity configuration, not from entity-specific code. `POST /identity/resolve` rejects unconfigured entity types and unsupported operations with a stable client error before writing any record.

SIMS owns tracked aggregate identities and is the sole minter of entity-scoped aggregate identity values and tracked UUIDs. A provider-supplied UUID is a source identity value; it never replaces a SIMS-minted identity. SIMS guarantees uniqueness only within its own identity store; SEAD consumes SIMS-issued values under the trust contract. Existing-data migration, production adoption, deployment validation, and cutover are separate operational work.

## Problem

The resolve endpoint derives entity behavior from an implicit default policy. Unlisted entity types receive the defaults rather than an explicit error, so a client cannot tell whether an operation is actually supported. There is no capability-discovery endpoint, so Shape Shifter cannot preflight its planned identity work before calling SIMS.

The current `identity_policy.yml` uses entity-specific `entity_subtype` and `allow_allocation` settings. These are legacy policy controls, not a validated capability contract. A generic mechanism must select behavior from explicit configuration, and a missing or invalid entry must fail rather than inherit a fallback that looks supported.

## Scope

- Define the versioned `GET /identity/capabilities` response contract.
- Define generic entity-scoped configuration for supported operations.
- Require an explicit configured operation on `POST /identity/resolve` before any write.
- Define stable client errors for unconfigured entity types and unsupported operations.

## Non-Goals

- Request-level idempotency (scoped run ID, payload fingerprint, replay storage). These belong to the batch contract and are required from the first batch version, but are not implemented here.
- Changing the `target_id` wire representation. It remains `int | null` and carries an opaque SIMS-issued aggregate identity value.
- Changing tracked-UUID semantics or the Binding Set model.
- Existing-data migration, production validation, deployment, and cutover.

## Proposed Design

### Entity configuration

Each entity entry in `identity_policy.yml` declares an `operations` mapping:

```yaml
entities:
  site:
    entity_subtype: shared_metadata
    accept_uuid: false
    auto_confirm: true
    operations:
      bind_existing: true   # Shape Shifter supplies an approved aggregate ID.
      allocate_new: true    # Shape Shifter approves a miss; SIMS mints a new identity.
```

`bind_existing` authorizes `approved_aggregate_id` binding. `allocate_new` authorizes minting a new tracked aggregate after a miss. A lookup-only entity sets `allocate_new: false`; a provider-owned aggregate root that is only ever allocated sets `bind_existing: false`. Relationship/child entities are not tracked in SIMS and set both to `false`.

### Capability discovery

`GET /identity/capabilities` returns:

```json
{
  "version": "1.0",
  "entities": [
    {
      "entity_type": "site",
      "entity_subtype": "shared_metadata",
      "bind_existing": true,
      "allocate_new": true,
      "auto_confirm": true,
      "accept_uuid": false
    }
  ]
}
```

Only explicitly configured entity types are listed. Unlisted types have no capabilities and are rejected by the resolve endpoint.

### Resolve authorization

Before creating a scope, submission, source identity, or tracked identity, the resolve endpoint infers the requested operation for each request:

- `bind_existing` when `approved_aggregate_id` is present;
- `allocate_new` otherwise.

It rejects the request with HTTP `422` when the entity type is unconfigured or the inferred operation is not enabled. A plain resolve on a lookup-only entity is rejected because Shape Shifter reconciles those entities and binds an approved existing identity instead.

### Source-key semantics

`primary_signal` and `additional_signals` are source identity keys. A provider-supplied UUID carried in a signal is a source identity value; it never replaces the SIMS-minted tracked UUID or aggregate identity value.

### Confirmation behavior

`auto_confirm` remains a per-entity configuration value reported in capabilities. It governs whether a Binding Set is confirmed at bind time or left proposed for manual review.

### Identity-value result

`ResolutionOutcome.aggregate_id` is serialized as `target_id`. The value is an opaque SIMS-issued, entity-scoped aggregate identity value; the field name is an adapter contract and does not imply SIMS knows a consumer table or column.

### Stable errors

- Unconfigured entity type → HTTP `422` with detail `Entity type '<type>' is not configured in SIMS`.
- Unsupported operation → HTTP `422` with detail `Operation '<op>' is not supported for entity type '<type>'`.

Missing or invalid configuration in `identity_policy.yml` raises at load time, so the service fails closed rather than serving partial capabilities.

## Risks And Tradeoffs

- `allow_allocation` remains a legacy runtime flag read by the binding path. `get_entity_policy` derives it from `operations.allocate_new` so the two cannot drift, but the legacy field is kept until the binding path is migrated to operation checks.
- `bind_existing: true` for shared-metadata entities is a forward-looking choice; only `site` binding is currently verified against a disposable database. Unverified operation claims are configuration, not deployment approval.
- Adding an entity type is configuration-only; it must not require a new allocator code path.

## Testing And Validation

- Policy tests confirm `operations` parsing, `supports`, `get_capabilities`, and validation errors for unknown keys and non-boolean values.
- API tests confirm the capability response version and content, and that unconfigured types and unsupported operations are rejected with HTTP `422` before any service call.
- `test_capabilities.py` ties the contract together: version constant, real-config capability listing, and rejection semantics.

## Acceptance Criteria

- `P-AC-1`: `GET /identity/capabilities` returns a versioned list of configured entity types with their supported operations, confirmation behavior, and key semantics.
- `P-AC-2`: Capability support is derived from validated configuration, not entity-specific code or an implicit default.
- `P-AC-3`: `POST /identity/resolve` rejects an unconfigured entity type with a stable client error before any write.
- `P-AC-4`: `POST /identity/resolve` rejects an unsupported operation with a stable client error before any write.
- `P-AC-5`: Missing or invalid configuration fails at load time rather than serving partial capabilities.

## Final Recommendation

Publish capabilities from validated entity configuration and enforce operation checks at the resolve endpoint before any write. Keep `target_id` as an opaque adapter carrier and keep existing-data migration and cutover outside this task.
