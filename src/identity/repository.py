"""Async database repositories for the SIMS identity module.

Each repository handles one table. All use the existing get_connection()
context manager from src.configuration — the shared psycopg AsyncConnectionPool.

Usage:
    async with SourceScopeRepository() as repo:
        scope = await repo.get_by_name("sead://admin")

Or directly (the connection is acquired per-operation):
    repo = SourceScopeRepository()
    scope = await repo.get_by_name("sead://admin")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import psycopg
from loguru import logger
from psycopg.rows import dict_row

from src.configuration import get_connection
from src.identity.models import (
    Binding,
    BindingSet,
    SourceIdentity,
    SourceScope,
    Submission,
    TrackedIdentity,
)
from src.identity.types import (
    BindingMethod,
    BindingSetState,
    SubmissionStatus,
    TrackedIdentityState,
)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _uuid() -> UUID:
    return uuid4()


# ---------------------------------------------------------------------------
# SourceScopeRepository
# ---------------------------------------------------------------------------


class SourceScopeRepository:
    """CRUD for sead_identity.source_scopes."""

    async def get(self, scope_uuid: UUID) -> SourceScope | None:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.source_scopes WHERE scope_uuid = %s",
                    (str(scope_uuid),),
                )
                row = await cur.fetchone()
        return SourceScope(**row) if row else None

    async def get_by_name(self, scope_name: str) -> SourceScope | None:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.source_scopes WHERE scope_name = %s",
                    (scope_name,),
                )
                row = await cur.fetchone()
        return SourceScope(**row) if row else None

    async def list_all(self) -> list[SourceScope]:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute("SELECT * FROM sead_identity.source_scopes ORDER BY scope_name")
                rows = await cur.fetchall()
        return [SourceScope(**r) for r in rows]

    async def create(
        self,
        scope_name: str,
        description: str | None = None,
        parent_scope_uuid: UUID | None = None,
        created_by: str | None = None,
    ) -> SourceScope:
        scope_uuid = _uuid()
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.source_scopes
                        (scope_uuid, scope_name, parent_scope_uuid, description, created_by)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (str(scope_uuid), scope_name, str(parent_scope_uuid) if parent_scope_uuid else None, description, created_by),
                )
                row = await cur.fetchone()
        assert row is not None
        return SourceScope(**row)


# ---------------------------------------------------------------------------
# SubmissionRepository
# ---------------------------------------------------------------------------


class SubmissionRepository:
    """CRUD for sead_identity.submissions."""

    async def get(self, submission_uuid: UUID) -> Submission | None:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.submissions WHERE submission_uuid = %s",
                    (str(submission_uuid),),
                )
                row = await cur.fetchone()
        return Submission(**row) if row else None

    async def create(
        self,
        scope_uuid: UUID,
        submission_name: str,
        created_by: str | None = None,
    ) -> Submission:
        submission_uuid = _uuid()
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.submissions
                        (submission_uuid, scope_uuid, submission_name, created_by)
                    VALUES (%s, %s, %s, %s)
                    RETURNING *
                    """,
                    (str(submission_uuid), str(scope_uuid), submission_name, created_by),
                )
                row = await cur.fetchone()
        assert row is not None
        return Submission(**row)

    async def update_status(self, submission_uuid: UUID, status: SubmissionStatus) -> Submission | None:
        completed_at = _now() if status in (SubmissionStatus.COMPLETED, SubmissionStatus.FAILED) else None
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE sead_identity.submissions
                    SET status = %s, completed_at = %s
                    WHERE submission_uuid = %s
                    RETURNING *
                    """,
                    (status.value, completed_at, str(submission_uuid)),
                )
                row = await cur.fetchone()
        return Submission(**row) if row else None

    async def list_by_scope(self, scope_uuid: UUID) -> list[Submission]:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.submissions WHERE scope_uuid = %s ORDER BY created_at DESC",
                    (str(scope_uuid),),
                )
                rows = await cur.fetchall()
        return [Submission(**r) for r in rows]


# ---------------------------------------------------------------------------
# SourceIdentityRepository
# ---------------------------------------------------------------------------


class SourceIdentityRepository:
    """CRUD for sead_identity.source_identities.

    Upsert semantics: create_or_get() returns the existing row on conflict,
    which is the primary idempotency guarantee for FR-12/FR-13.
    """

    async def get(self, source_identity_uuid: UUID) -> SourceIdentity | None:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.source_identities WHERE source_identity_uuid = %s",
                    (str(source_identity_uuid),),
                )
                row = await cur.fetchone()
        return SourceIdentity(**row) if row else None

    async def find_by_signals(
        self,
        scope_uuid: UUID,
        entity_type: str,
        identity_type: str,
        identity_value: str,
    ) -> SourceIdentity | None:
        """Look up a Source Identity by its uniqueness key."""
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT * FROM sead_identity.source_identities
                    WHERE scope_uuid = %s
                      AND entity_type = %s
                      AND identity_type = %s
                      AND identity_value = %s
                    """,
                    (str(scope_uuid), entity_type, identity_type, identity_value),
                )
                row = await cur.fetchone()
        return SourceIdentity(**row) if row else None

    async def create_or_get(
        self,
        scope_uuid: UUID,
        entity_type: str,
        identity_type: str,
        identity_value: str,
        identity_signals: dict | None = None,
        created_by: str | None = None,
    ) -> SourceIdentity:
        """Idempotent upsert — returns existing row on conflict (FR-12, FR-13)."""
        source_identity_uuid = _uuid()
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.source_identities
                        (source_identity_uuid, scope_uuid, entity_type,
                         identity_type, identity_value, identity_signals, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (scope_uuid, entity_type, identity_type, identity_value)
                        DO UPDATE SET identity_signals = EXCLUDED.identity_signals
                    RETURNING *
                    """,
                    (
                        str(source_identity_uuid),
                        str(scope_uuid),
                        entity_type,
                        identity_type,
                        identity_value,
                        psycopg.types.json.Jsonb(identity_signals) if identity_signals else None,
                        created_by,
                    ),
                )
                row = await cur.fetchone()
        assert row is not None
        return SourceIdentity(**row)

    async def link_to_submission(self, submission_uuid: UUID, source_identity_uuid: UUID) -> None:
        """Record M:N linkage in submission_source_identities junction."""
        async with get_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.submission_source_identities
                        (submission_uuid, source_identity_uuid)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    (str(submission_uuid), str(source_identity_uuid)),
                )


# ---------------------------------------------------------------------------
# TrackedIdentityRepository
# ---------------------------------------------------------------------------


class TrackedIdentityRepository:
    """CRUD for sead_identity.tracked_identities."""

    async def get(self, tracked_identity_uuid: UUID) -> TrackedIdentity | None:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.tracked_identities WHERE tracked_identity_uuid = %s",
                    (str(tracked_identity_uuid),),
                )
                row = await cur.fetchone()
        return TrackedIdentity(**row) if row else None

    async def find_by_internal_id(self, entity_type: str, sead_internal_id: int) -> TrackedIdentity | None:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT * FROM sead_identity.tracked_identities
                    WHERE entity_type = %s AND sead_internal_id = %s
                    """,
                    (entity_type, sead_internal_id),
                )
                row = await cur.fetchone()
        return TrackedIdentity(**row) if row else None

    async def mint(self, entity_type: str, created_by: str | None = None) -> TrackedIdentity:
        """Allocate a new Tracked Identity (mint UUID, set state=allocated)."""
        tracked_identity_uuid = _uuid()
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.tracked_identities
                        (tracked_identity_uuid, entity_type, created_by)
                    VALUES (%s, %s, %s)
                    RETURNING *
                    """,
                    (str(tracked_identity_uuid), entity_type, created_by),
                )
                row = await cur.fetchone()
        assert row is not None
        logger.debug(f"Minted TrackedIdentity {tracked_identity_uuid} for entity_type={entity_type}")
        return TrackedIdentity(**row)

    async def update_content_hash(self, tracked_identity_uuid: UUID, content_hash: str) -> TrackedIdentity | None:
        """Store new content hash for change detection (FR-24)."""
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE sead_identity.tracked_identities
                    SET content_hash = %s
                    WHERE tracked_identity_uuid = %s
                    RETURNING *
                    """,
                    (content_hash, str(tracked_identity_uuid)),
                )
                row = await cur.fetchone()
        return TrackedIdentity(**row) if row else None

    async def update_lifecycle_state(
        self,
        tracked_identity_uuid: UUID,
        state: TrackedIdentityState,
        sead_internal_id: int | None = None,
    ) -> TrackedIdentity | None:
        materialized_at = _now() if state == TrackedIdentityState.MATERIALIZED else None
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE sead_identity.tracked_identities
                    SET lifecycle_state = %s,
                        sead_internal_id = COALESCE(%s, sead_internal_id),
                        materialized_at = COALESCE(%s, materialized_at)
                    WHERE tracked_identity_uuid = %s
                    RETURNING *
                    """,
                    (state.value, sead_internal_id, materialized_at, str(tracked_identity_uuid)),
                )
                row = await cur.fetchone()
        return TrackedIdentity(**row) if row else None


# ---------------------------------------------------------------------------
# BindingSetRepository
# ---------------------------------------------------------------------------


class BindingSetRepository:
    """CRUD for sead_identity.binding_sets."""

    async def get(self, binding_set_uuid: UUID) -> BindingSet | None:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.binding_sets WHERE binding_set_uuid = %s",
                    (str(binding_set_uuid),),
                )
                row = await cur.fetchone()
        return BindingSet(**row) if row else None

    async def create(self, submission_uuid: UUID | None, created_by: str | None = None) -> BindingSet:
        binding_set_uuid = _uuid()
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.binding_sets
                        (binding_set_uuid, submission_uuid, created_by)
                    VALUES (%s, %s, %s)
                    RETURNING *
                    """,
                    (str(binding_set_uuid), str(submission_uuid) if submission_uuid else None, created_by),
                )
                row = await cur.fetchone()
        assert row is not None
        return BindingSet(**row)

    async def transition(self, binding_set_uuid: UUID, new_state: BindingSetState) -> BindingSet | None:
        """Apply a lifecycle state transition. Confirmed_at is set when confirming."""
        confirmed_at = _now() if new_state == BindingSetState.CONFIRMED else None
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE sead_identity.binding_sets
                    SET lifecycle_state = %s,
                        confirmed_at = COALESCE(%s, confirmed_at)
                    WHERE binding_set_uuid = %s
                    RETURNING *
                    """,
                    (new_state.value, confirmed_at, str(binding_set_uuid)),
                )
                row = await cur.fetchone()
        return BindingSet(**row) if row else None

    async def associate_change_request(self, binding_set_uuid: UUID, change_request_name: str) -> BindingSet | None:
        """Record the Sqitch change name on a confirmed Binding Set (FR-27)."""
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    UPDATE sead_identity.binding_sets
                    SET change_request_name = %s
                    WHERE binding_set_uuid = %s
                      AND lifecycle_state = 'confirmed'
                    RETURNING *
                    """,
                    (change_request_name, str(binding_set_uuid)),
                )
                row = await cur.fetchone()
        return BindingSet(**row) if row else None

    async def list_by_submission(self, submission_uuid: UUID) -> list[BindingSet]:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.binding_sets WHERE submission_uuid = %s ORDER BY created_at DESC",
                    (str(submission_uuid),),
                )
                rows = await cur.fetchall()
        return [BindingSet(**r) for r in rows]


