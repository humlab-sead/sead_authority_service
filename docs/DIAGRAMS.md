# SEAD Authority Service - System Diagrams

Diagrams describing the system's context, component structure, runtime flows, and state machines.

---

## 1. System Context

External systems that interact with the SEAD Authority Service and the direction of each integration.

```mermaid
flowchart LR
    subgraph Clients
        OR[OpenRefine]
        SS[Shape Shifter]
        DT[Data Tools / Scripts]
    end

    subgraph "SEAD Authority Service"
        SVC[FastAPI :8000<br/>Reconciliation · Identity]
    end

    subgraph "External Systems"
        PG[(PostgreSQL<br/>SEAD Database)]
        LLM[LLM Providers<br/>OpenAI · Anthropic · Ollama]
        MCP[Embedded MCP Server<br/>search_lookup]
    end

    OR -->|POST /reconcile| SVC
    SS -->|POST /identity/resolve| SVC
    DT -->|GET /suggest · GET /flyout| SVC

    SVC -->|Entity queries · Identity writes| PG
    SVC -->|Candidate validation| LLM
    SVC <-->|Retrieval augmentation| MCP

    classDef client fill:#f5f5f5,stroke:#aaaaaa,color:#333333;
    classDef svc fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef ext fill:#fdf3e8,stroke:#d48a2a,color:#4a2800;
    classDef db fill:#eeeeee,stroke:#888888,color:#333333;

    class OR,SS,DT client;
    class SVC svc;
    class LLM,MCP ext;
    class PG db;
```

---

## 2. Component Architecture

Internal components of the service and their relationships.

```mermaid
flowchart TB
    subgraph "API Layer"
        RR[Reconciliation Router<br/>/reconcile · /suggest · /flyout]
        IR[Identity Router<br/>/identity/*]
    end

    subgraph "Orchestration"
        RC[Reconciliation Orchestrator<br/>reconcile.py · suggest.py · preview.py]
        IS[Identity Service<br/>resolve · bind · confirm · detect-change]
    end

    subgraph "Strategy Registry"
        REG[Strategies Registry]
        BS[Base Strategy<br/>ReconciliationStrategy]
        RH[RAG Hybrid Strategy]
        ES[Entity Strategies<br/>Site · Taxon · Method · Reference · …]
    end

    subgraph "Data Access"
        BR[Base Repository<br/>trigram search · alternate ID]
        SR[Specialized Repositories<br/>SiteRepository · …]
        ID_R[Identity Repositories<br/>scopes · submissions · bindings · …]
    end

    subgraph "Cross-Cutting"
        CFG[Configuration<br/>ConfigValue · ConfigStore]
        LLM[LLM Providers<br/>OpenAI · Anthropic · Ollama]
        POOL[Connection Pool<br/>get_connection]
    end

    RR --> RC
    IR --> IS
    RC --> REG
    REG --> BS
    BS --> RH
    BS --> ES
    ES --> BR
    ES --> SR
    IS --> ID_R
    BR --> POOL
    SR --> POOL
    ID_R --> POOL
    RH --> LLM
    RC --> CFG
    IS --> CFG

    classDef api fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef orch fill:#f5e8fd,stroke:#8a4ab0,color:#3a1060;
    classDef registry fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef data fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef cross fill:#f5f5f5,stroke:#aaaaaa,color:#333333;

    class RR,IR api;
    class RC,IS orch;
    class REG,BS,RH,ES registry;
    class BR,SR,ID_R data;
    class CFG,LLM,POOL cross;
```

---

## 3. Reconciliation Request Flow

How a reconciliation query travels from an external client through the service to a response.

