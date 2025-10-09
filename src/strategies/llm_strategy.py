"""Base LLM-powered reconciliation strategy"""

from abc import abstractmethod
from typing import Any, Dict, List, Optional

import psycopg
from loguru import logger

from src.configuration.inject import ConfigValue
from src.llm.providers import Providers
from src.llm.providers.provider import LLMProvider
from src.strategies.query import QueryProxy

from .llm_models import ReconciliationResponse
from .strategy import ReconciliationStrategy, StrategySpecification

# pylint: disable=too-many-locals


class LLMReconciliationStrategy(ReconciliationStrategy):
    """Base class for LLM-powered reconciliation strategies"""

    def __init__(self, specification: StrategySpecification, query_proxy_class: QueryProxy) -> None:
        super().__init__(specification, query_proxy_class)

        provider_name: str = ConfigValue("llm.provider").resolve() or "ollama"
        self.llm_provider: LLMProvider = Providers.items[provider_name]()

        self.prompt_template = ConfigValue("llm.prompts.reconciliation").resolve()

        logger.info(f"Initialized {self.__class__.__name__} with provider: {provider_name}")

    @abstractmethod
    def get_context_description(self) -> str:
        """Return a description of the lookup domain for the LLM context"""

    @abstractmethod
    async def get_lookup_data(self, cursor: psycopg.AsyncCursor) -> List[Dict[str, Any]]:
        """Fetch the lookup data from the database"""

    def format_lookup_data(self, lookup_data: List[Dict[str, Any]]) -> str:
        """Format lookup data as 'id, value' pairs for the prompt"""
        lines = []
        id_field = self.get_entity_id_field()
        label_field = self.get_label_field()

        for row in lookup_data:
            lines.append(f"{row[id_field]}, {row[label_field]}")

        return "\n".join(lines)

    def format_input_data(self, queries: List[str]) -> str:
        """Format input queries as 'id, value' pairs for the prompt"""
        lines = []
        for i, query in enumerate(queries, 1):
            lines.append(f"{i}, {query}")
        return "\n".join(lines)

    async def find_candidates(
        self,
        cursor: psycopg.AsyncCursor,
        query: str,
        properties: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find candidates using LLM-powered reconciliation"""

        logger.info(f"Starting LLM reconciliation for query: '{query}'")

        try:
            # Get lookup data
            lookup_data = await self.get_lookup_data(cursor)
            logger.info(f"Retrieved {len(lookup_data)} lookup entries")

            # Format data for prompt
            context = self.get_context_description()
            formatted_lookup = self.format_lookup_data(lookup_data)
            formatted_input = self.format_input_data([query])

            # Build prompt
            prompt = self.prompt_template.format(context=context, lookup_data=formatted_lookup, data=formatted_input)

            logger.debug(f"Generated prompt length: {len(prompt)} characters")

            # Call LLM with structured output
            response = await self.llm_provider.complete(
                prompt=prompt,
                response_model=ReconciliationResponse,
                max_tokens=ConfigValue("llm.max_tokens").resolve() or 2000,
                temperature=ConfigValue("llm.temperature").resolve() or 0.1,
            )

            logger.info(f"LLM returned response with {len(response.results)} results")

            # Convert LLM response to reconciliation format
            candidates = []
            if response.results:
                result = response.results[0]  # We only sent one query
                for candidate in result.candidates[:limit]:
                    candidates.append(
                        {
                            self.get_entity_id_field(): candidate.id,
                            self.get_label_field(): candidate.value,
                            "name_sim": candidate.score,
                            "llm_reasons": candidate.reasons,
                        }
                    )

            logger.info(f"Returning {len(candidates)} candidates")
            return candidates

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("LLM reconciliation failed: %s", e)
            # Fallback to traditional fuzzy matching
            logger.info("Falling back to traditional fuzzy matching")
            return await super().find_candidates(cursor, query, properties, limit)

    async def find_batch_candidates(
        self,
        cursor: psycopg.AsyncCursor,
        queries: List[str],
        limit: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Find candidates for multiple queries in a single LLM call"""

        logger.info("Starting batch LLM reconciliation for %d queries", len(queries))

        try:
            # Get lookup data
            lookup_data = await self.get_lookup_data(cursor)
            logger.info("Retrieved %d lookup entries", len(lookup_data))

            # Format data for prompt
            context = self.get_context_description()
            formatted_lookup = self.format_lookup_data(lookup_data)
            formatted_input = self.format_input_data(queries)

            # Build prompt
            prompt = self.prompt_template.format(context=context, lookup_data=formatted_lookup, data=formatted_input)

            logger.debug(f"Generated batch prompt length: {len(prompt)} characters")

            # Call LLM with structured output
            response = await self.llm_provider.complete(
                prompt=prompt,
                response_model=ReconciliationResponse,
                max_tokens=ConfigValue("llm.max_tokens").resolve() or 4000,
                temperature=ConfigValue("llm.temperature").resolve() or 0.1,
            )

            logger.info("LLM returned batch response with %d results", len(response.results))

            # Convert LLM response to reconciliation format
            results = {}
            for result in response.results:
                query_index = int(result.input_id) - 1  # Convert back to 0-based index
                if 0 <= query_index < len(queries):
                    query = queries[query_index]
                    candidates = []
                    for candidate in result.candidates[:limit]:
                        candidates.append(
                            {
                                self.get_entity_id_field(): candidate.id,
                                self.get_label_field(): candidate.value,
                                "name_sim": candidate.score,
                                "llm_reasons": candidate.reasons,
                            }
                        )
                    results[query] = candidates

            logger.info("Returning batch results for %d queries", len(results))
            return results

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Batch LLM reconciliation failed: %s", e)
            # Fallback to individual calls
            results = {}
            for query in queries:
                results[query] = await self.find_candidates(cursor, query, limit=limit)
            return results
