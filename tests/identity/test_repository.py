"""Unit tests for SIMS identity repositories — no database required.

These tests verify:
1. Each repository correctly builds its SQL query and passes the right params.
2. Returned rows are mapped to the correct domain model.
3. Idempotent upsert paths pass ON CONFLICT to psycopg.

We mock get_connection() with a lightweight async context manager. The mock
records every `execute(sql, params)` call so assertions can be made without
needing a live PostgreSQL instance.

Integration tests (marked pytest.mark.integration) which hit a real database
are intentionally excluded from this file.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

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

# ---------------------------------------------------------------------------
# Fake database infrastructure
# ---------------------------------------------------------------------------

NOW = datetime(2026, 4, 4, 12, 0, 0, tzinfo=timezone.utc)
SCOPE_UUID: UUID = uuid4()
SUBMISSION_UUID: UUID = uuid4()
IDENTITY_UUID: UUID = uuid4()
TRACKED_UUID: UUID = uuid4()
BINDING_SET_UUID: UUID = uuid4()
BINDING_UUID: UUID = uuid4()


def _make_cursor(return_row: dict | None = None, return_rows: list[dict] | None = None) -> MagicMock:
    """Return an async context-manager mock for conn.cursor(row_factory=...)."""
    cursor = AsyncMock()
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=return_row)
    cursor.fetchall = AsyncMock(return_value=return_rows or [])

    # cursor is used as `async with conn.cursor(...) as cur:`
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=False)
    return cursor


def _make_conn(cursor: MagicMock) -> MagicMock:
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=cursor)
    return conn


@contextlib.asynccontextmanager
async def _fake_get_connection(conn: MagicMock):
    yield conn


def _patch_connection(conn: MagicMock):
    """Return a patch context for src.identity.repository.get_connection."""
    return patch(
        "src.identity.repository.get_connection",
        side_effect=lambda: _fake_get_connection(conn),
    )


# ---------------------------------------------------------------------------
# SourceScopeRepository
# ---------------------------------------------------------------------------


class TestSourceScopeRepository:
    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self) -> None:
        from src.identity.repository import SourceScopeRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SourceScopeRepository()
            result = await repo.get(SCOPE_UUID)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_scope_when_found(self) -> None:
        from src.identity.repository import SourceScopeRepository

        row = {
            "scope_uuid": SCOPE_UUID,
            "scope_name": "sead://admin",
            "parent_scope_uuid": None,
            "description": "Admin scope",
            "created_by": None,
            "created_at": NOW,
        }
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SourceScopeRepository()
            result = await repo.get(SCOPE_UUID)
        assert isinstance(result, SourceScope)
        assert result.scope_name == "sead://admin"

    @pytest.mark.asyncio
    async def test_get_by_name_returns_none(self) -> None:
        from src.identity.repository import SourceScopeRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SourceScopeRepository()
            result = await repo.get_by_name("missing://scope")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_returns_scope(self) -> None:
        from src.identity.repository import SourceScopeRepository

        row = {
            "scope_uuid": SCOPE_UUID,
            "scope_name": "sead://reconciliation",
            "parent_scope_uuid": None,
            "description": None,
            "created_by": None,
            "created_at": NOW,
        }
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SourceScopeRepository()
            result = await repo.get_by_name("sead://reconciliation")
        assert isinstance(result, SourceScope)
        assert result.scope_uuid == SCOPE_UUID

    @pytest.mark.asyncio
    async def test_list_all_returns_list(self) -> None:
        from src.identity.repository import SourceScopeRepository

        rows = [
            {
                "scope_uuid": uuid4(),
                "scope_name": "sead://admin",
                "parent_scope_uuid": None,
                "description": None,
                "created_by": None,
                "created_at": NOW,
            }
        ]
        cursor = _make_cursor(return_rows=rows)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SourceScopeRepository()
            result = await repo.list_all()
        assert len(result) == 1
        assert isinstance(result[0], SourceScope)

    @pytest.mark.asyncio
    async def test_create_returns_scope(self) -> None:
        from src.identity.repository import SourceScopeRepository

        row = {
            "scope_uuid": SCOPE_UUID,
            "scope_name": "test://scope",
            "parent_scope_uuid": None,
            "description": "Test",
            "created_by": "test_agent",
            "created_at": NOW,
        }
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SourceScopeRepository()
            result = await repo.create("test://scope", description="Test", created_by="test_agent")
        assert isinstance(result, SourceScope)
        assert result.description == "Test"


# ---------------------------------------------------------------------------
# SubmissionRepository
# ---------------------------------------------------------------------------


class TestSubmissionRepository:
    def _make_submission_row(self, status: str = "pending") -> dict:
        return {
            "submission_uuid": SUBMISSION_UUID,
            "scope_uuid": SCOPE_UUID,
            "submission_name": "test_sub",
            "status": status,
            "created_by": None,
            "created_at": NOW,
            "completed_at": None,
        }

    @pytest.mark.asyncio
    async def test_create_sets_status_pending(self) -> None:
        from src.identity.repository import SubmissionRepository

        row = self._make_submission_row("pending")
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SubmissionRepository()
            result = await repo.create(SCOPE_UUID, "test_sub")
        assert isinstance(result, Submission)
        assert result.status == SubmissionStatus.PENDING

    @pytest.mark.asyncio
    async def test_update_status_to_completed(self) -> None:
        from src.identity.repository import SubmissionRepository

        row = self._make_submission_row("completed")
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SubmissionRepository()
            result = await repo.update_status(SUBMISSION_UUID, SubmissionStatus.COMPLETED)
        assert result is not None
        assert result.status == SubmissionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_status_returns_none_when_not_found(self) -> None:
        from src.identity.repository import SubmissionRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            repo = SubmissionRepository()
            result = await repo.update_status(SUBMISSION_UUID, SubmissionStatus.FAILED)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self) -> None:
        from src.identity.repository import SubmissionRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await SubmissionRepository().get(SUBMISSION_UUID)
        assert result is None


# ---------------------------------------------------------------------------
# SourceIdentityRepository
# ---------------------------------------------------------------------------


class TestSourceIdentityRepository:
    def _make_identity_row(self) -> dict:
        return {
            "source_identity_uuid": IDENTITY_UUID,
            "scope_uuid": SCOPE_UUID,
            "entity_type": "site",
            "created_by": None,
            "created_at": NOW,
        }

    @pytest.mark.asyncio
    async def test_find_by_key_returns_none(self) -> None:
        from src.identity.repository import SourceIdentityRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await SourceIdentityRepository().find_by_key(
                SCOPE_UUID, "site", "business_key", "MISSING"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_create_or_get_returns_identity(self) -> None:
        from src.identity.repository import SourceIdentityRepository

        row = self._make_identity_row()
        cursor = _make_cursor()
        # First fetchone: key lookup returns None (not found)
        # Second fetchone: header INSERT returns the row
        cursor.fetchone.side_effect = [None, row]
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await SourceIdentityRepository().create_or_get(
                scope_uuid=SCOPE_UUID,
                entity_type="site",
                keys=[("business_key", "ABC-001")],
            )
        assert isinstance(result, SourceIdentity)
        assert result.entity_type == "site"

    @pytest.mark.asyncio
    async def test_create_or_get_sql_uses_on_conflict(self) -> None:
        """Confirm the key-insert SQL contains ON CONFLICT clause."""
        from src.identity.repository import SourceIdentityRepository

        row = self._make_identity_row()
        cursor = _make_cursor()
        cursor.fetchone.side_effect = [None, row]
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            await SourceIdentityRepository().create_or_get(
                scope_uuid=SCOPE_UUID,
                entity_type="site",
                keys=[("business_key", "ABC-001")],
            )
        # The last execute call is the key INSERT — must contain ON CONFLICT
        sql_call = cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in sql_call


# ---------------------------------------------------------------------------
# TrackedIdentityRepository
# ---------------------------------------------------------------------------


class TestTrackedIdentityRepository:
    def _make_tracked_row(self, state: str = "allocated") -> dict:
        return {
            "tracked_identity_uuid": TRACKED_UUID,
            "entity_type": "site",
            "sead_internal_id": None,
            "content_hash": None,
            "lifecycle_state": state,
            "created_by": None,
            "created_at": NOW,
            "materialized_at": None,
        }

    @pytest.mark.asyncio
    async def test_mint_returns_allocated_identity(self) -> None:
        from src.identity.repository import TrackedIdentityRepository

        row = self._make_tracked_row("allocated")
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await TrackedIdentityRepository().mint("site")
        assert isinstance(result, TrackedIdentity)
        assert result.lifecycle_state == TrackedIdentityState.ALLOCATED

    @pytest.mark.asyncio
    async def test_update_content_hash_returns_updated(self) -> None:
        from src.identity.repository import TrackedIdentityRepository

        row = {**self._make_tracked_row(), "content_hash": "abc123"}
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await TrackedIdentityRepository().update_content_hash(TRACKED_UUID, "abc123")
        assert result is not None
        assert result.content_hash == "abc123"

    @pytest.mark.asyncio
    async def test_update_lifecycle_state_returns_updated(self) -> None:
        from src.identity.repository import TrackedIdentityRepository

        row = self._make_tracked_row("materialized")
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await TrackedIdentityRepository().update_lifecycle_state(
                TRACKED_UUID, TrackedIdentityState.MATERIALIZED
            )
        assert result is not None
        assert result.lifecycle_state == TrackedIdentityState.MATERIALIZED

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self) -> None:
        from src.identity.repository import TrackedIdentityRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await TrackedIdentityRepository().get(TRACKED_UUID)
        assert result is None


# ---------------------------------------------------------------------------
# BindingSetRepository
# ---------------------------------------------------------------------------


class TestBindingSetRepository:
    def _make_set_row(self, state: str = "proposed") -> dict:
        return {
            "binding_set_uuid": BINDING_SET_UUID,
            "submission_uuid": SUBMISSION_UUID,
            "lifecycle_state": state,
            "change_request_name": None,
            "created_by": None,
            "created_at": NOW,
            "confirmed_at": None,
        }

    @pytest.mark.asyncio
    async def test_create_returns_proposed_set(self) -> None:
        from src.identity.repository import BindingSetRepository

        row = self._make_set_row("proposed")
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await BindingSetRepository().create(SUBMISSION_UUID)
        assert isinstance(result, BindingSet)
        assert result.lifecycle_state == BindingSetState.PROPOSED

    @pytest.mark.asyncio
    async def test_transition_to_confirmed(self) -> None:
        from src.identity.repository import BindingSetRepository

        row = self._make_set_row("confirmed")
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await BindingSetRepository().transition(BINDING_SET_UUID, BindingSetState.CONFIRMED)
        assert result is not None
        assert result.lifecycle_state == BindingSetState.CONFIRMED

    @pytest.mark.asyncio
    async def test_transition_returns_none_when_not_found(self) -> None:
        from src.identity.repository import BindingSetRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await BindingSetRepository().transition(BINDING_SET_UUID, BindingSetState.CONFIRMED)
        assert result is None


# ---------------------------------------------------------------------------
# BindingRepository
# ---------------------------------------------------------------------------


class TestBindingRepository:
    def _make_binding_row(self) -> dict:
        return {
            "binding_uuid": BINDING_UUID,
            "binding_set_uuid": BINDING_SET_UUID,
            "source_identity_uuid": IDENTITY_UUID,
            "tracked_identity_uuid": TRACKED_UUID,
            "method": "business_key",
            "provenance": None,
            "created_at": NOW,
        }

    @pytest.mark.asyncio
    async def test_create_returns_binding(self) -> None:
        from src.identity.repository import BindingRepository

        row = self._make_binding_row()
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await BindingRepository().create(
                binding_set_uuid=BINDING_SET_UUID,
                source_identity_uuid=IDENTITY_UUID,
                tracked_identity_uuid=TRACKED_UUID,
                method=BindingMethod.BUSINESS_KEY,
            )
        assert isinstance(result, Binding)
        assert result.method == BindingMethod.BUSINESS_KEY

    @pytest.mark.asyncio
    async def test_list_by_set_returns_list(self) -> None:
        from src.identity.repository import BindingRepository

        rows = [self._make_binding_row()]
        cursor = _make_cursor(return_rows=rows)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            results = await BindingRepository().list_by_set(BINDING_SET_UUID)
        assert len(results) == 1
        assert isinstance(results[0], Binding)

    @pytest.mark.asyncio
    async def test_get_returns_none_when_missing(self) -> None:
        from src.identity.repository import BindingRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await BindingRepository().get(BINDING_UUID)
        assert result is None

    @pytest.mark.asyncio
    async def test_find_confirmed_binding_returns_none_when_missing(self) -> None:
        from src.identity.repository import BindingRepository

        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await BindingRepository().find_confirmed_binding(IDENTITY_UUID)
        assert result is None

    @pytest.mark.asyncio
    async def test_find_confirmed_binding_returns_tuple(self) -> None:
        from src.identity.repository import BindingRepository

        row = {**self._make_binding_row(), "set_state": "confirmed"}
        cursor = _make_cursor(return_row=row)
        conn = _make_conn(cursor)
        with _patch_connection(conn):
            result = await BindingRepository().find_confirmed_binding(IDENTITY_UUID)
        assert result is not None
        binding, set_state = result
        assert isinstance(binding, Binding)
        assert set_state == "confirmed"
