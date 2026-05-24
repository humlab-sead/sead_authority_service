from typing import Any, Type

import pytest

import src.strategies.strategy as strategy_module
from src.configuration.provider import MockConfigProvider
from src.strategies.strategy import ReconciliationStrategy, Strategies
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config

# pylint: disable=attribute-defined-outside-init,protected-access, unused-argument


class TestMultipleReconciliationStrategy:

    @pytest.mark.parametrize(
        "strategy_cls",
        [strategy_cls for strategy_cls in Strategies.items.values()],
    )
    @pytest.mark.asyncio
    @with_test_config
    async def test_reconciliation_strategy(
        self,
        strategy_cls: Type[ReconciliationStrategy],
        test_provider: ExtendedMockConfigProvider,
    ) -> None:
        """Test reconciliation strategy."""

        strategy = strategy_cls()

        if strategy_cls.__name__.split(".")[-1] in [
            "GeoNamesReconciliationStrategy",
            "BibliographicReferenceReconciliationStrategy",
            "RAGMethodsReconciliationStrategy",
            "TaxonReconciliationStrategy",
        ]:
            return

        key: str = strategy.specification.get("key", "unknown")
        id_field: str = strategy.specification.get("id_field", "id")

        assert key == strategy.key
        assert strategy.get_entity_id_field() == id_field
        assert strategy.get_label_field() == strategy.specification.get("label_field", "name")

        mock_rows = [
            {id_field: 1, "label": f"Test {key.capitalize()} 1", "name_sim": 0.9},
            {id_field: 2, "label": f"Test {key.capitalize()} 2", "name_sim": 0.8},
        ]

        test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

        result: list[dict[str, Any]] = await strategy.find_candidates(f"Hej {key}", limit=5)

        test_provider.connection_mock.cursor_instance.execute.assert_called()  # type: ignore
        test_provider.connection_mock.cursor_instance.fetchall.assert_called()  # type: ignore
        assert result == mock_rows

    @pytest.mark.parametrize(
        "strategy_cls",
        [strategy_cls for strategy_cls in Strategies.items.values()],
    )
    @with_test_config
    def test_get_entity_id_field(self, strategy_cls, test_provider: MockConfigProvider):
        """Test getting entity ID field name."""
        strategy: ReconciliationStrategy = strategy_cls()
        assert strategy.get_entity_id_field() == strategy.specification["id_field"]

    # @pytest.mark.parametrize(
    #     "strategy_cls",
    #     [strategy_cls for strategy_cls in Strategies.items.values()],
    # )
    # @with_test_config
    # def test_get_label_field(self, strategy_cls, test_provider: MockConfigProvider):
    #     """Test getting label field name."""
    #     strategy: ReconciliationStrategy = strategy_cls()
    #     assert strategy.get_label_field() == "label"

    # @pytest.mark.parametrize(
    #     "strategy_cls",
    #     [strategy_cls for strategy_cls in Strategies.items.values()],
    # )
    # @with_test_config
    # def test_get_id_path(self, strategy_cls, test_provider: MockConfigProvider):
    #     """Test getting ID path."""
    #     strategy: ReconciliationStrategy = strategy_cls()
    #     assert strategy.specification.get("key", "unknown") == strategy.key

    @pytest.mark.parametrize(
        "strategy_cls",
        [strategy_cls for strategy_cls in Strategies.items.values()],
    )
    @with_test_config
    def test_get_property_settings(self, strategy_cls, test_provider: MockConfigProvider):
        """Test get_property_settings method returns location-specific settings."""
        strategy = strategy_cls()
        settings = strategy.get_property_settings()

        assert isinstance(settings, dict)

    # @patch("src.strategies.location.LocationRepository")
    # @pytest.mark.parametrize(
    #     "strategy_cls",
    #     [strategy_cls for strategy_cls in Strategies.items.values()],
    # )
    # @pytest.mark.asyncio
    # @with_test_config
    # async def test_find_candidates_by_fuzzy_search(self, mock_query_proxy_class, strategy_cls, test_provider: MockConfigProvider):
    #     """Test finding candidates by fuzzy search when no national ID."""
    #     strategy: ReconciliationStrategy = strategy_cls()
    #     mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
    #     mock_proxy = AsyncMock()
    #     mock_query_proxy_class.return_value = mock_proxy

    #     mock_proxy.fetch_location_by_national_id.return_value = []
    #     mock_locations: list[dict[str, Any]] = [
    #         {"location_id": 1, "label": "Test Location", "name_sim": 0.9},
    #         {"location_id": 2, "label": "Another Location", "name_sim": 0.7},
    #     ]
    #     mock_proxy.find.return_value = mock_locations

    #     result = await strategy.find_candidates(mock_cursor, "test location", {}, limit=5)

    #     mock_proxy.find.assert_called_once_with("test location", 5)
    #     # Results should be sorted by name_sim in descending order
    #     assert result[0]["name_sim"] >= result[1]["name_sim"]

    # @pytest.mark.asyncio
    # @pytest.mark.parametrize(
    #     "strategy_cls",
    #     [strategy_cls for strategy_cls in Strategies.items.values()],
    # )
    # @patch("src.strategies.location.LocationRepository")
    # @with_test_config
    # async def test_get_details(self, mock_query_proxy_class, strategy_cls, test_provider: ExtendedMockConfigProvider):
    #     """Test getting site details."""

    #     strategy: ReconciliationStrategy = strategy_cls()
    #     mock_rows = [{"ID": 123, "Name": "Test Site", "Description": "A test site"}]
    #     test_provider.create_connection_mock(fetchall=mock_rows, execute=None)

    #     result = await strategy.get_details("123")

    #     test_provider.connection_mock.egy.get_details.assert_called_once_with("123")
    #     assert result == mock_rows


