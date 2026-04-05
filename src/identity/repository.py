"""Async database repositories for the SIMS identity module.

Each repository handles one table. All use the existing get_connection()
context manager from src.configuration — the shared psycopg AsyncConnectionPool.

Usage:
    repo = SourceScopeRepository()
    scope = await repo.get_by_name("sead://admin")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar, Generic, TypeVar
from uuid import UUID, uuid4

from loguru import logger
from pydantic import BaseModel
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg.sql import SQL

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

ModelT = TypeVar("ModelT", bound=BaseModel)


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _uuid() -> UUID:
    return uuid4()


class RepositoryError(RuntimeError):
    """Raised when a repository operation fails unexpectedly."""


class BaseRepository(Generic[ModelT]):
    """Generic base repository for Pydantic-backed row models."""

    model: ClassVar[type]
    table_name: ClassVar[str]
    pk_column: ClassVar[str] = "id"
    default_order_by: ClassVar[str | None] = None

    async def get(self, pk: Any) -> ModelT | None:
        return await self.get_by(self.pk_column, pk)

    async def get_by(self, column: str, value: Any) -> ModelT | None:
        row = await self._fetchone(
            f"SELECT * FROM {self.table_name} WHERE {column} = %s",
            (value,),
        )
        return self._to_model(row)

    async def list_all(self) -> list[ModelT]:
        sql = f"SELECT * FROM {self.table_name}"
        if self.default_order_by:
            sql += f" ORDER BY {self.default_order_by}"
        rows = await self._fetchall(sql)
        return [self._to_model_required(row) for row in rows]

    async def _fetchone(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> dict[str, Any] | None:
        async with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(SQL(sql), params)  # type: ignore
            return await cur.fetchone()

    async def _fetchall(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        async with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(SQL(sql), params)  # type: ignore
            return list(await cur.fetchall())

    async def _execute(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> None:
        async with get_connection() as conn, conn.cursor() as cur:
            await cur.execute(SQL(sql), params)  # type: ignore

    def _to_model(self, row: dict[str, Any] | None) -> ModelT | None:
        return self.model.model_validate(row) if row is not None else None

    def _to_model_required(self, row: dict[str, Any] | None) -> ModelT:
        if row is None:
            raise RepositoryError(f"Expected row from {self.table_name}, got no result")
        return self.model.model_validate(row)

    async def _insert_returning(
        self,
        columns: list[str],
        values: tuple[Any, ...],
    ) -> ModelT:
        placeholders: str = ", ".join(["%s"] * len(columns))
        cols: str = ", ".join(columns)
        row = await self._fetchone(
            f"""
            INSERT INTO {self.table_name} ({cols})
            VALUES ({placeholders})
            RETURNING *
            """,
            values,
        )
        return self._to_model_required(row)


# ---------------------------------------------------------------------------
# SourceScopeRepository
# ---------------------------------------------------------------------------


class SourceScopeRepository(BaseRepository[SourceScope]):
    """CRUD for sead_identity.source_scopes."""

    model = SourceScope
    table_name = "sead_identity.source_scopes"
    pk_column = "scope_uuid"
    default_order_by = "scope_name"

    async def get_by_name(self, scope_name: str) -> SourceScope | None:
        return await self.get_by("scope_name", scope_name)

    async def create(
        self,
        scope_name: str,
        description: str | None = None,
        parent_scope_uuid: UUID | None = None,
        created_by: str | None = None,
    ) -> SourceScope:
        row = await self._fetchone(
            """
            INSERT INTO sead_identity.source_scopes
                (scope_uuid, scope_name, parent_scope_uuid, description, created_by)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *
            """,
            (_uuid(), scope_name, parent_scope_uuid, description, created_by),
        )
        return self._to_model_required(row)


# ---------------------------------------------------------------------------
# SubmissionRepository
# ---------------------------------------------------------------------------


class SubmissionRepository(BaseRepository[Submission]):
    """CRUD for sead_identity.submissions."""

    model = Submission
    table_name = "sead_identity.submissions"
    pk_column = "submission_uuid"

    async def create(
        self,
        scope_uuid: UUID,
        submission_name: str,
        created_by: str | None = None,
    ) -> Submission:
        row = await self._fetchone(
            """
            INSERT INTO sead_identity.submissions
                (submission_uuid, scope_uuid, submission_name, created_by)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (_uuid(), scope_uuid, submission_name, created_by),
        )
        return self._to_model_required(row)

    async def update_status(
        self,
        submission_uuid: UUID,
        status: SubmissionStatus,
    ) -> Submission | None:
        completed_at = _now() if status in (SubmissionStatus.COMPLETED, SubmissionStatus.FAILED) else None
        row = await self._fetchone(
            """
            UPDATE sead_identity.submissions
            SET status = %s, completed_at = %s
            WHERE submission_uuid = %s
            RETURNING *
            """,
            (status.value, completed_at, submission_uuid),
        )
        return self._to_model(row)

    async def list_by_scope(self, scope_uuid: UUID) -> list[Submission]:
        rows = await self._fetchall(
            """
            SELECT * FROM sead_identity.submissions
            WHERE scope_uuid = %s
            ORDER BY created_at DESC
            """,
            (scope_uuid,),
        )
        return [self._to_model_required(r) for r in rows]


