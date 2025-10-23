from typing import Any, Iterable, Literal, Self

import httpx


class NotSupportedError(Exception):
    """Exception for unsupported operations"""


class GeoNamesProxy:
    """
    Minimal async proxy around the GeoNames API using httpx.

    Usage:
        async with GeoNamesProxy("YOUR_USERNAME") as gn:
            hits = await gn.geonames_search("Umeå", country_bias="SE")
            detail = await gn._get_details(hits[0]["geonameId"])
    """

    def __init__(
        self,
        *,
        username: str,
        base_url: str = "https://api.geonames.org",
        lang: str = "en",
        timeout: float = 20.0,
        # add a proper user_agent identifying your application and contact info
        user_agent: str = "sead-GeonamesProxy/1.0 (contact: https://sead.se)",
    ) -> None:
        self.username: str = username
        self.base_url: str = base_url.rstrip("/")
        self.lang: str = lang
        self.timeout: float = timeout
        self.user_agent: str = user_agent
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> Self:
        self._client = httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": self.user_agent})
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def search(
        self,
        q: str,
        *,
        max_rows: int = 10,
        country_bias: str | None = None,
        lang: str | None = None,
        feature_classes: Iterable[str] = ("P", "A"),
        fuzzy: float = 0.8,
        orderby: Literal["relevance", "population"] = "relevance",
        style: Literal["FULL", "SHORT", "MEDIUM", "LONG"] = "FULL",
        extra_params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for places. Returns list of GeoNames dictionaries.
        See https://www.geonames.org/export/geonames-search.html for parameter details.
        q: The search query (place name)
        max_rows: Maximum number of results to return (max 1000)
        country_bias: Optional 2-letter country code to bias results
        lang: Optional language code for returned names (default is 'en')
        feature_classes: Iterable of feature classes to include (e.g. 'P' for populated places)
            available classes: A (Administrative), H (Hydrographic), L (Area), P (Populated place)
        fuzzy: Fuzzy matching threshold (0.0 to 1.0)
        orderby: 'relevance' or 'population' (note: 'population' not supported in free service)
        style: Level of detail in returned results
        """
        params: list[tuple[str, str | int | float]] = [
            ("q", q),
            ("maxRows", max_rows),
            ("lang", (lang or self.lang)),
            ("username", self.username),
            ("type", "json"),
            ("style", style),
            ("orderby", orderby),
            ("fuzzy", fuzzy),
        ]

        # Multiple featureClass params are allowed by GeoNames
        for fc in feature_classes:
            params.append(("featureClass", fc))

        if country_bias:
            params.append(("countryBias", country_bias))

        if extra_params:
            for k, v in extra_params.items():
                params.append((k, v))

        data = await self._get_json("/searchJSON", params)
        return data.get("geonames", [])

    async def get_details(
        self,
        geoname_id: int | str,
        *,
        lang: str | None = None,
        style: str = "FULL",
        extra_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Fetch details for a specific geonameId.
        """
        params: list[tuple[str, str | int]] = [
            ("geonameId", int(geoname_id)),
            ("username", self.username),
            ("lang", (lang or self.lang)),
            ("type", "json"),
            ("style", style),
        ]

        if extra_params:
            for k, v in extra_params.items():
                params.append((k, v))

        return await self._get_json("/getJSON", params)

    async def _get_json(self, path: str, params: list[tuple[str, Any]]) -> dict[str, Any]:
        """
        Internal GET helper with basic GeoNames error normalization.
        """
        if self._client is None:
            # Fallback: create a one-shot client if used without context manager
            async with httpx.AsyncClient(timeout=self.timeout, headers={"User-Agent": self.user_agent}) as client:
                resp: httpx.Response = await client.get(f"{self.base_url}{path}", params=params)
                data: dict[str, Any] = self._ensure_ok(resp)
                return data

        resp = await self._client.get(f"{self.base_url}{path}", params=params)
        data = self._ensure_ok(resp)
        return data

    @staticmethod
    def _ensure_ok(resp: httpx.Response) -> dict[str, Any]:
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "status" in data:
            # GeoNames encodes errors as {"status": {"message": "...", "value": <code>}}
            msg = data["status"].get("message", "GeoNames API error")
            code = data["status"].get("value", "unknown")
            raise RuntimeError(f"GeoNames error {code}: {msg}")
        return data
