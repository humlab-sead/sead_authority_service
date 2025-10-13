"""Base LLM-powered reconciliation strategy"""

from abc import abstractmethod
from typing import Any

import psycopg
from loguru import logger
from jinja2 import Environment, BaseLoader

from src.configuration import ConfigValue
from src.llm.providers import Providers
from src.llm.providers.provider import LLMProvider
from src.strategies.query import QueryProxy
from src.strategies.strategy import ReconciliationStrategy, StrategySpecification

from .format_data import format_rows_for_llm
from .llm_models import ReconciliationResponse

# pylint: disable=too-many-locals

JINJA = Environment(loader=BaseLoader(), autoescape=False)

class LLMReconciliationStrategy(ReconciliationStrategy):
    """Base class for LLM-powered reconciliation strategies"""

    def __init__(self, specification: StrategySpecification, query_proxy_class: QueryProxy) -> None:
        super().__init__(specification, query_proxy_class)

        provider_name: str = ConfigValue("llm.provider").resolve() or "ollama"
        self.llm_provider: LLMProvider = Providers.items[provider_name]()

        self.prompt_template: str = ConfigValue("llm.prompts.reconciliation").resolve()

        logger.info(f"Initialized {self.__class__.__name__} with provider: {provider_name}")

    def get_entity_type_description(self) -> str:
        return ConfigValue(f"policy.{self.key}.entity_type_description").resolve() or self.key.replace("_", " ")

    def get_lookup_format(self) -> str:
        return ConfigValue(f"policy.{self.key}.lookup_format", default="auto").resolve() or "auto"

    def get_lookup_fields_map(self) -> dict[str, str]:
        return ConfigValue(f"policy.{self.key}.lookup_fields_map", default={}).resolve() or {}

    @abstractmethod
    def get_context_description(self) -> str:
        """Return a description of the lookup domain for the LLM context"""

    @abstractmethod
    async def get_lookup_data(self, cursor: psycopg.AsyncCursor) -> list[dict[str, Any]]:
        """Fetch the lookup data from the database"""

    def get_lookup_fields(self) -> list[str]:
        """Return the fields to include in the lookup data"""
        return [self.get_entity_id_field(), self.get_label_field()]

    def format_lookup_data(self, lookup_data: list[dict[str, Any]]) -> str:
        """Format lookup data as 'id, value' pairs for the prompt"""
        fields: list[str] = self.get_lookup_fields()
        lines: list[str] = [", ".join(f"{row[f]}" for f in fields) for row in lookup_data]
        return "\n".join(lines)

    async def generate_llm_prompt(self, cursor, query):
        lookup_data: list[dict[str, Any]] = await self.get_lookup_data(cursor)
        logger.info(f"Retrieved {len(lookup_data)} lookup entries")

        lookup_format, lookup_text = format_rows_for_llm(
            lookup_data,
            target_format=self.get_lookup_format(),
            column_map=self.get_lookup_fields_map() or None,
        )
        _, data_text = format_rows_for_llm(
            [{"input_id": 1, "input_value": query}],
            target_format=lookup_format,
            logical_keys=["input_id", "input_value"],
        )
        # What to do with properties? For now we ignore them

        template = JINJA.from_string(self.prompt_template)
        prompt = template.render(
            entity_type=self.get_entity_type_description(),
            context=self.get_context_description(),
            lookup_format=lookup_format.upper(),
            lookup_data=lookup_text,
            data=data_text,
        )
        logger.debug(f"Generated prompt length: {len(prompt)} characters")
        return prompt

    async def find_candidates(
        self,
        cursor: psycopg.AsyncCursor,
        query: str,
        properties: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find candidates using LLM-powered reconciliation"""

        logger.info(f"Starting LLM reconciliation for query: '{query}'")

        # try:
        prompt: str = await self.generate_llm_prompt(cursor, query)

        extra_roles: dict[str, str] = ConfigValue(f"policy.{self.key}.roles,policy.roles").resolve() or {}
        max_tokens: int = ConfigValue(f"llm.{self.llm_provider.key}.max_tokens,llm.max_tokens").resolve() or 20000
        temperature: float = ConfigValue(f"llm.{self.llm_provider.key}.temperature,llm.temperature").resolve() or 0.1

        response: str = await self.llm_provider.complete(
            prompt=prompt,
            roles=extra_roles,
            response_model=ReconciliationResponse,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # logger.info(f"LLM returned response with {len(response)} results")

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

        # except Exception as e:  # pylint: disable=broad-exception-caught
        #     logger.error("LLM reconciliation failed: %s", e)
        #     logger.info("Falling back to traditional fuzzy matching")
        #     return await super().find_candidates(cursor, query, properties, limit)

    async def find_batch_candidates(
        self,
        cursor: psycopg.AsyncCursor,
        queries: list[str],
        limit: int = 10,
    ) -> dict[str, list[dict[str, Any]]]:
        """Find candidates for multiple queries in a single LLM call"""

        logger.info("Starting batch LLM reconciliation for %d queries", len(queries))

        try:
            # Get lookup data
            lookup_data: list[dict[str, Any]] = await self.get_lookup_data(cursor)
            logger.info("Retrieved %d lookup entries", len(lookup_data))

            # Format data for prompt
            context: str = self.get_context_description()
            formatted_lookup: str = self.format_lookup_data(lookup_data)
            formatted_input: str = self.format_input_data(queries)

            # Build prompt
            prompt: str = self.prompt_template.format(context=context, lookup_data=formatted_lookup, data=formatted_input)

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
                query_index: int = int(result.input_id) - 1  # Convert back to 0-based index
                if 0 <= query_index < len(queries):
                    query: str = queries[query_index]
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
