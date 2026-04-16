from __future__ import annotations

from dataclasses import dataclass

from app.services.language.chunk_filters import is_chunk_good_for_translation
from app.services.language.chunk_lang_detector import ChunkLanguageDetector
from app.services.retrieval.prompt_builder import build_translation_prompt_to_romanian

@dataclass
class ChunkTranslationResult:
    original_language: str
    translated_text_ro: str | None
    is_translated: bool
    status: str
    notes: str | None = None


class ChunkTranslationService:
    def __init__(self, llm_service) -> None:
        self.llm_service = llm_service
        self.language_detector = ChunkLanguageDetector()

    def process_chunk(self, text: str) -> ChunkTranslationResult:
        text = (text or "").strip()

        if not is_chunk_good_for_translation(text):
            return ChunkTranslationResult(
                original_language="unknown",
                translated_text_ro=None,
                is_translated=False,
                status="skipped",
                notes="chunk_not_good_for_translation",
            )

        lang_result = self.language_detector.detect(text)
        source_lang = lang_result.language

        if source_lang == "unknown":
            # можно все равно перевести как "auto"
            source_lang = "auto"

        if source_lang == "ro":
            return ChunkTranslationResult(
                original_language="ro",
                translated_text_ro=text,
                is_translated=False,
                status="done",
                notes="already_romanian",
            )

        prompt = build_translation_prompt_to_romanian(
            text=text,
            source_language=source_lang,
        )
        result = self.llm_service.generate_json(prompt)

        if not result:
            return ChunkTranslationResult(
                original_language=source_lang,
                translated_text_ro=None,
                is_translated=False,
                status="failed",
                notes="invalid_llm_json",
            )

        translated_text = (result.get("translated_text_ro") or "").strip()
        notes = (result.get("notes") or "").strip() or None

        if not translated_text:
            return ChunkTranslationResult(
                original_language=source_lang,
                translated_text_ro=None,
                is_translated=False,
                status="failed",
                notes="empty_translation",
            )

        return ChunkTranslationResult(
            original_language=source_lang,
            translated_text_ro=translated_text,
            is_translated=True,
            status="done",
            notes=notes,
        )