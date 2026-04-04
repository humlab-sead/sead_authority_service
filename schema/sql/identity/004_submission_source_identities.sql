-- SIMS: submission_source_identities (junction)
-- Records which Source Identities were carried by which Submissions (M:N).
-- A Source Identity may appear in multiple Submissions; a Submission carries multiple Source Identities.

create table sead_identity.submission_source_identities (
    submission_uuid      uuid        not null references sead_identity.submissions (submission_uuid),
    source_identity_uuid uuid        not null references sead_identity.source_identities (source_identity_uuid),
    observed_at          timestamptz not null default now(),

    constraint submission_source_identities_pkey
        primary key (submission_uuid, source_identity_uuid)
);

create index submission_source_identities_source_idx
    on sead_identity.submission_source_identities (source_identity_uuid);

comment on table sead_identity.submission_source_identities is
    'Junction: records which Source Identities were observed in which Submissions. '
    'Reflects the M:N relation — a Source Identity may appear across multiple deliveries (FR-23).';
