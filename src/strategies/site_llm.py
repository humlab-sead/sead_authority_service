# SITE_PROMPT = """
# You are an expert at matching archaeological and geographic site names.

# I need to find the best matches for this query: "{query}"

# Here are the candidate sites:
# {candidate_text}

# Please analyze the query and return the top {limit} best matches in JSON format.
# Consider:
# - Exact name matches (highest priority)
# - Similar names with spelling variations
# - Alternative names or translations
# - Geographic proximity hints
# - Historical name variations

# Return only a JSON array with this format:
# [
#   {{"site_id": 123, "confidence": 0.95, "reason": "Exact match"}},
#   {{"site_id": 456, "confidence": 0.82, "reason": "Very similar name with minor spelling difference"}}
# ]

# Be conservative with confidence scores. Only use scores above 0.8 for very strong matches.
# """

# """
# LLM-enhanced site reconciliation strategy.

# Provides two advanced matching modes:
# 1. Translation-enhanced fuzzy matching
# 2. AI-powered semantic matching using LLM context
# """

# import asyncio
# import json
# import logging
# from dataclasses import dataclass
# from typing import Any, Dict, List, Optional

# import psycopg

# from src.configuration.inject import ConfigValue
# from src.llm.cache import TranslationCache
# from src.llm.providers.client import LLMClient
# from src.llm.translation import TranslationService
# from src.strategies.query import QueryProxy
# from src.strategies.strategy import ReconciliationStrategy

# logger = logging.getLogger(__name__)


# class LLMClient:
#     """Main LLM client with provider abstraction"""

#     def __init__(self, provider: str = "openai"):

#         if Providers.get(provider) is None:
#             raise ValueError(f"None or unsupported LLM provider: {provider or 'None'}")

#         self.provider: LLMProvider = Providers.get(provider)()

#     async def find_semantic_matches(self, prompt: str, query: str, candidates: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
#         """Use LLM to find semantic matches from candidate pool"""

#         # Prepare candidates for LLM context
#         candidate_text = "\n".join(
#             [f"ID: {c['site_id']}, Name: {c.get('label', '')}, Location: {c.get('place_name', '')}" for c in candidates[: self.config.semantic_batch_size]]
#         )
#         prompt = prompt.replace("{{query}}", query)
#         prompt = prompt.replace("{{candidates}}", candidate_text)
#         prompt = prompt.replace("{{limit}}", str(limit))

#         try:
#             response = await self.provider.complete(prompt, max_tokens=self.config.max_tokens, temperature=self.config.temperature)

#             # Parse LLM response
#             matches = json.loads(response.strip())

#             # Merge with original candidate data
#             results = []
#             for match in matches:
#                 site_id = match["site_id"]
#                 candidate: dict[str, Any] | None = next((c for c in candidates if c["site_id"] == site_id), None)
#                 if candidate:
#                     candidate["semantic_score"] = match["confidence"]
#                     candidate["semantic_reason"] = match["reason"]
#                     candidate["name_sim"] = match["confidence"]  # For compatibility
#                     results.append(candidate)

#             return results[:limit]

#         except Exception as e:
#             logger.error(f"LLM semantic matching failed: {e}")
#             return []


# @dataclass
# class LLMConfig:
#     """Configuration for LLM services"""

#     provider: str  # "openai", "anthropic", "ollama", "azure"
#     model: str  # "gpt-4", "claude-3-sonnet", "llama2", etc.
#     api_key: Optional[str] = None
#     base_url: Optional[str] = None  # For local/custom endpoints
#     max_tokens: int = 1000
#     temperature: float = 0.1  # Low temperature for consistent matching
#     enable_translation: bool = True
#     enable_semantic_matching: bool = True
#     translation_target_lang: str = "en"  # Target language for translation
#     semantic_batch_size: int = 50  # Max records to include in LLM context


# class SiteLLMQueryProxy(QueryProxy):
#     """Query proxy with LLM-enhanced capabilities"""

#     def __init__(self, specification: dict[str, Any], cursor: psycopg.AsyncCursor):
#         super().__init__(specification, cursor)
#         self.llm_config = self._load_llm_config()
#         self.llm_client = LLMClient(self.llm_config)
#         self.translation_service = TranslationService(self.llm_client)
#         self.translation_cache = TranslationCache()