```mermaid
flowchart LR
    C([Client]) -->|POST /reconcile| RR[Reconciliation Router]

    RR -->|Validate request| ORC[Orchestrator]

    ORC -->|for each query| STR{Strategies.get\nentity_type}

    STR -->|strategy found| FIND[find_candidates]
    STR -->|not found| ERR[Return empty result]

    FIND --> PROPS[Parse property hints\nlat · lon · DOI · etc.]
    PROPS --> ALT{Alternate ID\nmatch?}

    ALT -->|yes| EXACT[Exact lookup\nby alt identifier]
    ALT -->|no| TRGM[Trigram search\nPostgreSQL]

    EXACT --> SCORE[Score and rank candidates]
    TRGM --> SCORE

    SCORE --> RAG{RAG hybrid\nenabled?}

    RAG -->|yes| LLM[LLM validation\nof top candidates]
    RAG -->|no| FMT[Format as OpenRefine candidates]
    LLM --> FMT

    FMT --> ORC
    ORC --> C

    classDef io fill:#f5f5f5,stroke:#aaaaaa,color:#333333;
    classDef decision fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef action fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef ext fill:#fdf3e8,stroke:#d48a2a,color:#4a2800;
    classDef err fill:#ffe0e0,stroke:#d64545,color:#4a1f1f;

    class C io;
    class STR,ALT,RAG decision;
    class RR,ORC,FIND,PROPS,EXACT,TRGM,SCORE,FMT action;
    class LLM ext;
    class ERR err;
```

---

## 4. Strategy Auto-Registration

How reconciliation strategies enter the registry at startup.

```mermaid
flowchart LR
    BOOT[Application startup] --> IMPORT[main.py imports\nsrc.strategies]

    IMPORT --> WALK[strategies/__init__.py\nrecursive module load]

    WALK --> M1[site.py]
    WALK --> M2[taxon.py]
    WALK --> M3[method.py]
    WALK --> M4[reference.py]
    WALK --> MN[…]

    M1 -->|@Strategies.register\nkey=site| REG[(Strategies Registry)]
    M2 -->|@Strategies.register\nkey=taxon| REG
    M3 -->|@Strategies.register\nkey=method| REG
    M4 -->|@Strategies.register\nkey=bibliographic_reference| REG
    MN -->|@Strategies.register\n…| REG

    REG --> READY[Runtime: Strategies.get\nentity_type → strategy]

    classDef boot fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef module fill:#f5f5f5,stroke:#aaaaaa,color:#333333;
    classDef registry fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef ready fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;

    class BOOT,IMPORT,WALK boot;
    class M1,M2,M3,M4,MN module;
    class REG registry;
    class READY ready;
```

---

## 5. Identity Resolution Flow

How the SIMS identity module resolves a batch of source identities into stable UUIDs.

```mermaid
flowchart LR
    C([Submission Tool]) -->|POST /identity/resolve\nResolutionRequest| IR[Identity Router]

    IR --> SVC[Identity Service]

    SVC --> SCOPE[get_or_create_scope\nsource_system]
    SCOPE --> SUB[create_submission]

    SUB --> LOOP[for each source identity]

    LOOP --> POL[policy.get_entity_policy\nentity_type]
    POL --> LOOKUP{Existing binding\nfound?}

    LOOKUP -->|yes| REUSE[Reuse tracked UUID]
    LOOKUP -->|no| METHOD{Binding method}

    METHOD -->|business key| MATCH[Reconcile via Authority Service]
    METHOD -->|allocate| ALLOC[Allocate new UUID]
    METHOD -->|manual| PENDING[Mark pending manual review]

    REUSE --> BIND[Bind source ID → UUID]
    MATCH --> BIND
    ALLOC --> BIND
    PENDING --> BIND

    BIND --> POL2{Auto-confirm\npolicy?}

    POL2 -->|yes| CONF[BindingSet: CONFIRMED]
    POL2 -->|no| PROP[BindingSet: PROPOSED]

    CONF --> C
    PROP --> C

    classDef io fill:#f5f5f5,stroke:#aaaaaa,color:#333333;
    classDef svc fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef decision fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef action fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef state fill:#fdf3e8,stroke:#d48a2a,color:#4a2800;

    class C io;
    class IR,SVC svc;
    class LOOKUP,METHOD,POL2 decision;
    class SCOPE,SUB,LOOP,POL,REUSE,MATCH,ALLOC,PENDING,BIND action;
    class CONF,PROP state;
```

