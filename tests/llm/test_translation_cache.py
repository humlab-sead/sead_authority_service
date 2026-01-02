"""Comprehensive tests for TranslationCache."""

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.llm.translation.cache import TranslationCache

# pylint: disable=protected-access


class TestTranslationCacheInitialization:
    """Test TranslationCache initialization."""

    def test_initialization_default_directory(self, tmp_path):
        """Test default cache directory is created."""
        cache_dir = tmp_path / "default_cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        assert cache.cache_dir == cache_dir
        assert cache.cache_dir.exists()
        assert cache.cache_dir.is_dir()
        assert isinstance(cache._memory_cache, dict)
        assert len(cache._memory_cache) == 0

    def test_initialization_custom_directory(self, tmp_path):
        """Test custom cache directory is created."""
        custom_dir = tmp_path / "custom" / "nested" / "cache"
        cache = TranslationCache(cache_dir=str(custom_dir))

        assert cache.cache_dir == custom_dir
        assert cache.cache_dir.exists()
        assert cache.cache_dir.is_dir()

    def test_initialization_existing_directory(self, tmp_path):
        """Test initialization with existing directory."""
        cache_dir = tmp_path / "existing_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache = TranslationCache(cache_dir=str(cache_dir))

        assert cache.cache_dir.exists()
        assert cache.cache_dir.is_dir()

    def test_memory_cache_initialized_empty(self, tmp_path):
        """Test memory cache is initialized as empty dict."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        assert not cache._memory_cache
        assert isinstance(cache._memory_cache, dict)


class TestTranslationCacheCacheKey:
    """Test cache key generation."""

    def test_cache_key_generation(self, tmp_path):
        """Test cache key is MD5 hash of text:target_lang."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        text = "Hello world"
        target_lang = "es"
        expected_content = f"{text}:{target_lang}"
        expected_key = hashlib.md5(expected_content.encode()).hexdigest()

        key = cache._cache_key(text, target_lang)

        assert key == expected_key
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length

    def test_cache_key_different_text(self, tmp_path):
        """Test different texts generate different keys."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        key1 = cache._cache_key("Hello", "es")
        key2 = cache._cache_key("World", "es")

        assert key1 != key2

    def test_cache_key_different_language(self, tmp_path):
        """Test different languages generate different keys."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        key1 = cache._cache_key("Hello", "es")
        key2 = cache._cache_key("Hello", "fr")

        assert key1 != key2

    def test_cache_key_same_inputs_same_key(self, tmp_path):
        """Test same inputs always generate same key."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        key1 = cache._cache_key("Test", "de")
        key2 = cache._cache_key("Test", "de")

        assert key1 == key2

    def test_cache_key_case_sensitive(self, tmp_path):
        """Test cache key is case sensitive."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        key1 = cache._cache_key("Hello", "es")
        key2 = cache._cache_key("hello", "es")

        assert key1 != key2

    def test_cache_key_unicode_handling(self, tmp_path):
        """Test cache key handles unicode text."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        text = "你好世界"  # Chinese text
        key = cache._cache_key(text, "en")

        assert isinstance(key, str)
        assert len(key) == 32

    def test_cache_key_empty_text(self, tmp_path):
        """Test cache key with empty text."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        key = cache._cache_key("", "es")

        assert isinstance(key, str)
        assert len(key) == 32