class _StubConfigValue:
    def __init__(self, path: str, default=None):
        self.path = path
        self.default = default

    def resolve(self):
        if self.path == "options:auto_accept_threshold":
            return 0.85
        if self.path == "options:id_base":
            return "https://w3id.org/sead/id/"
        if self.path.startswith("table_specs."):
            return {}
        return self.default


class _FakeRepository(strategy_module.BaseRepository):  # type: ignore[misc]
    def __init__(self, specification):
        self.specification = specification
        self.fetch_by_alternate_identity_calls: list[str] = []
        self.find_calls: list[tuple[str, int]] = []

    async def fetch_by_alternate_identity(self, alternate_identity: str, **kwargs) -> list[dict[str, Any]]:
        self.fetch_by_alternate_identity_calls.append(alternate_identity)
        return [{"name_sim": 0.2, "label": "alt", "id": 10}]

    async def find(self, name: str, limit: int = 10, **kwargs) -> list[dict[str, Any]]:
        self.find_calls.append((name, limit))
        return [{"name_sim": 0.9, "label": "name", "id": 11}]

    async def get_details(self, entity_id: str, **kwargs) -> dict[str, Any] | None:
        return {"ID": entity_id}


class _DummyRepoInstance(strategy_module.BaseRepository):  # type: ignore[misc]
    def __init__(self):
        pass


class _TestStrategy(ReconciliationStrategy):
    repository_cls = _FakeRepository  # type: ignore[assignment]
    _registry_key = "my_type"


class _NoRepoStrategy(ReconciliationStrategy):
    repository_cls = None  # type: ignore[assignment]
    _registry_key = "no_repo"


@pytest.mark.asyncio
async def test_find_candidates_uses_alternate_identity(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "key": "my_type",
        "id_field": "id",
        "label_field": "label",
        "alternate_identity_field": "alt_id",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }

    monkeypatch.setattr(strategy_module, "ConfigValue", _StubConfigValue)
    monkeypatch.setattr(strategy_module, "resolve_specification", lambda specification=None: spec)

    repo = _FakeRepository(spec)
    strategy = _TestStrategy(repository_or_cls=repo)  # type: ignore[arg-type]

    candidates = await strategy.find_candidates("q", properties={"alt_id": "ABC"}, limit=10)
    assert repo.fetch_by_alternate_identity_calls == ["ABC"]
    assert repo.find_calls == [("q", 10)]
    assert [c["id"] for c in candidates] == [11, 10]


