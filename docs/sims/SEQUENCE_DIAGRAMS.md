# SIMS Sequence Diagrams

Sequence diagrams covering the core SIMS workflows. See [DESIGN_VIEW.md](./DESIGN_VIEW.md) for the decision flow and [IMPLEMENTATION_VIEW.md](./IMPLEMENTATION_VIEW.md) for structural details.

---

## 1. Submission Setup

Establishes the Source Scope and Submission before any identity resolution begins. This is typically called once per ingest event.

```mermaid
sequenceDiagram
    participant Client
    participant IdentityService
    participant SourceScopeRepository
    participant SubmissionRepository

    Client->>IdentityService: get_or_create_scope(scope_name)
    IdentityService->>SourceScopeRepository: get_by_name(scope_name)
    SourceScopeRepository-->>IdentityService: None (not found)
    IdentityService->>SourceScopeRepository: create(scope_name)
    SourceScopeRepository-->>IdentityService: SourceScope(scope_uuid)
    IdentityService-->>Client: SourceScope

    Client->>IdentityService: create_submission(scope_uuid, submission_name)
    IdentityService->>SubmissionRepository: create(scope_uuid, submission_name)
    SubmissionRepository-->>IdentityService: Submission(submission_uuid, status=pending)
    IdentityService-->>Client: Submission
```

---

## 2. Provider-Owned Entity — First Submission (New Identity)

A provider-owned entity (e.g. `site`) arrives with no prior record in SIMS. The system mints a new Tracked Identity and auto-confirms the Binding Set because the entity policy permits allocation and auto-confirmation.

```mermaid
sequenceDiagram
    participant Client
    participant IdentityService
    participant IdentityPolicy
    participant SourceIdentityRepository
    participant BindingRepository
    participant BindingSetRepository
    participant TrackedIdentityRepository

    Note over Client,TrackedIdentityRepository: Step 1 — Resolve Identity

    Client->>IdentityService: resolve_identity(scope_uuid, ResolutionRequest{entity_type, primary_signal})
    IdentityService->>IdentityPolicy: get_entity_policy(entity_type)
    IdentityPolicy-->>IdentityService: EntityPolicy{allow_allocation=true, auto_confirm=true}

    IdentityService->>SourceIdentityRepository: create_or_get(scope_uuid, entity_type, keys)
    Note right of SourceIdentityRepository: Idempotent upsert — no match found
    SourceIdentityRepository-->>IdentityService: SourceIdentity(source_identity_uuid) [new]

    IdentityService->>SourceIdentityRepository: link_to_submission(submission_uuid, source_identity_uuid)

    IdentityService->>BindingRepository: find_confirmed_binding(source_identity_uuid)
    BindingRepository-->>IdentityService: None

    IdentityService-->>Client: ResolutionOutcome{outcome=new, tracked_identity_uuid=None}

    Note over Client,TrackedIdentityRepository: Step 2 — Bind

    Client->>IdentityService: bind(submission_uuid, [outcome])
    IdentityService->>BindingSetRepository: create(submission_uuid)
    BindingSetRepository-->>IdentityService: BindingSet(state=proposed)

    IdentityService->>IdentityPolicy: get_entity_policy(entity_type) → allow_allocation=true
    IdentityService->>TrackedIdentityRepository: mint(entity_type)
    TrackedIdentityRepository-->>IdentityService: TrackedIdentity(tracked_identity_uuid, state=allocated)

    IdentityService->>BindingRepository: create(binding_set_uuid, source_identity_uuid, tracked_identity_uuid, method=allocated)
    BindingRepository-->>IdentityService: Binding

    Note over IdentityService,BindingSetRepository: All entity types have auto_confirm=true → auto-confirm
    IdentityService->>BindingSetRepository: transition(binding_set_uuid, CONFIRMED)
    BindingSetRepository-->>IdentityService: BindingSet(state=confirmed)

    IdentityService-->>Client: BindingSetResponse{state=confirmed, binding_count=1}
```

---

## 3. Provider-Owned Entity — Re-Submission (Matched Identity)

The same entity arrives in a later submission. The Source Identity is found via idempotent upsert, an existing confirmed Binding is located, and the Binding Set is auto-confirmed without minting a new Tracked Identity.

```mermaid
sequenceDiagram
    participant Client
    participant IdentityService
    participant IdentityPolicy
    participant SourceIdentityRepository
    participant BindingRepository
    participant BindingSetRepository

    Note over Client,BindingSetRepository: Step 1 — Resolve Identity (idempotent)

    Client->>IdentityService: resolve_identity(scope_uuid, ResolutionRequest)
    IdentityService->>IdentityPolicy: get_entity_policy(entity_type)
    IdentityPolicy-->>IdentityService: EntityPolicy{auto_confirm=true}

    IdentityService->>SourceIdentityRepository: create_or_get(scope_uuid, entity_type, keys)
    Note right of SourceIdentityRepository: Key match found — returns existing record
    SourceIdentityRepository-->>IdentityService: SourceIdentity(source_identity_uuid) [existing]

    IdentityService->>SourceIdentityRepository: link_to_submission(submission_uuid, source_identity_uuid)
    Note right of SourceIdentityRepository: ON CONFLICT DO NOTHING

    IdentityService->>BindingRepository: find_confirmed_binding(source_identity_uuid)
    BindingRepository-->>IdentityService: (Binding, BindingSetState=confirmed)

    IdentityService-->>Client: ResolutionOutcome{outcome=matched, tracked_identity_uuid=<uuid>}

    Note over Client,BindingSetRepository: Step 2 — Bind (to existing Tracked Identity)

    Client->>IdentityService: bind(submission_uuid, [outcome])
    IdentityService->>BindingSetRepository: create(submission_uuid)
    BindingSetRepository-->>IdentityService: BindingSet(state=proposed)

    IdentityService->>BindingRepository: create(binding_set_uuid, source_identity_uuid, tracked_identity_uuid, method=exact_match)
    BindingRepository-->>IdentityService: Binding

    IdentityService->>BindingSetRepository: transition(binding_set_uuid, CONFIRMED)
    BindingSetRepository-->>IdentityService: BindingSet(state=confirmed)

    IdentityService-->>Client: BindingSetResponse{state=confirmed, binding_count=1}
```

