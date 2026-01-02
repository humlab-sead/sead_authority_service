from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.strategies.bibliographic_reference import (
    BibliographicReferenceReconciliationStrategy,
    BibliographicReferenceRepository,
)
from src.strategies.query import BaseRepository
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config


class _FakeBiblioRepo(BaseRepository):
    def __init__(self):
        self.fetch_by_isbn = AsyncMock()
        self.fetch_by_doi = AsyncMock()
        self.fetch_by_exact_full_reference = AsyncMock()
        self.fetch_by_exact_title_year = AsyncMock()
        self.fetch_by_exact_bugs_reference = AsyncMock()
        self.fuzzy_full_reference_partial = AsyncMock()
        self.fuzzy_authors_partial_and_year = AsyncMock()
        self.fuzzy_full_reference_fallback = AsyncMock()


class TestBibliographicReferenceRepository:
    def test_norm_isbn(self):
        assert BibliographicReferenceRepository._norm_isbn(None) is None
        assert BibliographicReferenceRepository._norm_isbn("") is None
        assert BibliographicReferenceRepository._norm_isbn("  ") is None
        assert BibliographicReferenceRepository._norm_isbn("978-0-306-40615-7") == "9780306406157"
        assert BibliographicReferenceRepository._norm_isbn("0 306 40615 2") == "0306406152"
        assert BibliographicReferenceRepository._norm_isbn("x") == "X"

    def test_norm_doi(self):
        assert BibliographicReferenceRepository._norm_doi(None) is None
        assert BibliographicReferenceRepository._norm_doi("") is None
        assert BibliographicReferenceRepository._norm_doi("  ") is None
        assert BibliographicReferenceRepository._norm_doi("10.1000/xyz") == "10.1000/xyz"
        assert BibliographicReferenceRepository._norm_doi(" https://doi.org/10.1000/xyz ") == "10.1000/xyz"
        assert BibliographicReferenceRepository._norm_doi("http://doi.org/10.1000/xyz") == "10.1000/xyz"

    @pytest.mark.asyncio
    async def test_fetch_by_isbn_returns_empty_for_invalid(self, monkeypatch: pytest.MonkeyPatch):
        repo = BibliographicReferenceRepository.__new__(BibliographicReferenceRepository)
        monkeypatch.setattr(repo, "get_sql_query", lambda key: "SQL")  # noqa: ARG005
        fetch_all = AsyncMock(return_value=[{"biblio_id": 1, "label": "X"}])
        monkeypatch.setattr(repo, "fetch_all", fetch_all)

        assert await repo.fetch_by_isbn("") == []
        fetch_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_by_isbn_sets_name_sim(self, monkeypatch: pytest.MonkeyPatch):
        repo = BibliographicReferenceRepository.__new__(BibliographicReferenceRepository)
        monkeypatch.setattr(repo, "get_sql_query", lambda key: "SQL")  # noqa: ARG005
        fetch_all = AsyncMock(return_value=[{"biblio_id": 1, "label": "A"}])
        monkeypatch.setattr(repo, "fetch_all", fetch_all)

        rows = await repo.fetch_by_isbn("978-0-306-40615-7")
        assert rows == [{"biblio_id": 1, "label": "A", "name_sim": 1.0}]
        fetch_all.assert_awaited_once_with("SQL", ("9780306406157",))

    @pytest.mark.asyncio
    async def test_fetch_by_doi_sets_name_sim(self, monkeypatch: pytest.MonkeyPatch):
        repo = BibliographicReferenceRepository.__new__(BibliographicReferenceRepository)
        monkeypatch.setattr(repo, "get_sql_query", lambda key: "SQL")  # noqa: ARG005
        fetch_all = AsyncMock(return_value=[{"biblio_id": 1, "label": "A"}])
        monkeypatch.setattr(repo, "fetch_all", fetch_all)

        rows = await repo.fetch_by_doi(" https://doi.org/10.1000/xyz ")
        assert rows == [{"biblio_id": 1, "label": "A", "name_sim": 1.0}]
        fetch_all.assert_awaited_once_with("SQL", ("10.1000/xyz", "10.1000/xyz"))

    @pytest.mark.asyncio
    async def test_fuzzy_full_reference_partial_applies_floor(self, monkeypatch: pytest.MonkeyPatch):
        repo = BibliographicReferenceRepository.__new__(BibliographicReferenceRepository)
        monkeypatch.setattr(repo, "get_sql_query", lambda key: "SQL")  # noqa: ARG005
        fetch_all = AsyncMock(return_value=[{"biblio_id": 1, "label": "A", "name_sim": 0.1}, {"biblio_id": 2, "label": "B", "name_sim": 0.95}])
        monkeypatch.setattr(repo, "fetch_all", fetch_all)

        rows = await repo.fuzzy_full_reference_partial("foo", limit=10, threshold=0.45)
        assert rows[0]["name_sim"] == 0.8
        assert rows[1]["name_sim"] == 0.95

    @pytest.mark.asyncio
    async def test_fuzzy_full_reference_fallback_caps(self, monkeypatch: pytest.MonkeyPatch):
        repo = BibliographicReferenceRepository.__new__(BibliographicReferenceRepository)
        monkeypatch.setattr(repo, "get_sql_query", lambda key: "SQL")  # noqa: ARG005
        fetch_all = AsyncMock(return_value=[{"biblio_id": 1, "label": "A", "name_sim": 0.9}, {"biblio_id": 2, "label": "B", "name_sim": 0.2}])
        monkeypatch.setattr(repo, "fetch_all", fetch_all)

        rows = await repo.fuzzy_full_reference_fallback("foo", limit=10, threshold=0.30)
        assert rows[0]["name_sim"] == 0.7
        assert rows[1]["name_sim"] == 0.2

    @pytest.mark.asyncio
    async def test_fuzzy_authors_partial_and_year_filters_by_year(self, monkeypatch: pytest.MonkeyPatch):
        repo = BibliographicReferenceRepository.__new__(BibliographicReferenceRepository)
        monkeypatch.setattr(repo, "get_sql_query", lambda key: "SQL")  # noqa: ARG005
        fetch_all = AsyncMock(
            return_value=[
                ("e1", 10, "A", 0.5),
                ("e2", 11, "B", 0.9),
            ]
        )
        fetch_one = AsyncMock(return_value={10: True})
        monkeypatch.setattr(repo, "fetch_all", fetch_all)
        monkeypatch.setattr(repo, "fetch_one", fetch_one)

        rows = await repo.fuzzy_authors_partial_and_year("Smith", year="2020", limit=10, threshold=0.45)
        assert rows == [{"biblio_id": 10, "label": "A", "name_sim": 0.8}]


