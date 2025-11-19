import re
from typing import Any

from .query import EntityRepository
from .strategy import ReconciliationStrategy, Strategies, StrategySpecification

SPECIFICATION: StrategySpecification = {
    "key": "bibliographic_reference",
    "display_name": "Bibliographic References",
    "id_field": "biblio_id",
    "label_field": "full_reference",  # show the whole reference
    "properties": [
        {"id": "doi", "name": "DOI", "type": "string", "description": "Digital Object Identifier"},
        {"id": "isbn", "name": "ISBN", "type": "string", "description": "International Standard Book Number"},
        {"id": "title", "name": "Title", "type": "string", "description": "Title of the work"},
        {"id": "year", "name": "Year", "type": "string", "description": "Publication year"},
        {"id": "authors", "name": "Authors", "type": "string", "description": "Authors of the work"},
        {"id": "full_reference", "name": "Full reference", "type": "string", "description": "Full bibliographic reference"},
        {"id": "bugs_reference", "name": "BUGS reference", "type": "string", "description": "BugsCEP reference"},
    ],
    # "default_types": [{"id": "biblio", "name": "Bibliographic reference"}],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_find_sql": """
        select * from authority.fuzzy_bibliographic_references(%(q)s, %(n)s);
    """,
        "details_sql": """
            select  biblio_id as "ID",
                    bugs_reference as "BUGS Reference",
                    doi as "DOI",
                    isbn as "ISBN",
                    notes as "Notes",
                    title as "Title",
                    year as "Year",
                    authors as "Authors",
                    full_reference as "Full reference",
                    url as "URL"
            from public.tbl_biblio
            where biblio_id = %(id)s::int
    """,
        "isbn_sql": """
            select biblio_id, full_reference as label
            from public.tbl_biblio
            where replace(upper(isbn), '-', '') = %s
            """,
        "doi_sql": """
            select biblio_id, full_reference as label
            from public.tbl_biblio
            where replace(lower(doi), 'https://doi.org/', '') = lower(%s)
               or lower(doi) = lower(%s)
            """,
        "full_reference_sql": """
            select biblio_id, full_reference as label
            from public.tbl_biblio
            where full_reference = %s
            """,
        "title_year_sql": """
            select biblio_id, full_reference as label
            from public.tbl_biblio
            where title = %s and year = %s
            """,
        "bugs_reference_sql": """
            select biblio_id, full_reference as label
            from public.tbl_biblio
            where bugs_reference = %s
            """,
        "full_reference_fuzzy_word_similarity_sql": """
            select entity_id, biblio_id, label, name_sim
            from authority.fuzzy_bibliographic_references(
              p_text => %s, p_limit => %s, p_target_field => 'full_reference',
              p_mode => 'word', p_threshold => %s
            )
            """,
        "authors_fuzzy_sql": """
            select entity_id, biblio_id, label, name_sim
            from authority.fuzzy_bibliographic_references(
              p_text => %s, p_limit => %s, p_target_field => 'authors',
              p_mode => 'word', p_threshold => %s
            )
            """,
        "biblio_ids_sql": """
            select biblio_id, full_reference AS label
            from public.tbl_biblio
            where biblio_id = any(%s)
              and year = %s
        """,
        "full_reference_fuzzy_similarity_sql": """
            select entity_id, biblio_id, label, name_sim
            from authority.fuzzy_bibliographic_references(
              p_text => %s, p_limit => %s, p_target_field => 'full_reference',
              p_mode => 'similarity', p_threshold => %s
            )
            """,
    },
}


class BibliographicReferenceQueryProxy(EntityRepository):

    @staticmethod
    def _norm_isbn(isbn: str | None) -> str | None:
        if not isbn:
            return None
        s = re.sub(r"[^0-9Xx]", "", isbn).upper()
        return s or None

    @staticmethod
    def _norm_doi(doi: str | None) -> str | None:
        if not doi:
            return None
        doi = doi.strip()
        doi = doi.replace("https://doi.org/", "").replace("http://doi.org/", "").strip()
        return doi or None

    async def fetch_by_isbn(self, isbn: str) -> list[dict]:
        norm: str | None = self._norm_isbn(isbn)
        if not norm:
            return []
        rows: list[dict[str, Any]] = await self.fetch_all(self.get_sql_query("isbn_sql"), (norm,))
        return [r | {"name_sim": 1.0} for r in rows]

    async def fetch_by_doi(self, doi: str) -> list[dict]:
        norm: str | None = self._norm_doi(doi)
        if not norm:
            return []
        rows: list[dict[str, Any]] = await self.fetch_all(self.get_sql_query("doi_sql"), (norm, norm))
        return [r | {"name_sim": 1.0} for r in rows]

    async def fetch_by_exact_full_reference(self, full_reference: str) -> list[dict]:
        rows: list[dict[str, Any]] = await self.fetch_all(self.get_sql_query("full_reference_sql"), (full_reference,))
        return [r | {"name_sim": 1.0} for r in rows]

    async def fetch_by_exact_title_year(self, title: str, year: str | int) -> list[dict]:
        rows: list[dict[str, Any]] = await self.fetch_all(self.get_sql_query("title_year_sql"), (title, str(year)))
        return [r | {"name_sim": 1.0} for r in rows]

    async def fetch_by_exact_bugs_reference(self, bugs: str) -> list[dict]:
        rows: list[dict[str, Any]] = await self.fetch_all(self.get_sql_query("bugs_reference_sql"), (bugs,))
        return [r | {"name_sim": 1.0} for r in rows]

    # --- fuzzy lookups -------------------------------------------

    async def fuzzy_full_reference_partial(self, text: str, limit: int, threshold: float = 0.45) -> list[dict]:
        # best-substring match on full_reference
        rows: list[dict[str, Any]] = await self.fetch_all(self.get_sql_query("full_reference_fuzzy_word_similarity_sql"), (text, limit, threshold))
        return [r | {"name_sim": max(0.8, float(r["name_sim"]))} for r in rows]

    async def fuzzy_authors_partial_and_year(self, authors: str, year: str | int, limit: int, threshold: float = 0.45) -> list[dict]:
        rows: list[dict[str, Any]] = await self.fetch_all(self.get_sql_query("authors_fuzzy_sql"), params=(authors, limit, threshold), row_factory="tuple")
        # filter to exact year; promote to 0.8 if matches
        ids: list[int] = [r[1] for r in rows]  # type: ignore
        if not ids:
            return []
        year_ok: dict[str, Any] | None = await self.fetch_one(self.get_sql_query("biblio_ids_sql"), params=(ids, str(year)), row_factory="tuple")
        out = []
        for r in rows:
            bid, label, sim = r[1], r[2], float(r[3])  # type: ignore
            if year_ok and bid in year_ok:
                out.append({"biblio_id": bid, "label": label, "name_sim": max(0.8, sim)})
        return out

    # async def fuzzy_title_partial_and_year(self, title: str, year: str | int, limit: int,
    #                                        threshold: float = 0.45) -> list[dict]:
    #     rows = await self.fetch_all(
    #         """
    #         SELECT entity_id, biblio_id, label, name_sim
    #         FROM authority.fuzzy_bibliographic_references(
    #           p_text => %s, p_limit => %s, p_target_field => 'title',
    #           p_mode => 'word', p_threshold => %s
    #         )
    #         """,
    #         (title, limit, threshold), row_factory='tuple
    #     )
    #     ids = [r[1] for r in rows]
    #     if not ids:
    #         return []
    #     await self.cursor.execute(self.get_sql_query("biblio_ids_sql"), (ids, str(year)))
    #     has_year = {r[0] for r in await self.cursor.fetchall()}
    #     out = []
    #     for r in rows:
    #         bid, label, sim = r[1], r[2], float(r[3])
    #         if bid in has_year:
    #             out.append({"biblio_id": bid, "label": label, "name_sim": max(0.8, sim)})
    #     return out

    async def fuzzy_full_reference_fallback(self, text: str, limit: int, threshold: float = 0.30) -> list[dict]:
        rows: list[dict[str, Any]] = await self.fetch_all(self.get_sql_query("full_reference_fuzzy_similarity_sql"), (text, limit, threshold))
        return [r | {"name_sim": min(0.7, float(r["name_sim"]))} for r in rows]


@Strategies.register(key="bibliographic_reference")
class BibliographicReferenceReconciliationStrategy(ReconciliationStrategy):
    """Reconcile bibliographic references using exact identifiers and fuzzy text."""

    def __init__(self):
        super().__init__(SPECIFICATION, BibliographicReferenceQueryProxy)

    @staticmethod
    def _as_openrefine_candidate(row: dict) -> dict:
        # Convert 0..1 to 0..100, set match if >= 0.99
        score01 = float(row.get("name_sim", 0.0))
        score = max(0.0, min(100.0, round(score01 * 100, 1)))
        return {
            "id": row["biblio_id"],
            "name": row.get("label") or "",
            "score": score,
            "match": score01 >= 0.99,
            "type": [{"id": "biblio", "name": "Bibliographic reference"}],
        }

    @staticmethod
    def _merge_max(cands: list[dict]) -> list[dict]:
        best: dict[int, dict] = {}
        for c in cands:
            bid = int(c["biblio_id"])
            prev = best.get(bid)
            if not prev or c["name_sim"] > prev["name_sim"]:
                best[bid] = c
        return list(best.values())

    async def find_candidates(
        self,
        query: str,
        properties: dict[str, object] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        props = properties or {}
        candidates: list[dict] = []
        proxy: BibliographicReferenceQueryProxy = self.get_proxy()  # type: ignore
        # 1) High-confidence exact identifiers
        if props.get("isbn"):
            candidates.extend(await proxy.fetch_by_isbn(str(props["isbn"])))
        if props.get("doi"):
            candidates.extend(await proxy.fetch_by_doi(str(props["doi"])))
        if props.get("full_reference"):
            candidates.extend(await proxy.fetch_by_exact_full_reference(str(props["full_reference"])))
        if props.get("title") and props.get("year"):
            candidates.extend(await proxy.fetch_by_exact_title_year(str(props["title"]), str(props["year"])))
        if props.get("bugs_reference"):
            candidates.extend(await proxy.fetch_by_exact_bugs_reference(str(props["bugs_reference"])))

        # 2) Strong fuzzy / partial passes (0.8 floor)
        if props.get("full_reference"):
            candidates.extend(await proxy.fuzzy_full_reference_partial(str(props["full_reference"]), limit=limit))
        if props.get("authors") and props.get("year"):
            candidates.extend(await proxy.fuzzy_authors_partial_and_year(str(props["authors"]), str(props["year"]), limit=limit))

        # Optional but useful: title+year partial
        # if props.get("title") and props.get("year"):
        #     candidates.extend(await self.get_proxy().fuzzy_title_partial_and_year(str(props["title"]), str(props["year"]), limit=limit))

        # 3) Fallback: fuzzy on the free-text `query` (from the front-end)
        # If query is provided and not obviously identical to a property, try full_reference
        if query and not props.get("full_reference"):
            candidates.extend(await proxy.fuzzy_full_reference_partial(query, limit=limit))
            # If still thin, add overall similarity (lower confidence cap)
            if len(candidates) < limit:
                candidates.extend(await proxy.fuzzy_full_reference_fallback(query, limit=limit))

        # 4) Merge, cap, and convert to OpenRefine candidates
        merged = self._merge_max(candidates)
        merged.sort(key=lambda x: x.get("name_sim", 0.0), reverse=True)
        return [self._as_openrefine_candidate(c) for c in merged[:limit]]
