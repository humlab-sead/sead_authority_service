# SEAD Identity System Requirements

> **Status:** Reflects the implementation as of Phases 1–2 (complete). Generic configurable aggregate-identity allocation is the target design and is not yet implemented. Existing-data migration, production adoption, and cutover are outside the current development task. See [OPERATIONS.md](./OPERATIONS.md) for deployment and [src/identity/README.md](../../src/identity/README.md) for the module entry point.

## Purpose

> **Module location**: SIMS is implemented as the `src/identity/` module within the [`sead_authority_service`](https://github.com/humlab-sead/sead_authority_service) repository. There is no separate `sead_identity_system` deployment. See [docs/SIMS/README.md](./README.md) for full context.

This document states the initial functional requirements for the SEAD Identity System.

It is intentionally focused on:

- why the system exists,
- the domain concepts the system must understand,
- what the system must do (functional requirements),
- and how the system should surface to clients at a high level through an API.

### Out Of Scope For This Document

This document covers requirements only. Implementation details, NFRs, infrastructure, deployment, authentication, endpoint contracts, and rollout plans belong in separate documents.

---

## Problem Statement

### Why the system exists

Tracked aggregates need stable identities that remain consistent across submissions and consumers. A consuming system may also use local relational keys, but those storage details do not define SIMS identity.

This creates several problems:

1. External systems cannot safely refer to tracked aggregates before the consumer materializes their data.
2. The same incoming entity may be inserted multiple times because there is no stable identity handshake across submissions.
3. Update workflows are weak because the system cannot reliably distinguish a changed entity from a new one.
4. Remote systems may be forced to depend on storage identifiers whose meaning is local to one consumer.
5. Shared metadata and classifiers risk duplication when reconciliation rules are weak or absent.

SIMS solves these problems by owning stable aggregate identities and the source identities associated with them.

### Problem boundaries

SIMS owns identity for tracked aggregates; it does not own a consumer's data model or storage schema.

The SIMS–SEAD trust contract requires:

- SIMS is the sole minter of tracked aggregate identities and guarantees uniqueness within its own identity store.
- Every tracked entity represented in SEAD has a corresponding SIMS Tracked Identity. SEAD consumes SIMS-issued identity values under the trust contract.
- SIMS does not map identity values to SEAD tables or columns and does not enforce SEAD database integrity.

---

## Scope And Goals

### Scope

SIMS manages tracked aggregate identities, entity-scoped identity values, and the source identities associated with those aggregates. It uses a generic allocation mechanism configured by entity type; supporting another configured type must not require a dedicated allocator implementation.

SIMS stores source identities and their associations with tracked aggregates. A consuming workflow owns reconciliation against its own domain data and submits approved identity outcomes to SIMS; SIMS does not inspect SEAD definitions or schemas.

### Goals

The system **must**:

1. Provide stable identities for tracked aggregates.
2. Keep SIMS identity ownership separate from a consumer's local storage keys.
3. Support idempotent identity allocation and resolution.
4. Support both UUID-based and business-key-based ingestion workflows.
5. Support identity resolution using source identities and approved caller decisions without performing target-system reconciliation.
6. Provide a foundation for later update and change-detection workflows.
7. Support entity relationships that are not limited to simple parent-child trees.

---

## Domain Concepts

### Core identity concepts

The system must distinguish the following identifier types.

| Type | Definition | Scope |
|---|---|---|
| **Aggregate identity value** | Opaque value minted and stored by SIMS for a tracked aggregate | Entity-type scoped |
| **Tracked UUID** | Stable UUID assigned and stored by SIMS for a tracked aggregate | Global |
| **Business key** | Natural key or key set identifying an entity in practice | Source scope or entity configuration |
| **Provider key** | Identifier used by a data provider | Provider/source scope |
| **Authority key** | Identifier from an external reference system (e.g. Wikidata, GeoNames) | External authority |

### Tracked entities

A **tracked entity** is an entity or aggregate root for which SIMS manages a stable identity. Value objects and storage-only rows are not independently tracked unless the domain model defines them as aggregates. This document uses the domain-driven design vocabulary defined in [CONCEPTUAL_MODEL.md § Domain Modeling Foundations](./CONCEPTUAL_MODEL.md#domain-modeling-foundations).

### Entity subtypes

Within tracked entities, this document recognizes three identity patterns.

#### Provider-owned entities

Entities whose data originates from a submitting provider and is treated as provider-owned content. Identity is allocated based on incoming source identities and validated SIMS configuration.

In Shape Shifter terms, these correspond broadly to **fact** entities.

#### Shared metadata entities

Entities that function as shared reference structures used across datasets and providers. The consuming workflow reconciles these entities against its domain data and submits an approved match or permitted allocation request to SIMS. SIMS does not search or inspect the consumer's database.

In Shape Shifter terms, these correspond broadly to **classifier** and **lookup** entities.

#### Relationship entities

Some many-to-many associations are represented as bridge records. In most cases a bridge record is a value object owned by an aggregate. Where a bridge record carries its own attributes or lifetime that require independent tracking, it may qualify as a tracked entity.

In Shape Shifter terms, these correspond to **bridge** entities.

### Relationship types

The domain model must support:

- **Ownership**: the child is part of the aggregate state of a parent entity.
- **Association**: two entities are linked without ownership (e.g. site-to-location).
- **Reconciliation linkage**: a provider object or classifier is matched to an existing consumer-domain object without implying ownership. The consuming workflow owns that matching process.

### Conceptual model alignment

The full conceptual model — core concepts (Source Scope, Submission, Source Identity, Tracked Identity, Binding, Binding Set, Identity Resolution, Change Request), relations, lifecycles, and canonical use cases — is defined in [CONCEPTUAL_MODEL.md](./CONCEPTUAL_MODEL.md).

---

## Functional Requirements

### Identity model requirements

FR-1. The system shall maintain a stable tracked UUID for each tracked aggregate.

FR-2. The system shall store an entity-scoped aggregate identity value with the tracked UUID and entity type.

FR-3. The system shall expose SIMS-issued identity values without requiring knowledge of a consumer's table or column names.

FR-4. The system shall guarantee uniqueness of aggregate identity values within the SIMS identity store and shall not claim to enforce uniqueness in a consumer database.

FR-5. The system shall distinguish aggregate identity values, tracked UUIDs, business keys, provider keys, and authority keys.

### Identifier intake requirements

FR-6. The system shall accept provider-supplied identifiers as Source Identity values when allowed by SIMS entity configuration; it shall not adopt a provider-supplied value as a SIMS-minted aggregate identity or tracked UUID.

FR-7. The system shall mint new aggregate identity values and tracked UUIDs through a generic allocator when allocation is configured.

FR-8. The system shall support business-key-based resolution for entities where business keys are defined.

FR-9. The system shall retain provider keys in the identity system independently of whether a consuming system stores those keys.

FR-10. The system shall support recording authority keys for tracked entities when such identifiers are available.

FR-11. The system shall enforce validated entity configuration that governs accepted source-key semantics and the generic identity operation.

### Idempotency and mapping requirements

FR-12. The system shall return the same SIMS tracked identity for the same accepted source identity across repeated submissions.

FR-13. The system shall prevent duplicate identity allocation for the same accepted identifier within the same source scope.

FR-14. The system shall support stable lookup of SIMS mappings between source identities, aggregate identity values, and tracked UUIDs.

### Domain modeling requirements

FR-15. The system shall support tracked entities that are provider-owned data.

FR-16. The system shall support tracked entities that are shared metadata.

FR-17. The system shall support binding an approved existing Tracked Identity and shall not perform reconciliation against a consumer's domain database.

FR-18. The system shall support many-to-many associations between tracked entities.

FR-19. The system shall distinguish owned child value objects from independently tracked entities.

FR-20. The system shall reject a request with diagnostic information when the configured operation forbids allocation and the caller has not supplied an approved existing identity.

### Submission and traceability requirements

FR-21. The system shall group related identity actions under a submission concept.

FR-22. The system shall preserve enough submission context to support auditing and traceability.

FR-23. The system shall preserve the relationship between a submission, the identifiers provided, and the resulting resolved or minted identities.

### Update-foundation requirements

FR-24. The system shall maintain identity state sufficient for aggregate-level change detection and update workflows without requiring structural redesign of the identity model.

FR-25. The system shall keep identity allocation logic independent of business-data mutation logic.

### Binding set requirements

FR-26. The system shall group the Bindings produced by an identity resolution batch into a Binding Set that is confirmed or rejected as an atomic unit.

### Change Request completeness requirements

FR-27. The system shall expose Binding Set confirmation state so a consuming workflow can check identity outcomes before applying its own domain changes. SIMS shall not apply or validate those changes.

FR-28. The system shall allocate and persist an aggregate identity value and tracked UUID for each configured new tracked identity before returning a successful allocation result.

FR-29. The system shall allocate aggregate identity values from SIMS-owned state and shall not inspect or depend on consumer tables, columns, sequences, or database constraints.

FR-30. The generic allocator shall use validated entity-scoped configuration, reject conflicting identities within SIMS, and never recycle an allocated aggregate identity value.

---

## Usage Scenarios

The scenarios below describe requirements-level situations. [CONCEPTUAL_MODEL.md § Canonical Use Cases](./CONCEPTUAL_MODEL.md#canonical-use-cases) provides corresponding identity-centered use cases.

### Scenario 1: Provider submits entity data

A provider submits entities, either with provider-generated UUIDs or using business keys only.

Expected outcome:

- Where UUIDs are supplied, the system records them as scoped Source Identity values according to validated entity configuration.
- Where only business keys are supplied, the system uses defined business-key rules to resolve or identify the entity.
- In both cases, existing SIMS identities are reused where a Source Identity is already bound; new SIMS aggregate identity values and tracked UUIDs are minted where allocation is configured.
- Provider UUIDs remain distinct Source Identity values and never replace a SIMS-minted tracked UUID.

### Scenario 2: Provider submits entities governed by a shared-metadata policy

A provider submits values for methods, sample types, bibliographic references, taxa-related structures, or other classifiers.

Expected outcome:

- the system does not treat those values as provider-owned entities by default,
- instead it applies the configured resolution policy for shared metadata,
- if matched, the existing SIMS Tracked Identity is reused,
- if not matched and allocation is disallowed, the system rejects the request with diagnostic information.

### Scenario 3: Entity association rather than ownership

Two independently tracked entities are linked, such as site and location.

Expected outcome:

- both retain their own identity,
- the relationship is modeled as an association,
- neither entity is forced into an incorrect ownership hierarchy purely for identity allocation convenience.

### Scenario 4: Authority-backed reconciliation

A provider or curator supplies an authority identifier, such as a GeoNames or Wikidata identifier.

Expected outcome:

- the authority key can be attached to a tracked entity,
- the authority key can support reconciliation,
- the system can retain both SIMS aggregate identity and external authoritative identity without conflating them.

---

## High Level API Behaviour

The API exposes the identity system as a service. Clients present identity evidence, request resolution or allocation within a source scope, and receive stable identity results. Endpoint design belongs in a later API specification.

### API-visible concepts

At a high level, the API should expose behavior around:

- tracked entity types,
- source scopes and submissions,
- identity evidence,
- resolved identity,
- minted identity,
- reconciliation result,
- association handling,
- traceability of identity decisions.

### API non-goals at this stage

This requirements document does not yet define:

- endpoint names,
- request schemas,
- response schemas,
- authentication strategy,
- pagination,
- error code catalog,
- transactional guarantees at protocol level.

Those belong to a later API specification once the domain model has stabilized.
