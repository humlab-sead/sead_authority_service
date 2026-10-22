"""Enumeration types for the SIMS identity module."""

from enum import StrEnum


class IdentityType(StrEnum):
    """How a Source Identity value was obtained from the provider."""

    UUID = "uuid"
    BUSINESS_KEY = "business_key"
    PROVIDER_KEY = "provider_key"
    AUTHORITY_KEY = "authority_key"


class SubmissionStatus(StrEnum):
    """Lifecycle state of a Submission."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class TrackedIdentityState(StrEnum):
    """Lifecycle state of a Tracked Identity."""

    ALLOCATED = "allocated"
    PENDING_MATERIALIZATION = "pending_materialization"
    MATERIALIZED = "materialized"
    INVALIDATED = "invalidated"


class BindingSetState(StrEnum):
    """Lifecycle state of a Binding Set."""

    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    INVALIDATED = "invalidated"


class BindingMethod(StrEnum):
    """How a Binding was established between a Source Identity and a Tracked Identity."""

    EXACT_MATCH = "exact_match"
    BUSINESS_KEY = "business_key"
    UUID_ACCEPTED = "uuid_accepted"
    UUID_MAPPED = "uuid_mapped"
    MANUAL = "manual"
    ALLOCATED = "allocated"


class ChangeOutcome(StrEnum):
    """Result of a content-hash change detection comparison."""

    INSERT = "insert"
    UPDATE = "update"
    SKIP = "skip"