class TestBibliographicReferenceReconciliationStrategy:
    def test_as_openrefine_candidate_scoring(self):
        c = BibliographicReferenceReconciliationStrategy._as_openrefine_candidate({"biblio_id": 1, "label": "A", "name_sim": 1.0})
        assert c["score"] == 100.0
        assert c["match"] is True

        c = BibliographicReferenceReconciliationStrategy._as_openrefine_candidate({"biblio_id": 1, "label": "A", "name_sim": 0.0})
        assert c["score"] == 0.0
        assert c["match"] is False

        c = BibliographicReferenceReconciliationStrategy._as_openrefine_candidate({"biblio_id": 1, "label": "A", "name_sim": 2.0})
        assert c["score"] == 100.0

        c = BibliographicReferenceReconciliationStrategy._as_openrefine_candidate({"biblio_id": 1, "label": None, "name_sim": -1.0})
        assert c["name"] == ""
        assert c["score"] == 0.0

    def test_merge_max(self):
        rows = [
            {"biblio_id": 1, "label": "A", "name_sim": 0.6},
            {"biblio_id": 1, "label": "A2", "name_sim": 0.9},
            {"biblio_id": 2, "label": "B", "name_sim": 0.7},
        ]
        merged = BibliographicReferenceReconciliationStrategy._merge_max(rows)
        merged.sort(key=lambda r: r["biblio_id"])
        assert merged == [{"biblio_id": 1, "label": "A2", "name_sim": 0.9}, {"biblio_id": 2, "label": "B", "name_sim": 0.7}]

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_properties_paths_skip_query_fallback(self, test_provider: ExtendedMockConfigProvider):
        proxy = _FakeBiblioRepo()
        proxy.fetch_by_isbn.return_value = [{"biblio_id": 1, "label": "ISBN", "name_sim": 1.0}]
        proxy.fetch_by_doi.return_value = [{"biblio_id": 2, "label": "DOI", "name_sim": 1.0}]
        proxy.fetch_by_exact_full_reference.return_value = [{"biblio_id": 3, "label": "FULL", "name_sim": 1.0}]
        proxy.fetch_by_exact_title_year.return_value = [{"biblio_id": 4, "label": "TITLEYEAR", "name_sim": 1.0}]
        proxy.fetch_by_exact_bugs_reference.return_value = [{"biblio_id": 5, "label": "BUGS", "name_sim": 1.0}]
        proxy.fuzzy_full_reference_partial.return_value = [{"biblio_id": 3, "label": "FULL", "name_sim": 0.8}]
        proxy.fuzzy_authors_partial_and_year.return_value = [{"biblio_id": 6, "label": "AUTH", "name_sim": 0.85}]
        proxy.fuzzy_full_reference_fallback.return_value = [{"biblio_id": 7, "label": "FB", "name_sim": 0.5}]

        strategy = BibliographicReferenceReconciliationStrategy(repository_or_cls=proxy)  # type: ignore[arg-type]
        results = await strategy.find_candidates(
            query="free text",
            properties={
                "isbn": "978-0-306-40615-7",
                "doi": "10.1000/xyz",
                "full_reference": "A ref",
                "title": "T",
                "year": "2020",
                "bugs_reference": "B123",
                "authors": "Smith",
            },
            limit=10,
        )

        assert {r["id"] for r in results} >= {1, 2, 3, 4, 5, 6}
        proxy.fuzzy_full_reference_fallback.assert_not_awaited()

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_query_fallback_and_dedup(self, test_provider: ExtendedMockConfigProvider):
        proxy = _FakeBiblioRepo()
        proxy.fetch_by_isbn.return_value = []
        proxy.fetch_by_doi.return_value = []
        proxy.fetch_by_exact_full_reference.return_value = []
        proxy.fetch_by_exact_title_year.return_value = []
        proxy.fetch_by_exact_bugs_reference.return_value = []
        proxy.fuzzy_full_reference_partial.return_value = [
            {"biblio_id": 1, "label": "A", "name_sim": 0.9},
            {"biblio_id": 1, "label": "A", "name_sim": 0.6},
        ]
        proxy.fuzzy_full_reference_fallback.return_value = [{"biblio_id": 2, "label": "B", "name_sim": 0.4}]
        proxy.fuzzy_authors_partial_and_year.return_value = []

        strategy = BibliographicReferenceReconciliationStrategy(repository_or_cls=proxy)  # type: ignore[arg-type]
        results = await strategy.find_candidates(query="free text", properties={}, limit=10)

        assert [r["id"] for r in results] == [1, 2]
        assert results[0]["score"] == 90.0
        proxy.fuzzy_full_reference_fallback.assert_awaited()

    @pytest.mark.asyncio
    @with_test_config
    async def test_find_candidates_does_not_call_fallback_when_enough(self, test_provider: ExtendedMockConfigProvider):
        proxy = _FakeBiblioRepo()
        proxy.fetch_by_isbn.return_value = []
        proxy.fetch_by_doi.return_value = []
        proxy.fetch_by_exact_full_reference.return_value = []
        proxy.fetch_by_exact_title_year.return_value = []
        proxy.fetch_by_exact_bugs_reference.return_value = []
        proxy.fuzzy_authors_partial_and_year.return_value = []
        proxy.fuzzy_full_reference_partial.return_value = [
            {"biblio_id": i, "label": f"R{i}", "name_sim": 0.9} for i in range(10)
        ]
        proxy.fuzzy_full_reference_fallback.return_value = [{"biblio_id": 99, "label": "FB", "name_sim": 0.5}]

        strategy = BibliographicReferenceReconciliationStrategy(repository_or_cls=proxy)  # type: ignore[arg-type]
        results = await strategy.find_candidates(query="free text", properties={}, limit=5)

        assert len(results) == 5
        proxy.fuzzy_full_reference_fallback.assert_not_awaited()