# ---------------------------------------------------------------------------
# SourceIdentityRepository
# ---------------------------------------------------------------------------


class SourceIdentityRepository(BaseRepository[SourceIdentity]):
    """CRUD for sead_identity.source_identities and source_identity_keys.

    Idempotency: create_or_get() first tries to find an existing source identity
    by any of the supplied keys; only inserts a new header row (and its key rows)
    when none is found.
    """

    model = SourceIdentity
    table_name = "sead_identity.source_identities"
    pk_column = "source_identity_uuid"

    async def find_by_key(
        self,
        scope_uuid: UUID,
        entity_type: str,
        key_type: str,
        key_value: str,
    ) -> SourceIdentity | None:
        row = await self._fetchone(
            """
            SELECT si.*
            FROM sead_identity.source_identities si
            JOIN sead_identity.source_identity_keys sik
              ON sik.source_identity_uuid = si.source_identity_uuid
            WHERE si.scope_uuid  = %s
              AND si.entity_type = %s
              AND sik.key_type   = %s
              AND sik.key_value  = %s
            LIMIT 1
            """,
            (scope_uuid, entity_type, key_type, key_value),
        )
        return self._to_model(row)

    async def create_or_get(
        self,
        scope_uuid: UUID,
        entity_type: str,
        keys: list[tuple[str, str]],
        created_by: str | None = None,
    ) -> SourceIdentity:
        """Idempotent upsert — returns existing identity if any key already matches."""
        async with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            for key_type, key_value in keys:
                await cur.execute(
                    """
                    SELECT si.*
                    FROM sead_identity.source_identities si
                    JOIN sead_identity.source_identity_keys sik
                      ON sik.source_identity_uuid = si.source_identity_uuid
                    WHERE si.scope_uuid  = %s
                      AND si.entity_type = %s
                      AND sik.key_type   = %s
                      AND sik.key_value  = %s
                    LIMIT 1
                    """,
                    (scope_uuid, entity_type, key_type, key_value),
                )
                row = await cur.fetchone()
                if row:
                    return self._to_model_required(row)

            source_identity_uuid = _uuid()

            await cur.execute(
                """
                INSERT INTO sead_identity.source_identities
                    (source_identity_uuid, scope_uuid, entity_type, created_by)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (source_identity_uuid, scope_uuid, entity_type, created_by),
            )
            row = await cur.fetchone()
            model = self._to_model_required(row)

            for key_type, key_value in keys:
                await cur.execute(
                    """
                    INSERT INTO sead_identity.source_identity_keys
                        (source_identity_uuid, key_type, key_value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (source_identity_uuid, key_type) DO NOTHING
                    """,
                    (source_identity_uuid, key_type, key_value),
                )

            return model

    async def link_to_submission(
        self,
        submission_uuid: UUID,
        source_identity_uuid: UUID,
    ) -> None:
        await self._execute(
            """
            INSERT INTO sead_identity.submission_source_identities
                (submission_uuid, source_identity_uuid)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
            """,
            (submission_uuid, source_identity_uuid),
        )


# ---------------------------------------------------------------------------
# TrackedIdentityRepository
# ---------------------------------------------------------------------------


class TrackedIdentityRepository(BaseRepository[TrackedIdentity]):
    """CRUD for sead_identity.tracked_identities."""

    model = TrackedIdentity
    table_name = "sead_identity.tracked_identities"
    pk_column = "tracked_identity_uuid"

    async def find_by_internal_id(
        self,
        entity_type: str,
        sead_internal_id: int,
    ) -> TrackedIdentity | None:
        row = await self._fetchone(
            """
            SELECT * FROM sead_identity.tracked_identities
            WHERE entity_type = %s AND sead_internal_id = %s
            """,
            (entity_type, sead_internal_id),
        )
        return self._to_model(row)

    async def mint(
        self,
        entity_type: str,
        created_by: str | None = None,
    ) -> TrackedIdentity:
        tracked_identity_uuid = _uuid()
        row = await self._fetchone(
            """
            INSERT INTO sead_identity.tracked_identities
                (tracked_identity_uuid, entity_type, created_by)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (tracked_identity_uuid, entity_type, created_by),
        )
        logger.debug(
            "Minted TrackedIdentity {} for entity_type={}",
            tracked_identity_uuid,
            entity_type,
        )
        return self._to_model_required(row)

    async def update_content_hash(
        self,
        tracked_identity_uuid: UUID,
        content_hash: str,
    ) -> TrackedIdentity | None:
        row = await self._fetchone(
            """
            UPDATE sead_identity.tracked_identities
            SET content_hash = %s
            WHERE tracked_identity_uuid = %s
            RETURNING *
            """,
            (content_hash, tracked_identity_uuid),
        )
        return self._to_model(row)

    async def update_lifecycle_state(
        self,
        tracked_identity_uuid: UUID,
        state: TrackedIdentityState,
        sead_internal_id: int | None = None,
    ) -> TrackedIdentity | None:
        materialized_at = _now() if state == TrackedIdentityState.MATERIALIZED else None
        row = await self._fetchone(
            """
            UPDATE sead_identity.tracked_identities
            SET lifecycle_state = %s,
                sead_internal_id = COALESCE(%s, sead_internal_id),
                materialized_at = COALESCE(%s, materialized_at)
            WHERE tracked_identity_uuid = %s
            RETURNING *
            """,
            (state.value, sead_internal_id, materialized_at, tracked_identity_uuid),
        )
        return self._to_model(row)


# ---------------------------------------------------------------------------
# BindingSetRepository
# ---------------------------------------------------------------------------


class BindingSetRepository(BaseRepository[BindingSet]):
    """CRUD for sead_identity.binding_sets."""

    model = BindingSet
    table_name = "sead_identity.binding_sets"
    pk_column = "binding_set_uuid"

    async def create(
        self,
        submission_uuid: UUID | None,
        created_by: str | None = None,
    ) -> BindingSet:
        row = await self._fetchone(
            """
            INSERT INTO sead_identity.binding_sets
                (binding_set_uuid, submission_uuid, created_by)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (_uuid(), submission_uuid, created_by),
        )
        return self._to_model_required(row)

    async def transition(
        self,
        binding_set_uuid: UUID,
        new_state: BindingSetState,
    ) -> BindingSet | None:
        confirmed_at = _now() if new_state == BindingSetState.CONFIRMED else None
        row = await self._fetchone(
            """
            UPDATE sead_identity.binding_sets
            SET lifecycle_state = %s,
                confirmed_at = COALESCE(%s, confirmed_at)
            WHERE binding_set_uuid = %s
            RETURNING *
            """,
            (new_state.value, confirmed_at, binding_set_uuid),
        )
        return self._to_model(row)

    async def associate_change_request(
        self,
        binding_set_uuid: UUID,
        change_request_name: str,
    ) -> BindingSet | None:
        row = await self._fetchone(
            """
            UPDATE sead_identity.binding_sets
            SET change_request_name = %s
            WHERE binding_set_uuid = %s
              AND lifecycle_state = 'confirmed'
            RETURNING *
            """,
            (change_request_name, binding_set_uuid),
        )
        return self._to_model(row)

    async def list_by_submission(self, submission_uuid: UUID) -> list[BindingSet]:
        rows = await self._fetchall(
            """
            SELECT * FROM sead_identity.binding_sets
            WHERE submission_uuid = %s
            ORDER BY created_at DESC
            """,
            (submission_uuid,),
        )
        return [self._to_model_required(r) for r in rows]


# ---------------------------------------------------------------------------
# BindingRepository
# ---------------------------------------------------------------------------


class BindingRepository(BaseRepository[Binding]):
    """CRUD for sead_identity.bindings."""

    model = Binding
    table_name = "sead_identity.bindings"
    pk_column = "binding_uuid"

    async def create(
        self,
        binding_set_uuid: UUID,
        source_identity_uuid: UUID,
        tracked_identity_uuid: UUID,
        method: BindingMethod,
        provenance: dict[str, Any] | None = None,
        created_by: str | None = None,
    ) -> Binding:
        row = await self._fetchone(
            """
            INSERT INTO sead_identity.bindings
                (binding_uuid, binding_set_uuid, source_identity_uuid,
                 tracked_identity_uuid, method, provenance, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (
                _uuid(),
                binding_set_uuid,
                source_identity_uuid,
                tracked_identity_uuid,
                method.value,
                Jsonb(provenance) if provenance is not None else None,
                created_by,
            ),
        )
        return self._to_model_required(row)

    async def list_by_set(self, binding_set_uuid: UUID) -> list[Binding]:
        rows = await self._fetchall(
            """
            SELECT * FROM sead_identity.bindings
            WHERE binding_set_uuid = %s
            """,
            (binding_set_uuid,),
        )
        return [self._to_model_required(r) for r in rows]

    async def find_confirmed_binding(
        self,
        source_identity_uuid: UUID,
    ) -> tuple[Binding, BindingSetState] | None:
        row = await self._fetchone(
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
            (source_identity_uuid,),
        )
        if row is None:
            return None

        set_state = BindingSetState(row.pop("set_state"))
        binding = self._to_model_required(row)
        return binding, set_state
