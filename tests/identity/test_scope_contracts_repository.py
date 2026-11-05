"""Unit tests for the provider-scope contract repository.

The database connection is replaced with a recording mock, so no live
PostgreSQL instance is required.
"""

from __future__ import annotations

import contextlib
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.identity.models import EntityKeyContract
from src.identity.repository import RepositoryError, ScopeEntityContractRepository

NOW = datetime(2026, 11, 5, 12, 0, 0, tzinfo=timezone.utc)
SCOPE_UUID: UUID = uuid4()
CONTRACT_UUID: UUID = uuid4()
SCOPE_NAME = "provider://gbif/occurrence"


def _make_cursor(return_row: dict | None = None, return_rows: list[dict] | None = None) -> MagicMock:
    cursor = AsyncMock()
    cursor.execute = AsyncMock()
    cursor.fetchone = AsyncMock(return_value=return_row)
    cursor.fetchall = AsyncMock(return_value=return_rows or [])
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
    return patch("src.identity.repository.get_connection", side_effect=lambda: _fake_get_connection(conn))


def _row(entity_type: str = "site", keys: list[str] | None = None) -> dict:
    return {
        "contract_uuid": CONTRACT_UUID,
        "scope_uuid": SCOPE_UUID,
        "entity_type": entity_type,
        "business_keys": keys or ["site_name", "country"],
        "created_at": NOW,
        "created_by": "shape-shifter",
    }


class TestScopeEntityContractRepository:
    @pytest.mark.asyncio
    async def test_list_by_scope_maps_rows_and_keeps_key_order(self) -> None:
        cursor = _make_cursor(return_rows=[_row("site", ["site_name", "country"])])
        conn = _make_conn(cursor)

        with _patch_connection(conn):
            contracts = await ScopeEntityContractRepository().list_by_scope(SCOPE_UUID)

        assert len(contracts) == 1
        assert isinstance(contracts[0], EntityKeyContract)
        assert contracts[0].business_keys == ["site_name", "country"]
        sql, params = cursor.execute.call_args.args
        assert "sead_identity.scope_entity_contracts" in str(sql)
        assert params == (SCOPE_UUID,)

    @pytest.mark.asyncio
    async def test_list_by_scope_name_joins_scope_table(self) -> None:
        cursor = _make_cursor(return_rows=[])
        conn = _make_conn(cursor)

        with _patch_connection(conn):
            contracts = await ScopeEntityContractRepository().list_by_scope_name(SCOPE_NAME)

        assert contracts == []
        sql, params = cursor.execute.call_args.args
        assert "sead_identity.source_scopes" in str(sql)
        assert params == (SCOPE_NAME,)

    @pytest.mark.asyncio
    async def test_create_inserts_ordered_key_list(self) -> None:
        cursor = _make_cursor(return_row=_row("site", ["site_name", "country"]))
        conn = _make_conn(cursor)

        with _patch_connection(conn):
            contract = await ScopeEntityContractRepository().create(SCOPE_UUID, "site", ["site_name", "country"], created_by="tester")

        assert contract.business_keys == ["site_name", "country"]
        sql, params = cursor.execute.call_args.args
        assert "INSERT INTO sead_identity.scope_entity_contracts" in str(sql)
        assert params[1:] == (SCOPE_UUID, "site", ["site_name", "country"], "tester")

    @pytest.mark.asyncio
    async def test_lock_scope_locks_the_scope_row(self) -> None:
        cursor = _make_cursor(return_row={"scope_uuid": SCOPE_UUID})
        conn = _make_conn(cursor)

        with _patch_connection(conn):
            await ScopeEntityContractRepository().lock_scope(SCOPE_UUID)

        sql, params = cursor.execute.call_args.args
        assert "FOR UPDATE" in str(sql)
        assert params == (SCOPE_UUID,)

    @pytest.mark.asyncio
    async def test_lock_scope_raises_when_scope_is_missing(self) -> None:
        cursor = _make_cursor(return_row=None)
        conn = _make_conn(cursor)

        with _patch_connection(conn), pytest.raises(RepositoryError, match="does not exist"):
            await ScopeEntityContractRepository().lock_scope(SCOPE_UUID)