#     def _load_llm_config(self) -> LLMConfig:
#         """Load LLM configuration from config"""
#         return LLMConfig(
#             provider=ConfigValue("llm:provider", "openai").resolve(),
#             model=ConfigValue("llm:model", "gpt-3.5-turbo").resolve(),
#             api_key=ConfigValue("llm:api_key").resolve(),
#             base_url=ConfigValue("llm:base_url").resolve(),
#             max_tokens=ConfigValue("llm:max_tokens", 1000).resolve(),
#             temperature=ConfigValue("llm:temperature", 0.1).resolve(),
#             enable_translation=ConfigValue("llm:enable_translation", True).resolve(),
#             enable_semantic_matching=ConfigValue("llm:enable_semantic_matching", True).resolve(),
#             translation_target_lang=ConfigValue("llm:translation_target_lang", "en").resolve(),
#             semantic_batch_size=ConfigValue("llm:semantic_batch_size", 50).resolve(),
#         )

#     async def fetch_with_translation(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
#         """
#         Use Case 1: Translation-enhanced fuzzy matching

#         1. Detect source language
#         2. Translate to target language if needed
#         3. Perform fuzzy search with translated query
#         4. Return results with translation metadata
#         """
#         logger.info(f"Starting translation-enhanced search for: {query}")

#         # Check cache first
#         cached_translation = await self.translation_cache.get(query, self.llm_config.translation_target_lang)
#         if cached_translation:
#             translated_query = cached_translation
#             logger.info(f"Using cached translation: {translated_query}")
#         else:
#             # Detect and translate
#             try:
#                 detection = await self.translation_service.detect_language(query)
#                 logger.info(f"Detected language: {detection.language} (confidence: {detection.confidence})")

#                 if detection.language != self.llm_config.translation_target_lang and detection.confidence > 0.7:
#                     translated_query = await self.translation_service.translate(
#                         query, source_lang=detection.language, target_lang=self.llm_config.translation_target_lang
#                     )
#                     # Cache the translation
#                     await self.translation_cache.set(query, self.llm_config.translation_target_lang, translated_query)
#                     logger.info(f"Translated '{query}' to '{translated_query}'")
#                 else:
#                     translated_query = query
#                     logger.info("No translation needed")
#             except Exception as e:
#                 logger.warning(f"Translation failed, using original query: {e}")
#                 translated_query = query

#         # Perform fuzzy search with translated query
#         results = await self.fetch_by_fuzzy_name_search(translated_query, limit)

#         # Add translation metadata to results
#         for result in results:
#             result["translation_used"] = translated_query != query
#             result["original_query"] = query
#             result["translated_query"] = translated_query

#         return results

#     async def fetch_with_semantic_matching(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
#         """
#         Use Case 2: AI-powered semantic matching

#         1. Load candidate records from database
#         2. Use LLM to find best semantic matches
#         3. Return results with AI confidence scores
#         """
#         logger.info(f"Starting semantic matching for: {query}")

#         # Get candidate records (broader search)
#         candidates = await self.fetch_candidate_pool(query, self.llm_config.semantic_batch_size)

#         if not candidates:
#             logger.info("No candidates found for semantic matching")
#             return []

#         # Use LLM for semantic matching
#         try:
#             semantic_matches = await self.llm_client.find_semantic_matches(query=query, candidates=candidates, limit=limit)

#             logger.info(f"LLM found {len(semantic_matches)} semantic matches")
#             return semantic_matches

#         except Exception as e:
#             logger.error(f"Semantic matching failed: {e}")
#             # Fallback to traditional fuzzy search
#             return await self.fetch_by_fuzzy_name_search(query, limit)

#     async def fetch_candidate_pool(self, query: str, max_candidates: int) -> List[Dict[str, Any]]:
#         """Load broader set of candidates for semantic matching"""
#         # Use multiple search strategies to build candidate pool
#         candidates = []

#         # 1. Fuzzy search with broader threshold
#         fuzzy_results = await self.fetch_by_fuzzy_name_search(query, max_candidates // 2)
#         candidates.extend(fuzzy_results)

#         # 2. Partial word matching
#         words = query.split()
#         if len(words) > 1:
#             for word in words:
#                 if len(word) > 3:  # Skip short words
#                     word_results = await self.fetch_by_fuzzy_name_search(word, max_candidates // (len(words) * 2))
#                     candidates.extend(word_results)

#         # 3. Geographic proximity if coordinates available
#         # (implement if needed)