@pytest.mark.asyncio
async def test_find_candidates_sorts_by_score_when_name_sim_missing(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "key": "my_type",
        "id_field": "id",
        "label_field": "label",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }

    monkeypatch.setattr(strategy_module, "ConfigValue", _StubConfigValue)
    monkeypatch.setattr(strategy_module, "resolve_specification", lambda specification=None: spec)

    strategy = _TestStrategy(repository_or_cls=_FakeRepository(spec))  # type: ignore[arg-type]

    async def _fake_find_candidates(query, properties, limit, proxy):  # pylint: disable=unused-argument
        return [{"score": 2, "id": 1}, {"score": 10, "id": 2}, {"score": 5, "id": 3}]

    monkeypatch.setattr(strategy, "_find_candidates", _fake_find_candidates)
    candidates = await strategy.find_candidates("q", limit=2)
    assert [c["id"] for c in candidates] == [2, 3]


def test_get_display_name_fallback_uses_key_title(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "key": "my_type",
        "id_field": "id",
        "label_field": "label",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }
    monkeypatch.setattr(strategy_module, "ConfigValue", _StubConfigValue)
    monkeypatch.setattr(strategy_module, "resolve_specification", lambda specification=None: spec)
    strategy = _TestStrategy(repository_or_cls=_FakeRepository(spec))  # type: ignore[arg-type]
    assert strategy.get_display_name() == "My Type"


def test_as_candidate_includes_distance_and_threshold(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "key": "my_type",
        "id_field": "id",
        "label_field": "label",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }
    monkeypatch.setattr(strategy_module, "ConfigValue", _StubConfigValue)
    monkeypatch.setattr(strategy_module, "resolve_specification", lambda specification=None: spec)
    strategy = _TestStrategy(repository_or_cls=_FakeRepository(spec))  # type: ignore[arg-type]

    candidate = strategy.as_candidate({"id": 1, "label": "Place", "name_sim": 0.901, "distance_km": 1.234}, query="X")
    assert candidate["id"] == "https://w3id.org/sead/id/my_type/1"
    assert candidate["score"] == 90.1
    assert candidate["match"] is True
    assert candidate["distance_km"] == 1.23

    candidate = strategy.as_candidate({"id": 1, "label": "Place", "name_sim": 1.5}, query="X")
    assert candidate["score"] == 100.0


def test_get_repository_returns_instance(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "key": "my_type",
        "id_field": "id",
        "label_field": "label",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }
    monkeypatch.setattr(strategy_module, "ConfigValue", _StubConfigValue)
    monkeypatch.setattr(strategy_module, "resolve_specification", lambda specification=None: spec)
    repo = _DummyRepoInstance()
    strategy = _TestStrategy(repository_or_cls=repo)  # type: ignore[arg-type]
    assert strategy.get_repository() is repo
    assert strategy.get_repository() is repo


def test_get_repository_builds_from_class_and_caches(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "key": "my_type",
        "id_field": "id",
        "label_field": "label",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }
    monkeypatch.setattr(strategy_module, "ConfigValue", _StubConfigValue)
    monkeypatch.setattr(strategy_module, "resolve_specification", lambda specification=None: spec)

    class RepoWithSpec(_FakeRepository):
        pass

    strategy = _TestStrategy(repository_or_cls=RepoWithSpec)  # type: ignore[arg-type]
    repo1 = strategy.get_repository()
    repo2 = strategy.get_repository()
    assert repo1 is repo2
    assert repo1.specification is spec


def test_get_repository_raises_when_missing(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "key": "no_repo",
        "id_field": "id",
        "label_field": "label",
        "properties": [],
        "property_settings": {},
        "sql_queries": {},
    }
    monkeypatch.setattr(strategy_module, "ConfigValue", _StubConfigValue)
    monkeypatch.setattr(strategy_module, "resolve_specification", lambda specification=None: spec)
    strategy = _NoRepoStrategy(repository_or_cls=None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="No proxy configured for strategy"):
        strategy.get_repository()


def test_strategy_registry_sets_repository_cls(monkeypatch: pytest.MonkeyPatch):
    class LocalRegistry(strategy_module.StrategyRegistry):
        items = {}

    class CustomRepo(_FakeRepository):
        pass

    @LocalRegistry.register(key="k", repository_cls=CustomRepo)
    class LocalStrategy(ReconciliationStrategy):
        repository_cls = _FakeRepository  # type: ignore[assignment]

    assert LocalRegistry.get("k") is LocalStrategy
    assert LocalStrategy.repository_cls is CustomRepo
