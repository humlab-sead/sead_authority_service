from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.configuration import MockConfigProvider
from src.llm.translation.translation import LanguageDetection, TranslationService
from tests.conftest import ExtendedMockConfigProvider
from tests.decorators import with_test_config


class TestTranslationServiceDetectLanguage:
    @pytest.mark.asyncio
    async def test_detect_language_ascii_fast_path(self):
        llm = AsyncMock()
        llm.complete = AsyncMock()
        service = TranslationService(llm_client=llm)  # type: ignore[arg-type]

        result = await service.detect_language("Hello world")

        assert result == LanguageDetection("en", 0.9)
        llm.complete.assert_not_awaited()

    @pytest.mark.asyncio
    @with_test_config
    async def test_detect_language_uses_llm_and_parses_response(self, test_provider: ExtendedMockConfigProvider):
        test_provider.get_config().update({"llm.prompts.language_detection": "lang={text} | {context}"})

        llm = AsyncMock()
        llm.complete = AsyncMock(return_value="sv, 0.75")
        service = TranslationService(llm_client=llm)  # type: ignore[arg-type]

        result = await service.detect_language("Café", context="archaeology")

        assert result == LanguageDetection("sv", 0.75)
        llm.complete.assert_awaited_once()
        prompt = llm.complete.call_args.args[0]
        assert "lang=Café" in prompt
        assert "Context:\narchaeology" in prompt

    @pytest.mark.asyncio
    @with_test_config
    async def test_detect_language_invalid_llm_response_returns_unknown(self, test_provider: MockConfigProvider):
        test_provider.get_config().update({"llm.prompts.language_detection": "lang={text} | {context}"})

        llm = AsyncMock()
        llm.complete = AsyncMock(return_value="sv,not-a-float")
        service = TranslationService(llm_client=llm)  # type: ignore[arg-type]

        result = await service.detect_language("Café")

        assert result == LanguageDetection("??", 0.0)

    @pytest.mark.asyncio
    @with_test_config
    async def test_detect_language_llm_exception_returns_unknown(self, test_provider: MockConfigProvider):
        test_provider.get_config().update({"llm.prompts.language_detection": "lang={text} | {context}"})

        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=RuntimeError("boom"))
        service = TranslationService(llm_client=llm)  # type: ignore[arg-type]

        result = await service.detect_language("Café")

        assert result == LanguageDetection("??", 0.0)


class TestTranslationServiceTranslate:
    @pytest.mark.asyncio
    async def test_translate_same_language_returns_input(self):
        llm = AsyncMock()
        llm.complete = AsyncMock()
        service = TranslationService(llm_client=llm)  # type: ignore[arg-type]

        out = await service.translate("Gamla Uppsala", source_lang="sv", target_lang="sv")

        assert out == "Gamla Uppsala"
        llm.complete.assert_not_awaited()

    @pytest.mark.asyncio
    @with_test_config
    async def test_translate_uses_config_prompt_and_strips_quotes(self, test_provider: MockConfigProvider):
        test_provider.get_config().update({"llm.translation_prompt": "PROMPT"})

        llm = AsyncMock()
        llm.complete = AsyncMock(return_value='"Hello"')
        service = TranslationService(llm_client=llm)  # type: ignore[arg-type]

        out = await service.translate("Hej", source_lang="sv", target_lang="en")

        assert out == "Hello"
        llm.complete.assert_awaited_once_with("PROMPT", max_tokens=100, temperature=0.1)

    @pytest.mark.asyncio
    @with_test_config
    async def test_translate_llm_exception_returns_original(self, test_provider: MockConfigProvider):
        test_provider.get_config().update({"llm.translation_prompt": "PROMPT"})
        llm = AsyncMock()
        llm.complete = AsyncMock(side_effect=RuntimeError("boom"))
        service = TranslationService(llm_client=llm)  # type: ignore[arg-type]

        out = await service.translate("Hej", source_lang="sv", target_lang="en")

        assert out == "Hej"


class TestTranslationServiceHeuristics:
    def test_contains_non_english_patterns(self):
        llm = AsyncMock()
        service = TranslationService(llm_client=llm)  # type: ignore[arg-type]

        assert service._contains_non_english_patterns("Ångström") is True  # pylint: disable=protected-access
        assert service._contains_non_english_patterns("Château") is True  # pylint: disable=protected-access
        assert service._contains_non_english_patterns("Hello") is False  # pylint: disable=protected-access
