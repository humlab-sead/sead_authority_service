"""
Translation service using LLM
"""

import re
from dataclasses import dataclass

from loguru import logger

# from llm.providers.client import LLMClient
from src.configuration import ConfigValue


@dataclass
class LanguageDetection:
    language: str
    confidence: float


class TranslationService:
    """LLM-based translation service"""

    def __init__(self, llm_client) -> None:
        self.llm_client = llm_client

    async def detect_language(self, text: str, context: str = "", default: str = "en") -> LanguageDetection:
        """Detect the language of input text"""

        if text.isascii() and not self._contains_non_english_patterns(text):
            return LanguageDetection("en", 0.9)

        if context:
            context = f"Context:\n{context}"

        default_language: str = default or ConfigValue("llm.prompts.language_detection").resolve()
        prompt_template: str = ConfigValue("llm.prompts.language_detection").resolve()
        prompt: str = prompt_template.format(text=text, context=context)
        try:
            response: str = await self.llm_client.provider.complete(prompt, max_tokens=50, temperature=0.1)
            parts: list[str] = response.strip().split(",")
            if len(parts) == 2:
                lang_code: str = parts[0].strip()
                confidence: float = float(parts[1].strip())
                return LanguageDetection(lang_code, confidence)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Language detection failed: {e}")

        return LanguageDetection(default_language, 0.5)

    async def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translate text from source to target language"""

        if source_lang == target_lang:
            return text

        prompt: str = ConfigValue("llm.translation_prompt").resolve()
        prompt = f"""
Translate this archaeological/geographic site name from {source_lang} to {target_lang}.

Keep the translation natural and preserve proper nouns when appropriate.
For place names, use the most common English form if it exists.

Examples:
- "Gamla Uppsala" (sv->en) -> "Old Uppsala"
- "Sankt Petersburg" (de->en) -> "Saint Petersburg"  
- "Château de Versailles" (fr->en) -> "Palace of Versailles"

Text to translate: "{text}"
Translation:"""

        try:
            response = await self.llm_client.provider.complete(prompt, max_tokens=100, temperature=0.1)
            translation = response.strip().strip('"')
            logger.info(f"Translated '{text}' ({source_lang}) -> '{translation}' ({target_lang})")
            return translation
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Translation failed: {e}")
            return text  # Return original on failure

    def _contains_non_english_patterns(self, text: str) -> bool:
        """Simple heuristics to detect non-English text"""
        # Nordic characters
        if re.search(r"[åäöüßøæ]", text.lower()):
            return True
        # Accented characters
        if re.search(r"[àáâãäåçèéêëìíîïñòóôõöøùúûüýÿ]", text.lower()):
            return True
        return False