---

## 4. Shared Metadata Entity — Allocation Blocked

A shared metadata entity (e.g. `method`) arrives with no prior SIMS record and no reconciliation match. Policy blocks allocation; the Binding Set is left in `proposed` state with zero Bindings, signalling that the submission cannot proceed.

```mermaid
sequenceDiagram
    participant Client
    participant IdentityService
    participant IdentityPolicy
    participant SourceIdentityRepository
    participant BindingRepository
    participant BindingSetRepository

    Note over Client,BindingSetRepository: Step 1 — Resolve Identity

    Client->>IdentityService: resolve_identity(scope_uuid, ResolutionRequest{entity_type=method})
    IdentityService->>IdentityPolicy: get_entity_policy("method")
    IdentityPolicy-->>IdentityService: EntityPolicy{entity_subtype=shared_metadata, allow_allocation=false, auto_confirm=false}

    IdentityService->>SourceIdentityRepository: create_or_get(scope_uuid, entity_type, keys)
    SourceIdentityRepository-->>IdentityService: SourceIdentity(source_identity_uuid) [new]

    IdentityService->>SourceIdentityRepository: link_to_submission(submission_uuid, source_identity_uuid)

    IdentityService->>BindingRepository: find_confirmed_binding(source_identity_uuid)
    BindingRepository-->>IdentityService: None

    IdentityService-->>Client: ResolutionOutcome{outcome=new, tracked_identity_uuid=None}

    Note over Client,BindingSetRepository: Step 2 — Bind (allocation blocked by policy)

    Client->>IdentityService: bind(submission_uuid, [outcome])
    IdentityService->>BindingSetRepository: create(submission_uuid)
    BindingSetRepository-->>IdentityService: BindingSet(state=proposed)

    IdentityService->>IdentityPolicy: get_entity_policy("method") → allow_allocation=false
    Note over IdentityService: Allocation blocked — no Tracked Identity minted, no Binding created

    Note over IdentityService,BindingSetRepository: auto_confirm=false and zero bindings → Binding Set stays proposed
    IdentityService-->>Client: BindingSetResponse{state=proposed, binding_count=0}

    Note over Client: Submission halted — reconciliation required before re-submission
```

---

## 5. Manual Confirmation and Change Request Association

For shared metadata entities or low-confidence matches the Binding Set requires manual review before it can be associated with a Change Request in the SEAD Change Control System.

```mermaid
sequenceDiagram
    participant Reviewer
    participant IdentityService
    participant BindingSetRepository

    Note over Reviewer,BindingSetRepository: Binding Set was created in proposed state (no auto-confirm)

    Reviewer->>IdentityService: confirm_binding_set(binding_set_uuid)
    IdentityService->>BindingSetRepository: transition(binding_set_uuid, CONFIRMED)
    BindingSetRepository-->>IdentityService: BindingSet(state=confirmed, confirmed_at=now)
    IdentityService-->>Reviewer: BindingSet{state=confirmed}

    Note over Reviewer,BindingSetRepository: Identity correspondence is now authoritative

    Reviewer->>IdentityService: associate_change_request(binding_set_uuid, cr_name)
    IdentityService->>BindingSetRepository: associate_change_request(binding_set_uuid, cr_name)
    Note right of BindingSetRepository: Only succeeds if state = confirmed
    BindingSetRepository-->>IdentityService: BindingSet(change_request_name=cr_name)
    IdentityService-->>Reviewer: BindingSet{change_request_name=cr_name}

    Note over Reviewer: Change Request may now be applied to SEAD
```

---

## 6. Change Detection

Used to determine whether a previously materialized entity's content has changed, enabling optimistic skip-on-no-change behaviour (FR-24).

```mermaid
sequenceDiagram
    participant Client
    participant IdentityService
    participant TrackedIdentityRepository

    Client->>IdentityService: detect_change(ChangeDetectionRequest{tracked_identity_uuid, content_hash})
    IdentityService->>TrackedIdentityRepository: get(tracked_identity_uuid)
    TrackedIdentityRepository-->>IdentityService: TrackedIdentity{content_hash=<stored>}

    alt No prior hash (insert)
        IdentityService->>TrackedIdentityRepository: update_content_hash(tracked_identity_uuid, new_hash)
        IdentityService-->>Client: ChangeDetectionResult{outcome=insert}
    else Hash differs (update)
        IdentityService->>TrackedIdentityRepository: update_content_hash(tracked_identity_uuid, new_hash)
        IdentityService-->>Client: ChangeDetectionResult{outcome=update}
    else Hash matches (skip)
        IdentityService-->>Client: ChangeDetectionResult{outcome=skip}
    end
```
