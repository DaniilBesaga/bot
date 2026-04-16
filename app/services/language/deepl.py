from __future__ import annotations

from dataclasses import dataclass

import deepl

from app.core.config import settings


@dataclass
class TranslationResult:
    original_language: str | None
    translated_text_ro: str | None
    is_translated: bool
    status: str  # done / skipped / failed


class DeepLTranslationService:
    def __init__(
        self,
        api_key: str | None = None,
        target_lang: str = "RO",
        glossary_id: str | None = None,
    ) -> None:
        self.api_key = api_key or settings.DEEPL_API_KEY
        self.target_lang = target_lang
        self.glossary_id = glossary_id or settings.DEEPL_GLOSSARY_ID

        if not self.api_key:
            raise ValueError("DEEPL_API_KEY is not configured")

        self.client = deepl.Translator(self.api_key)

    def process_chunk(self, text: str) -> TranslationResult:
        text = (text or "").strip()

        if not text:
            return TranslationResult(
                original_language=None,
                translated_text_ro=None,
                is_translated=False,
                status="skipped",
            )

        try:
            # Если хочешь, можно передавать list[str] батчами.
            # Пока оставляем 1 chunk = 1 запрос для минимальных изменений.
            kwargs = {
                "target_lang": self.target_lang,
                # DeepL сам определяет исходный язык, если source_lang не задан.
                # Следующие параметры опциональны, но полезны:
                "split_sentences": "1",
                "preserve_formatting": True,
                # Можно попробовать next-gen model_type, если доступен в аккаунте:
                # "model_type": "prefer_quality_optimized",
            }

            if self.glossary_id:
                kwargs["glossary"] = self.client.get_glossary(self.glossary_id)

            result = self.client.translate_text(text, **kwargs)

            detected_source_lang = getattr(result, "detected_source_lang", None)
            translated_text = getattr(result, "text", None)

            # Если текст уже на румынском, можно не считать это переводом.
            # Но DeepL все равно может вернуть тот же/почти тот же текст.
            is_already_ro = (detected_source_lang or "").upper() == "RO"

            return TranslationResult(
                original_language=detected_source_lang,
                translated_text_ro=translated_text,
                is_translated=not is_already_ro,
                status="done",
            )

        except deepl.QuotaExceededException:
            # Free: когда месячный лимит кончился.
            raise

        except deepl.TooManyRequestsException:
            # 429 / rate limiting
            raise

        except deepl.DeepLException:
            # Любая другая ошибка DeepL SDK
            raise