# ---------------------------------------------------------------------------
# BindingRepository
# ---------------------------------------------------------------------------


class BindingRepository:
    """CRUD for sead_identity.bindings."""

    async def get(self, binding_uuid: UUID) -> Binding | None:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.bindings WHERE binding_uuid = %s",
                    (str(binding_uuid),),
                )
                row = await cur.fetchone()
        return Binding(**row) if row else None

    async def create(
        self,
        binding_set_uuid: UUID,
        source_identity_uuid: UUID,
        tracked_identity_uuid: UUID,
        method: BindingMethod,
        provenance: dict | None = None,
        created_by: str | None = None,
    ) -> Binding:
        binding_uuid = _uuid()
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.bindings
                        (binding_uuid, binding_set_uuid, source_identity_uuid,
                         tracked_identity_uuid, method, provenance)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING *
                    """,
                    (
                        str(binding_uuid),
                        str(binding_set_uuid),
                        str(source_identity_uuid),
                        str(tracked_identity_uuid),
                        method.value,
                        psycopg.types.json.Jsonb(provenance) if provenance else None,
                    ),
                )
                row = await cur.fetchone()
        assert row is not None
        return Binding(**row)

    async def list_by_set(self, binding_set_uuid: UUID) -> list[Binding]:
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    "SELECT * FROM sead_identity.bindings WHERE binding_set_uuid = %s",
                    (str(binding_set_uuid),),
                )
                rows = await cur.fetchall()
        return [Binding(**r) for r in rows]

    async def find_confirmed_binding(
        self, source_identity_uuid: UUID
    ) -> tuple[Binding, BindingSet] | None:
        """Return the current confirmed Binding for a Source Identity, if any."""
        async with get_connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(
                    """
                    SELECT b.*, bs.lifecycle_state AS set_state
                    FROM sead_identity.bindings b
                    JOIN sead_identity.binding_sets bs
                        ON bs.binding_set_uuid = b.binding_set_uuid
                    WHERE b.source_identity_uuid = %s
                      AND bs.lifecycle_state = 'confirmed'
                    ORDER BY bs.confirmed_at DESC
                    LIMIT 1
                    """,
                    (str(source_identity_uuid),),
                )
                row = await cur.fetchone()
        if not row:
            return None
        set_state = row.pop("set_state")
        binding = Binding(**row)
        return binding, set_state