class TestTranslationCacheGet:
    """Test cache retrieval."""

    @pytest.mark.asyncio
    async def test_get_from_memory_cache(self, tmp_path):
        """Test retrieving translation from memory cache."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))
        text = "Hello"
        target_lang = "es"
        translation = "Hola"

        # Populate memory cache
        key = cache._cache_key(text, target_lang)
        cache._memory_cache[key] = translation

        result = await cache.get(text, target_lang)

        assert result == translation

    @pytest.mark.asyncio
    async def test_get_from_file_cache(self, tmp_path):
        """Test retrieving translation from file cache."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Hello"
        target_lang = "es"
        translation = "Hola"
        key = cache._cache_key(text, target_lang)

        # Create cache file
        cache_file = cache_dir / f"{key}.json"
        cache_data = {
            "text": text,
            "target_lang": target_lang,
            "translation": translation,
            "timestamp": "2026-01-01T00:00:00Z",
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = await cache.get(text, target_lang)

        assert result == translation
        # Should also populate memory cache
        assert cache._memory_cache[key] == translation

    @pytest.mark.asyncio
    async def test_get_not_found(self, tmp_path):
        """Test retrieving non-existent translation returns None."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        result = await cache.get("NonExistent", "es")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_memory_cache_before_file_cache(self, tmp_path):
        """Test memory cache is checked before file cache."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Hello"
        target_lang = "es"
        key = cache._cache_key(text, target_lang)

        # Add to memory cache
        cache._memory_cache[key] = "Hola (memory)"

        # Create different file cache
        cache_file = cache_dir / f"{key}.json"
        cache_data = {
            "text": text,
            "target_lang": target_lang,
            "translation": "Hola (file)",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = await cache.get(text, target_lang)

        # Should return memory cache value
        assert result == "Hola (memory)"

    @pytest.mark.asyncio
    async def test_get_corrupted_cache_file(self, tmp_path):
        """Test handling corrupted cache file returns None."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Hello"
        target_lang = "es"
        key = cache._cache_key(text, target_lang)

        # Create corrupted cache file
        cache_file = cache_dir / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        result = await cache.get(text, target_lang)

        # Should return None and handle error gracefully
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cache_file_missing_translation(self, tmp_path):
        """Test cache file without translation key."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Hello"
        target_lang = "es"
        key = cache._cache_key(text, target_lang)

        # Create cache file without translation
        cache_file = cache_dir / f"{key}.json"
        cache_data = {
            "text": text,
            "target_lang": target_lang,
            "timestamp": "2026-01-01T00:00:00Z",
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = await cache.get(text, target_lang)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cache_file_null_translation(self, tmp_path):
        """Test cache file with null translation."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Hello"
        target_lang = "es"
        key = cache._cache_key(text, target_lang)

        # Create cache file with null translation
        cache_file = cache_dir / f"{key}.json"
        cache_data = {
            "text": text,
            "target_lang": target_lang,
            "translation": None,
            "timestamp": "2026-01-01T00:00:00Z",
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f)

        result = await cache.get(text, target_lang)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_unicode_translation(self, tmp_path):
        """Test getting unicode translation."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Hello"
        target_lang = "zh"
        translation = "你好"
        key = cache._cache_key(text, target_lang)

        # Create cache file
        cache_file = cache_dir / f"{key}.json"
        cache_data = {
            "text": text,
            "target_lang": target_lang,
            "translation": translation,
            "timestamp": "2026-01-01T00:00:00Z",
        }
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False)

        result = await cache.get(text, target_lang)

        assert result == translation


class TestTranslationCacheSet:
    """Test cache storage."""

    @pytest.mark.asyncio
    async def test_set_updates_memory_cache(self, tmp_path):
        """Test set updates memory cache."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        text = "Hello"
        target_lang = "es"
        translation = "Hola"

        await cache.set(text, target_lang, translation)

        key = cache._cache_key(text, target_lang)
        assert key in cache._memory_cache
        assert cache._memory_cache[key] == translation

    @pytest.mark.asyncio
    async def test_set_creates_file_cache(self, tmp_path):
        """Test set creates file cache."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Hello"
        target_lang = "es"
        translation = "Hola"

        await cache.set(text, target_lang, translation)

        key = cache._cache_key(text, target_lang)
        cache_file = cache_dir / f"{key}.json"

        assert cache_file.exists()

        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["text"] == text
            assert data["target_lang"] == target_lang
            assert data["translation"] == translation
            assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_set_file_cache_format(self, tmp_path):
        """Test file cache has correct format."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Test"
        target_lang = "fr"
        translation = "Tester"

        await cache.set(text, target_lang, translation)

        key = cache._cache_key(text, target_lang)
        cache_file = cache_dir / f"{key}.json"

        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)

            assert "text" in data
            assert "target_lang" in data
            assert "translation" in data
            assert "timestamp" in data
            assert data["text"] == text
            assert data["target_lang"] == target_lang
            assert data["translation"] == translation

    @pytest.mark.asyncio
    async def test_set_overwrites_existing(self, tmp_path):
        """Test set overwrites existing cache entry."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        text = "Hello"
        target_lang = "es"

        await cache.set(text, target_lang, "Old translation")
        await cache.set(text, target_lang, "New translation")

        result = await cache.get(text, target_lang)

        assert result == "New translation"

    @pytest.mark.asyncio
    async def test_set_unicode_translation(self, tmp_path):
        """Test set with unicode translation."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        text = "Hello"
        target_lang = "ja"
        translation = "こんにちは"

        await cache.set(text, target_lang, translation)

        key = cache._cache_key(text, target_lang)
        cache_file = cache_dir / f"{key}.json"

        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data["translation"] == translation

    @pytest.mark.asyncio
    async def test_set_file_write_error(self, tmp_path):
        """Test handling file write errors still updates memory cache."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        with patch("builtins.open", side_effect=PermissionError("No permission")):
            await cache.set("Hello", "es", "Hola")

        # Memory cache should still be updated even if file write fails
        key = cache._cache_key("Hello", "es")
        assert cache._memory_cache[key] == "Hola"

    @pytest.mark.asyncio
    async def test_set_empty_translation(self, tmp_path):
        """Test set with empty translation."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        text = "Hello"
        target_lang = "es"
        translation = ""

        await cache.set(text, target_lang, translation)

        result = await cache.get(text, target_lang)

        assert result == ""

    @pytest.mark.asyncio
    async def test_set_timestamp_format(self, tmp_path):
        """Test timestamp is in ISO format."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        await cache.set("Hello", "es", "Hola")

        key = cache._cache_key("Hello", "es")
        cache_file = cache_dir / f"{key}.json"

        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            timestamp = data["timestamp"]

            # Should be a valid ISO format string
            assert isinstance(timestamp, str)
            assert len(timestamp) > 0


class TestTranslationCacheIntegration:
    """Integration tests for cache workflow."""

    @pytest.mark.asyncio
    async def test_roundtrip_set_and_get(self, tmp_path):
        """Test setting and getting translation."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        text = "Good morning"
        target_lang = "de"
        translation = "Guten Morgen"

        await cache.set(text, target_lang, translation)
        result = await cache.get(text, target_lang)

        assert result == translation

    @pytest.mark.asyncio
    async def test_multiple_translations(self, tmp_path):
        """Test storing multiple translations."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        translations = [
            ("Hello", "es", "Hola"),
            ("Goodbye", "fr", "Au revoir"),
            ("Thank you", "de", "Danke"),
            ("Yes", "it", "Sì"),
        ]

        # Set all translations
        for text, lang, trans in translations:
            await cache.set(text, lang, trans)

        # Get all translations
        for text, lang, trans in translations:
            result = await cache.get(text, lang)
            assert result == trans

    @pytest.mark.asyncio
    async def test_cache_persistence_across_instances(self, tmp_path):
        """Test cache persists across different cache instances."""
        cache_dir = tmp_path / "cache"

        # First instance
        cache1 = TranslationCache(cache_dir=str(cache_dir))
        await cache1.set("Hello", "es", "Hola")

        # Second instance
        cache2 = TranslationCache(cache_dir=str(cache_dir))
        result = await cache2.get("Hello", "es")

        assert result == "Hola"

    @pytest.mark.asyncio
    async def test_memory_cache_populated_from_file(self, tmp_path):
        """Test memory cache is populated when reading from file."""
        cache_dir = tmp_path / "cache"

        # First instance sets cache
        cache1 = TranslationCache(cache_dir=str(cache_dir))
        await cache1.set("Hello", "es", "Hola")

        # Second instance reads from file
        cache2 = TranslationCache(cache_dir=str(cache_dir))
        assert len(cache2._memory_cache) == 0

        await cache2.get("Hello", "es")

        # Memory cache should now be populated
        key = cache2._cache_key("Hello", "es")
        assert key in cache2._memory_cache

    @pytest.mark.asyncio
    async def test_same_text_different_languages(self, tmp_path):
        """Test same text translated to different languages."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        text = "Hello"
        await cache.set(text, "es", "Hola")
        await cache.set(text, "fr", "Bonjour")
        await cache.set(text, "de", "Hallo")

        assert await cache.get(text, "es") == "Hola"
        assert await cache.get(text, "fr") == "Bonjour"
        assert await cache.get(text, "de") == "Hallo"

    @pytest.mark.asyncio
    async def test_cache_isolation_by_language(self, tmp_path):
        """Test translations are isolated by language."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        await cache.set("test", "es", "prueba")
        result_fr = await cache.get("test", "fr")

        assert result_fr is None

    @pytest.mark.asyncio
    async def test_large_number_of_entries(self, tmp_path):
        """Test cache handles large number of entries."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        # Create 100 cache entries
        for i in range(100):
            await cache.set(f"text_{i}", "es", f"traduccion_{i}")

        # Verify all entries
        for i in range(100):
            result = await cache.get(f"text_{i}", "es")
            assert result == f"traduccion_{i}"


class TestTranslationCacheEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_special_characters_in_text(self, tmp_path):
        """Test handling special characters in text."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        special_texts = [
            "Hello\nWorld",  # Newline
            "Tab\there",  # Tab
            "Quote's test",  # Apostrophe
            'Double "quote"',  # Quotes
            "Emoji 😀",  # Emoji
            "Math: α + β = γ",  # Greek letters
        ]

        for text in special_texts:
            await cache.set(text, "es", f"translation of {text}")
            result = await cache.get(text, "es")
            assert result == f"translation of {text}"

    @pytest.mark.asyncio
    async def test_very_long_text(self, tmp_path):
        """Test handling very long text."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        long_text = "A" * 10000
        translation = "B" * 10000

        await cache.set(long_text, "es", translation)
        result = await cache.get(long_text, "es")

        assert result == translation

    @pytest.mark.asyncio
    async def test_whitespace_preservation(self, tmp_path):
        """Test whitespace is preserved in translations."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        text = "  spaces  around  "
        translation = "  espacios  alrededor  "

        await cache.set(text, "es", translation)
        result = await cache.get(text, "es")

        assert result == translation

    @pytest.mark.asyncio
    async def test_cache_directory_permissions(self, tmp_path):
        """Test behavior when cache directory has permission issues."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        # This should work normally
        await cache.set("Hello", "es", "Hola")

        # Note: We can't easily test actual permission errors in pytest
        # without root access, so we use mocking in test_set_file_write_error

    @pytest.mark.asyncio
    async def test_concurrent_access_simulation(self, tmp_path):
        """Test simulated concurrent access (memory cache doesn't conflict)."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        await cache.set("Hello", "es", "Hola1")
        await cache.set("Hello", "es", "Hola2")
        await cache.set("Hello", "es", "Hola3")

        result = await cache.get("Hello", "es")

        # Should have the last value
        assert result == "Hola3"

    def test_cache_dir_as_path_object(self, tmp_path):
        """Test initialization with Path object."""
        cache_dir = tmp_path / "cache"
        cache = TranslationCache(cache_dir=str(cache_dir))

        assert isinstance(cache.cache_dir, Path)
        assert cache.cache_dir.exists()

    @pytest.mark.asyncio
    async def test_empty_target_language(self, tmp_path):
        """Test handling empty target language."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        await cache.set("Hello", "", "Translation")
        result = await cache.get("Hello", "")

        assert result == "Translation"

    @pytest.mark.asyncio
    async def test_json_special_chars_in_translation(self, tmp_path):
        """Test translations with JSON special characters."""
        cache = TranslationCache(cache_dir=str(tmp_path / "cache"))

        translation_with_special = '{"key": "value", "array": [1, 2, 3]}'

        await cache.set("JSON test", "es", translation_with_special)
        result = await cache.get("JSON test", "es")

        assert result == translation_with_special