---

## 6. Binding Set State Machine

Lifecycle states of a SIMS `BindingSet` from creation to final outcome.

```mermaid
stateDiagram-v2
    direction LR

    [*] --> Proposed : Resolve request\n(manual review required)
    [*] --> Confirmed : Resolve request\n(auto-confirm policy)

    Proposed --> Confirmed : POST /binding-sets/{uuid}/confirm
    Proposed --> Rejected : Operator rejects
    Proposed --> Superseded : Newer binding set\nreplaces this one

    Confirmed --> Invalidated : Source data\nwithdrawn

    Rejected --> [*]
    Superseded --> [*]
    Invalidated --> [*]

    note right of Proposed
        Awaiting operator review.
        UUID allocated; not yet
        safe for downstream use.
    end note

    note right of Confirmed
        UUID stable and safe
        for downstream ingestion.
    end note

    classDef proposed fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef confirmed fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef rejected fill:#ffe0e0,stroke:#d64545,color:#4a1f1f;
    classDef terminal fill:#eeeeee,stroke:#888888,color:#333333;

    class Proposed proposed;
    class Confirmed confirmed;
    class Rejected,Superseded,Invalidated terminal;
```

---

## 7. Tracked Identity State Machine

Lifecycle states of a `TrackedIdentity` (a stable UUID allocated to a SEAD entity).

```mermaid
stateDiagram-v2
    direction LR

    [*] --> Allocated : UUID allocated\non first resolution

    Allocated --> PendingMaterialization : Binding confirmed;\nawaiting Clearinghouse ingestion

    PendingMaterialization --> Materialized : Clearinghouse\ncommit confirmed

    Materialized --> Invalidated : Source data\nwithdrawn or superseded

    Allocated --> Invalidated : Allocation voided\nbefore materialization

    Invalidated --> [*]

    note right of Allocated
        UUID exists; not yet
        written to SEAD.
    end note

    note right of Materialized
        UUID is live in the
        SEAD Clearinghouse.
    end note

    classDef allocated fill:#fff7d6,stroke:#d6a300,color:#2b2b2b;
    classDef pending fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef materialized fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef invalidated fill:#eeeeee,stroke:#888888,color:#333333;

    class Allocated allocated;
    class PendingMaterialization pending;
    class Materialized materialized;
    class Invalidated invalidated;
```

---

## 8. Configuration and Initialization Sequence

Order of initialization at service startup.

```mermaid
flowchart TB
    START([uvicorn starts]) --> LIFESPAN[FastAPI lifespan event]

    LIFESPAN --> ENV[Load .env file]
    ENV --> YAML[Parse config/config.yml\n+ @include entities.yml\n+ @include prompts.yml\n+ identity_policy.yml]
    YAML --> STORE[Initialize ConfigStore]
    STORE --> POOL[Create async connection pool\nget_connection singleton]
    POOL --> IMPORT[Import src.strategies\nauto-register all strategies]
    IMPORT --> READY([Service ready :8000])

    READY --> REQ[Incoming request]
    REQ --> CV[ConfigValue.resolve\nreads from ConfigStore]
    REQ --> CONN[get_connection\nreturns pool reference]

    classDef boot fill:#dff7e8,stroke:#2e9f5b,color:#1d3a29;
    classDef ready fill:#e8f4fd,stroke:#4a90d9,color:#1a3a5c;
    classDef runtime fill:#f5f5f5,stroke:#aaaaaa,color:#333333;

    class START,LIFESPAN,ENV,YAML,STORE,POOL,IMPORT boot;
    class READY ready;
    class REQ,CV,CONN runtime;
```

---

## Related Documents

- [DESIGN.md](DESIGN.md) — architecture rationale, component responsibilities, design decisions, and known constraints
- [DEVELOPMENT.md](DEVELOPMENT.md) — contributor workflow and development commands
- [SIMS documentation](SIMS/) — identity module requirements, design views, and entity tracking policy
