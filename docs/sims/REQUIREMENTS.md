# SEAD Identity System Requirements

## Purpose

> **Module location**: SIMS is implemented as the `src/identity/` module within the [`sead_authority_service`](https://github.com/humlab-sead/sead_authority_service) repository. There is no separate `sead_identity_system` deployment. See [docs/sims/README.md](./README.md) for full context.

This document states the initial functional requirements for the SEAD Identity System.

It is intentionally focused on:

- why the system exists,
- the domain concepts the system must understand,
- what the system must do (functional requirements),
- and how the system should surface to clients at a high level through an API.

### Out Of Scope For This Document

AI agents, take notice! The following are **out of scope** for this document, and should **not** be included in this document:

- implementation details,
- implementation plans,
- non-functional requirements (NFRs)
- deployment phases,
- infrastructure architecture,
- performance targets,
- authentication details,
- endpoint-level contracts or payload definitions,
- database migration steps,
- rollout plans,
- code-level hashing or serialization rules.

---

## Problem Statement

### Why the system exists

SEAD currently relies on sequence-generated integer primary keys as its internal identifiers. Those identifiers work well for internal relational integrity, but they are not sufficient as stable cross-system identities.

This creates several problems:

1. External systems cannot safely refer to SEAD entities before data is inserted.
2. The same incoming entity may be inserted multiple times because there is no stable identity handshake across submissions.
3. Update workflows are weak because the system cannot reliably distinguish a changed entity from a new one.
4. Remote systems are forced to depend on transient internal identifiers that are not appropriate as public references.
5. Shared metadata and classifiers risk duplication when reconciliation rules are weak or absent.

The SEAD Identity System exists to solve that class of problems by introducing a stable identity layer above SEAD's internal relational keys.

### Problem boundaries

The system is not intended to replace any part of SEAD's relational model. It exists to complement it.

The system must therefore support both of the following at the same time:

- SEAD continues using internal integer or bigint primary keys for relational storage.
- SEAD gains stable, externally usable identities for tracked entities.

---

## Scope And Goals

### Scope

The SEAD Identity System is concerned with identity management for tracked SEAD entities and with the mapping between the identity types defined in [Domain Concepts](#domain-concepts) below.

The system is also concerned with the relationship between provider-specific data and shared SEAD metadata, including reconciliation where those overlap.

### Goals

The system **must**:

1. Provide stable identities for tracked SEAD entities.
2. Preserve SEAD's existing relational primary keys.
3. Support idempotent identity allocation and resolution.
4. Support both UUID-based and business-key-based ingestion workflows.
5. Support reconciliation between provider data and shared SEAD metadata/classifiers.
6. Provide a foundation for later update and change-detection workflows.
7. Support entity relationships that are not limited to simple parent-child trees.

---

## Domain Concepts

### Core identity concepts

The system must distinguish the following concepts clearly.

#### SEAD internal identity

The current SEAD primary key used inside the relational schema.

Characteristics:

- entity-scoped,
- integer sequences, 
- relational,
- internal to SEAD,
- should **not** be exposed as a public identity.
- represented in SEAD as `{entity}_id` where applicable.

#### SEAD universal identity

The stable UUID used to identify **a tracked SEAD entity** across system boundaries.

Characteristics:

- globally scoped,
- externally usable,
- stable across submissions,
- represented in SEAD as `{entity}_uuid` where applicable.

#### Business key

A natural key or key set that uniquely identifies an entity in practice.

Characteristics:

- defined per entity type,
- used primarily for reconciliation,
- may come from SEAD conventions or provider data,
- may or may not be globally stable.

#### Provider key

An identifier used by a remote data provider.

Characteristics:

- may be a UUID,
- may be a business key,
- may be internal to the provider,
- should generally be retained in the identity system even when not promoted into SEAD tables.

#### Authority key

An identifier from an external authority or reference system, such as Wikidata, GeoNames, or a domain ontology.

Characteristics:

- useful for reconciliation,
- useful for de-duplication of shared metadata,
- not always available from providers,
- may become strategically important for shared SEAD entities.

### Entity and value object distinction

This document uses domain-driven design (DDD) concepts as defined in [CONCEPTUAL_MODEL.md § Domain Modeling Foundations](./CONCEPTUAL_MODEL.md#domain-modeling-foundations): **entity**, **value object**, and **aggregate**.

**A tracked entity** is an entity for which this system manages stable UUID identity. Not every domain object needs to be tracked. Determining which SEAD objects qualify as tracked entities is a SEAD domain-modeling task, deferred to SEAD model specification work. That work may draw on Shape Shifter's target model conformance definitions as an input.

### Entity subtypes

Within tracked entities, this document recognizes three identity patterns.

#### Provider-owned entities

Entities whose data originates from a submitting provider and is treated as provider-owned content. Identity is allocated based on incoming evidence. Reconciliation against shared SEAD structures is not the primary concern.

In Shape Shifter terms, these correspond broadly to **fact** entities.

#### Shared metadata entities

Entities that function as shared reference structures used across datasets and multiple providers. These must be reconciled against existing SEAD definitions rather than simply allocated a new identity. Insertion without reconciliation risks duplication.

In Shape Shifter terms, these correspond broadly to **classifier** and **lookup** entities.

#### Relationship entities

Some many-to-many associations are represented as bridge records. In most cases a bridge record is a value object owned by an aggregate. Where a bridge record carries its own attributes or lifetime that require independent tracking, it may qualify as a tracked entity.

In Shape Shifter terms, these correspond to **bridge** entities.

### Value objects and owned child structures

Value objects belong to an owning entity and are managed as part of that entity's aggregate state. They do not receive stable identity and cannot be independently referenced or reconciled.

### Relationship types

The domain model must support more than one relationship type.

#### Ownership

The child is part of the aggregate state of a parent entity.

#### Association

Two entities are linked, but one does not own the identity of the other.

This is important for relationships such as site-to-location where the schema expresses association rather than strict containment.

#### Reconciliation linkage

A provider object or classifier is matched to an existing SEAD object without implying ownership.

### Conceptual model alignment

The domain concepts above are elaborated in [CONCEPTUAL_MODEL.md](./CONCEPTUAL_MODEL.md), which defines the full conceptual model for SIMS. The following CM concepts are relevant to how these requirements are realized:

- **Source Scope**: the external namespace (system, provider, dataset) within which source identifiers are unique and interpretable. This is the identity context implied by "identity scope" in FR-13 and "submission context" in the API concepts.
- **Binding**: the explicit, governed correspondence between a source-side identity and a SEAD-side tracked identity. Bindings are the decision objects that record the outcome of identity resolution (FR-12, FR-14) and support traceability (FR-22, FR-23).
- **Change Request**: the governed package of proposed domain changes created after identity resolution. This is the mechanism through which identity decisions are separated from business-data mutation (FR-25) and supports update workflows (FR-24).
- **Identity Resolution**: the process that evaluates identity evidence and determines whether to reuse an existing tracked identity, allocate a new one, or leave the case unresolved. This process implements the resolution and allocation logic required by FR-6 through FR-11.

See [CONCEPTUAL_MODEL.md § Core Concepts](./CONCEPTUAL_MODEL.md#core-concepts) for full definitions, relations, and lifecycle semantics.

---

## Functional Requirements

### Identity model requirements

FR-1. The system shall maintain a stable UUID identity for each tracked SEAD entity.

FR-2. The system shall maintain a mapping between the tracked entity UUID and the corresponding SEAD internal identifier.

FR-3. The system shall support reuse of existing `{entity}_uuid` fields in SEAD where such fields already exist.

FR-4. The system shall not require replacement of SEAD internal integer or bigint primary keys.

FR-5. The system shall distinguish between SEAD universal identity, SEAD internal identity, business keys, provider keys, and authority keys.

### Identifier intake requirements

FR-6. The system shall accept provider-supplied UUIDs for tracked entities when allowed by SEAD identity policy.

FR-7. The system shall mint a new SEAD UUID for a tracked entity when no accepted UUID is supplied.

FR-8. The system shall support business-key-based resolution for entities where business keys are defined.

FR-9. The system shall retain provider keys in the identity system even when those keys are not written into SEAD tables.

FR-10. The system shall support recording authority keys for tracked entities when such identifiers are available.

FR-11. The system shall enforce an administrable identity policy that governs whether a provider-supplied UUID is accepted as the SEAD universal identity or treated only as a provider key.

### Idempotency and mapping requirements

FR-12. The system shall return the same resolved SEAD identity for the same accepted identifier across repeated submissions.

FR-13. The system shall prevent duplicate identity allocation for the same accepted identifier within the same identity scope.

FR-14. The system shall support stable lookup of existing mappings between provider identifiers, business keys, authority keys, UUID identity, and SEAD internal identity.

### Domain modeling requirements

FR-15. The system shall support tracked entities that are provider-owned data.

FR-16. The system shall support tracked entities that are shared metadata.

FR-17. The system shall support reconciliation of shared metadata and classifiers rather than only raw insertion.

FR-18. The system shall support many-to-many associations between tracked entities.

FR-19. The system shall distinguish owned child value objects from independently tracked entities.

FR-20. The system shall surface unresolved reconciliation state when an incoming shared metadata or classifier entity cannot be matched to an existing SEAD entity, rather than silently allocating a new identity.

### Submission and traceability requirements

FR-21. The system shall group related identity actions under a submission concept.

FR-22. The system shall preserve enough submission context to support auditing and traceability.

FR-23. The system shall preserve the relationship between a submission, the identifiers provided, and the resulting resolved or minted identities.

### Update-foundation requirements

FR-24. The system shall maintain identity state sufficient for aggregate-level change detection and update workflows without requiring structural redesign of the identity model.

FR-25. The system shall keep identity allocation logic independent of business-data mutation logic.

---

## Usage Scenarios

> **Cross-reference**: [CONCEPTUAL_MODEL.md § Canonical Use Cases](./CONCEPTUAL_MODEL.md#canonical-use-cases) provides identity-centered use cases that complement these requirements-level scenarios. The mapping is:
>
> | REQ scenario | CM use case(s) |
> |---|---|
> | Scenario 1 (provider submits entity data) | UC 2 (new source identity matched to existing tracked identity), UC 3 (new source identity requiring new tracked identity) |
> | Scenario 2 (classifier reconciliation) | UC 2 (matched to existing tracked identity), plus unresolved case handling ([CM deferred issue 2](./CONCEPTUAL_MODEL.md#deferred-issues)) |
> | Scenario 3 (association, not ownership) | Not identity-specific; modeled through CM relations (independent tracked identities with separate bindings) |
> | Scenario 4 (authority-backed reconciliation) | UC 2 (matched via authority key as identity signal) |
> | — | UC 1 (existing source identity with existing binding) — covers repeat submissions, not explicitly a REQ scenario |
> | — | UC 4 (confirmed binding later corrected) — covers error correction, not explicitly a REQ scenario |
> | — | UC 5 (change request rejected) — covers governance outcomes, not explicitly a REQ scenario |

### Scenario 1: Provider submits entity data

A provider submits entities, either with provider-generated UUIDs or using business keys only.

Expected outcome:

- Where UUIDs are supplied, the system determines whether they are accepted as SEAD universal identities per the configured identity policy.
- Where only business keys are supplied, the system uses defined business-key rules to resolve or identify the entity.
- In both cases, existing identities are resolved where found; new SEAD UUIDs are minted where not.
- Provider keys are retained in the identity system regardless of whether they are accepted as SEAD identities.

### Scenario 2: Provider submits classifiers that should reconcile to shared SEAD metadata

A provider submits values for methods, sample types, bibliographic references, taxa-related structures, or other classifiers.

Expected outcome:

- the system does not treat those values as provider-owned entities by default,
- instead it attempts reconciliation against shared SEAD metadata,
- if matched, the shared SEAD entity is reused,
- if not matched, the system surfaces that unresolved state for later handling according to SEAD policy.

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
- the system can retain both SEAD identity and external authoritative identity without conflating them.

---

## High Level API Behaviour

The API exposes the identity system as a service. Clients present identity evidence, request resolution or allocation within a submission context, and receive stable identity results. Endpoint design belongs in a later API specification.

### API-visible concepts

At a high level, the API should expose behavior around:

- tracked entity types,
- submission contexts,
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
