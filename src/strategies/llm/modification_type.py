"""Modification type reconciliation strategy using LLM"""

from typing import Any

from loguru import logger

from src.configuration import ConfigValue

from ..query import BaseRepository
from ..strategy import Strategies, StrategySpecification
from .llm_strategy import LLMReconciliationStrategy

# Specification for modification types
SPECIFICATION: StrategySpecification = {
    "key": "modification_type",
    "display_name": "Modification Types",
    "id_field": "modification_type_id",
    "label_field": "modification_type_name",
    "properties": [
        {
            "id": "description",
            "name": "Description",
            "type": "string",
            "description": "Description of the modification type",
        }
    ],
    "property_settings": {},
    "sql_queries": {
        "fuzzy_find_sql": """
            SELECT 
                modification_type_id,
                modification_type_name as label,
                similarity(modification_type_name, %(q)s) as name_sim
            FROM tbl_modification_types
            WHERE modification_type_name %% %(q)s
            ORDER BY name_sim DESC
            LIMIT %(n)s
        """,
        "details_sql": """
            SELECT 
                modification_type_id as "ID",
                modification_type_name as "Name", 
                modification_type_description as "Description"
            FROM tbl_modification_types
            WHERE modification_type_id = %(id)s
        """,
        "get_lookup_data": """
            SELECT 
                modification_type_id,
                modification_type_name,
                modification_type_description
            FROM tbl_modification_types
            ORDER BY modification_type_id
        """,
    },
    "llm_settings": {
        "context_description": (
            "Fossil and specimen modification types in paleontology and archaeology. "
            "These describe how organic matter has been altered or preserved over time, "
            "including processes like carbonization, mineralization, fragmentation, and other "
            "preservation states that affect the physical and chemical properties of specimens."
        ),
    },
}


class ModificationTypeQueryProxy(BaseRepository):
    """Modification type-specific query proxy"""

    async def get_lookup_data(self) -> list[dict[str, Any]]:
        """Fetch all modification types for LLM lookup"""
        return await self.fetch_all(self.specification["sql_queries"]["get_lookup_data"])


@Strategies.register(key="modification_type")
class LLMModificationTypeReconciliationStrategy(LLMReconciliationStrategy):
    """LLM-powered modification type reconciliation strategy"""

    def __init__(self) -> None:
        super().__init__(SPECIFICATION, ModificationTypeQueryProxy)
        logger.info("Initialized ModificationTypeReconciliationStrategy with LLM support")

    def get_context_description(self) -> str:
        """Return context description for modification types"""
        return ConfigValue("policy.modification_type.context", default="").resolve() or ""

    def get_lookup_fields(self) -> list[str]:
        return super().get_lookup_fields() + ["modification_type_description"]

    async def get_lookup_data(self) -> list[dict[str, Any]]:
        """Fetch modification type lookup data"""
        proxy = ModificationTypeQueryProxy(self.specification)
        return await proxy.get_lookup_data()

    async def find_candidates(
        self,
        query: str,
        properties: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find modification type candidates using LLM"""

        logger.info("Finding modification type candidates for: '%s'", query)

        # Use the LLM-powered approach
        candidates: list[dict[str, Any]] = await super().find_candidates(query, properties, limit)

        # Log some details about the results
        if candidates:
            logger.info(
                "LLM found %d candidates, top match: '%s' (score: %.2f)",
                len(candidates),
                candidates[0].get(self.get_label_field()),
                candidates[0].get("name_sim", 0),
            )

            # Log reasoning if available
            if "llm_reasons" in candidates[0]:
                logger.debug("LLM reasoning: %s", candidates[0]["llm_reasons"])
        else:
            logger.info("No candidates found")

        return candidates
