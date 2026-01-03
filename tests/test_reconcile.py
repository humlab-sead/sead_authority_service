from __future__ import annotations

from typing import Any

import pytest

import src.reconcile as reconcile_module


class _ConfigProvider:
    def __init__(self, config: dict[str, Any]):
        self._config = config

    def get_config(self) -> dict[str, Any]:
        return self._config


class _RecordingStrategy:
    calls: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []

    async def find_candidates(self, *, query: str, properties: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "properties": properties, "limit": limit})
        return list(self.candidates)

    def as_candidate(self, data: dict[str, Any], query: str) -> dict[str, Any]:
        return {"id": data.get("id"), "name": data.get("name"), "query": query}


@pytest.mark.asyncio
async def test_reconcile_queries_empty_query_short_circuits(monkeypatch: pytest.MonkeyPatch):
    async def _fake_get_connection():
        return object()

    monkeypatch.setattr(reconcile_module, "get_config_provider", lambda: _ConfigProvider({"options:default_query_limit": 10}))
    monkeypatch.setattr(reconcile_module.Strategies, "items", {"site": _RecordingStrategy}, raising=False)

    _RecordingStrategy.calls = []
    results = await reconcile_module.reconcile_queries({"q0": {"query": "   ", "type": "site"}})
    assert results == {"q0": {"result": []}}
    assert not _RecordingStrategy.calls


@pytest.mark.asyncio
async def test_reconcile_queries_missing_type_raises(monkeypatch: pytest.MonkeyPatch):
    async def _fake_get_connection():
        return object()

    monkeypatch.setattr(reconcile_module, "get_config_provider", lambda: _ConfigProvider({}))
    monkeypatch.setattr(reconcile_module.Strategies, "items", {"site": _RecordingStrategy}, raising=False)

    with pytest.raises(ValueError, match="Missing 'type' in query"):
        await reconcile_module.reconcile_queries({"q0": {"query": "abc"}})


@pytest.mark.asyncio
async def test_reconcile_queries_unknown_type_raises(monkeypatch: pytest.MonkeyPatch):
    async def _fake_get_connection():
        return object()

    monkeypatch.setattr(reconcile_module, "get_config_provider", lambda: _ConfigProvider({}))
    monkeypatch.setattr(reconcile_module.Strategies, "items", {"site": _RecordingStrategy}, raising=False)

    with pytest.raises(ValueError, match="Unknown query type 'nope' in query"):
        await reconcile_module.reconcile_queries({"q0": {"query": "abc", "type": "nope"}})


@pytest.mark.asyncio
async def test_reconcile_queries_builds_properties_and_candidates(monkeypatch: pytest.MonkeyPatch):
    async def _fake_get_connection():
        return object()

    monkeypatch.setattr(reconcile_module, "get_config_provider", lambda: _ConfigProvider({"options:default_query_limit": 7}))
    monkeypatch.setattr(reconcile_module.Strategies, "items", {"site": _RecordingStrategy}, raising=False)

    _RecordingStrategy.calls = []
    _RecordingStrategy.candidates = [{"id": "1", "name": "Site A"}, {"id": "2", "name": "Site B"}]

    queries = {
        "q0": {
            "query": "upp",
            "type": "site",
            "properties": [
                {"pid": "country", "v": "Sweden"},
                {"pid": "missing_v"},
                {"v": "missing_pid"},
            ],
        }
    }

    results = await reconcile_module.reconcile_queries(queries)
    assert results["q0"]["result"] == [
        {"id": "1", "name": "Site A", "query": "upp"},
        {"id": "2", "name": "Site B", "query": "upp"},
    ]
    assert _RecordingStrategy.calls == [{"query": "upp", "properties": {"country": "Sweden"}, "limit": 7}]


@pytest.mark.asyncio
async def test_reconcile_queries_fallback_default_limit(monkeypatch: pytest.MonkeyPatch):
    async def _fake_get_connection():
        return object()

    monkeypatch.setattr(reconcile_module, "get_config_provider", lambda: _ConfigProvider({}))
    monkeypatch.setattr(reconcile_module.Strategies, "items", {"site": _RecordingStrategy}, raising=False)

    _RecordingStrategy.calls = []
    _RecordingStrategy.candidates = []

    await reconcile_module.reconcile_queries({"q0": {"query": "ab", "type": "site"}})
    assert _RecordingStrategy.calls[0]["limit"] == 10


@pytest.mark.asyncio
async def test_reconcile_queries_covers_strategy_cls_none_branch(monkeypatch: pytest.MonkeyPatch):
    class _FlakyItems:
        def __init__(self):
            self._calls = 0

        def get(self, key: str, default: Any = None) -> Any:  # pylint: disable=unused-argument
            self._calls += 1
            if self._calls == 1:
                return _RecordingStrategy
            return None

        def keys(self):
            return ["site"]

    async def _fake_get_connection():
        return object()

    monkeypatch.setattr(reconcile_module, "get_config_provider", lambda: _ConfigProvider({}))
    monkeypatch.setattr(reconcile_module.Strategies, "items", _FlakyItems(), raising=False)

    with pytest.raises(ValueError, match="Unknown entity type: site"):
        await reconcile_module.reconcile_queries({"q0": {"query": "ab", "type": "site"}})
