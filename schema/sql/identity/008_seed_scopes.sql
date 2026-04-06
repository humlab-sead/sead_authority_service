-- SIMS: well-known internal source scopes
-- Represents SEAD-internal origins that use the same Source Scope / Submission model
-- as external providers (per IMPLEMENTATION_VIEW § Internal Origins).

insert into sead_identity.source_scopes (scope_name, description)
values
(
    'sead://admin',
    'SEAD administrator actions: adding or modifying classifiers, methods, and other SEAD-administered entities.'
),
(
    'sead://migration',
    'Sqitch-driven schema or data migrations that produce or modify tracked entities.'
),
(
    'sead://reconciliation',
    'Reconciliation outputs from the Shape Shifter workflow: matched shared metadata entities.'
);
