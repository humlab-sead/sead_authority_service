"""SIMS identity management module.

Provides identity policy, UUID allocation, and evidence tracing
for tracked SEAD entities. Runtime implementation of the SIMS design
(see docs/sims/ for design documentation).

Planned submodules:
- policy: resolve/allocate/map decision logic per entity type
- registry: identity_registry CRUD (UUID minting, evidence recording)
- models: identity domain models (IdentityEvidence, AllocationResult, etc.)
"""
