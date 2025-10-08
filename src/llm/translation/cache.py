"""
Translation caching to avoid repeated API calls
"""

import datetime
import hashlib
import json
from pathlib import Path

from loguru import logger


class TranslationCache:
    """Simple file-based cache for translations"""

    def __init__(self, cache_dir: str = "cache/translations"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, str] = {}

    def _cache_key(self, text: str, target_lang: str) -> str:
        """Generate cache key from text and target language"""
        content = f"{text}:{target_lang}"
        return hashlib.md5(content.encode()).hexdigest()

    async def get(self, text: str, target_lang: str) -> None | str:
        """Get cached translation"""
        key = self._cache_key(text, target_lang)

        # Check memory cache first
        if key in self._memory_cache:
            return self._memory_cache[key]

        # Check file cache
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    translation = data.get("translation")
                    if translation:
                        self._memory_cache[key] = translation
                        return translation
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Failed to read cache file {cache_file}: {e}")

        return None

    async def set(self, text: str, target_lang: str, translation: str):
        """Cache translation"""
        key = self._cache_key(text, target_lang)

        # Update memory cache
        self._memory_cache[key] = translation

        # Update file cache
        cache_file = self.cache_dir / f"{key}.json"
        try:
            data = {"text": text, "target_lang": target_lang, "translation": translation, "timestamp": str(datetime.datetime.now(datetime.timezone.utc))}
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"Failed to write cache file {cache_file}: {e}")