#         # Remove duplicates and limit
#         seen_ids = set()
#         unique_candidates = []
#         for candidate in candidates:
#             if candidate["site_id"] not in seen_ids:
#                 seen_ids.add(candidate["site_id"])
#                 unique_candidates.append(candidate)
#                 if len(unique_candidates) >= max_candidates:
#                     break

#         return unique_candidates


# class SiteLLMReconciliationStrategy(ReconciliationStrategy):
#     """LLM-enhanced site reconciliation strategy"""

#     def __init__(self):
#         specification = {
#             **SITE_SPECIFICATION,  # Inherit from base site spec
#             "key": "site_llm",
#             "properties": [
#                 *SITE_SPECIFICATION["properties"],
#                 # Add LLM-specific properties
#                 {"id": "translation_confidence", "name": "Translation Confidence", "type": "number", "description": "Confidence score for translation (0-1)"},
#                 {"id": "semantic_score", "name": "Semantic Score", "type": "number", "description": "AI semantic matching score (0-1)"},
#                 {"id": "matching_method", "name": "Matching Method", "type": "string", "description": "Method used: fuzzy, translation, semantic, hybrid"},
#             ],
#         }
#         super().__init__(specification, SiteLLMQueryProxy)

#     async def find_candidates(self, cursor: psycopg.AsyncCursor, query: str, properties: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
#         """Enhanced candidate finding with LLM capabilities"""

#         llm_proxy = SiteLLMQueryProxy(self.specification, cursor)

#         # Determine matching strategy based on configuration and query
#         strategy = self._determine_strategy(query, properties)
#         logger.info(f"Using strategy: {strategy}")

#         if strategy == "translation":
#             results = await llm_proxy.fetch_with_translation(query, limit)
#         elif strategy == "semantic":
#             results = await llm_proxy.fetch_with_semantic_matching(query, limit)
#         elif strategy == "hybrid":
#             # Combine both approaches
#             translation_results = await llm_proxy.fetch_with_translation(query, limit // 2)
#             semantic_results = await llm_proxy.fetch_with_semantic_matching(query, limit // 2)
#             results = self._merge_results(translation_results, semantic_results, limit)
#         else:
#             # Fallback to traditional fuzzy matching
#             results = await llm_proxy.fetch_by_fuzzy_name_search(query, limit)

#         # Convert to standard candidate format
#         candidates = []
#         for result in results:
#             candidate = self.as_candidate(result)
#             # Add LLM-specific metadata
#             candidate["matching_method"] = strategy
#             if "translation_used" in result:
#                 candidate["translation_used"] = result["translation_used"]
#             if "semantic_score" in result:
#                 candidate["semantic_score"] = result["semantic_score"]
#             candidates.append(candidate)

#         return candidates

#     def _determine_strategy(self, query: str, properties: dict[str, Any]) -> str:
#         """Determine the best matching strategy for the query"""
#         config = ConfigValue("llm").resolve() or {}

#         # Check if LLM features are enabled
#         enable_translation = config.get("enable_translation", True)
#         enable_semantic = config.get("enable_semantic_matching", True)

#         # Heuristics for strategy selection
#         if not enable_translation and not enable_semantic:
#             return "fuzzy"

#         # Use semantic matching for complex/descriptive queries
#         if len(query.split()) > 3 and enable_semantic:
#             return "semantic"

#         # Use translation for non-ASCII queries
#         if not query.isascii() and enable_translation:
#             return "translation"

#         # Use hybrid for best results when both are enabled
#         if enable_translation and enable_semantic:
#             return "hybrid"

#         return "fuzzy"

#     def _merge_results(self, results1: List[Dict], results2: List[Dict], limit: int) -> List[Dict]:
#         """Merge and deduplicate results from multiple strategies"""
#         seen_ids = set()
#         merged = []

#         # Interleave results to maintain diversity
#         all_results = []
#         max_len = max(len(results1), len(results2))

#         for i in range(max_len):
#             if i < len(results1):
#                 all_results.append(results1[i])
#             if i < len(results2):
#                 all_results.append(results2[i])

#         # Deduplicate by site_id and limit
#         for result in all_results:
#             if result["site_id"] not in seen_ids:
#                 seen_ids.add(result["site_id"])
#                 merged.append(result)
#                 if len(merged) >= limit:
#                     break

#         return merged
