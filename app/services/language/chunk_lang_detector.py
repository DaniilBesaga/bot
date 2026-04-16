from __future__ import annotations

import re
from dataclasses import dataclass

try:
    from lingua import Language, LanguageDetectorBuilder
    _HAS_LINGUA = True
except Exception:
    _HAS_LINGUA = False

try:
    from langdetect import detect as langdetect_detect
    _HAS_LANGDETECT = True
except Exception:
    _HAS_LANGDETECT = False


SUPPORTED_LANGS = {"ro", "it", "en", "ru", "fr", "de", "es"}


@dataclass
class LanguageDetectionResult:
    language: str
    confidence: float
    method: str


class ChunkLanguageDetector:
    def __init__(self) -> None:
        self._lingua_detector = None

        if _HAS_LINGUA:
            languages = [
                Language.ROMANIAN,
                Language.ITALIAN,
                Language.ENGLISH,
                Language.RUSSIAN,
                Language.FRENCH,
                Language.GERMAN,
                Language.SPANISH,
            ]
            self._lingua_detector = (
                LanguageDetectorBuilder
                .from_languages(*languages)
                .build()
            )

    def _prepare_text(self, text: str) -> str:
        text = (text or "").strip()

        # убираем email, сайты, телефоны
        text = re.sub(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", " ", text)
        text = re.sub(r"https?://\S+|www\.\S+", " ", text)
        text = re.sub(r"\+?\d[\d\-\.\(\) ]{5,}", " ", text)

        # убираем артикулы / модели вида MAXI 80 / DN32 / AISI304
        text = re.sub(r"\b[A-Z0-9\-\/]{2,}\b", " ", text)

        # оставляем буквы и базовую пунктуацию
        text = re.sub(r"[^\w\sÀ-ÿĂÂÎȘŞȚŢăâîșşțţЁёА-Яа-я]", " ", text, flags=re.UNICODE)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:2000]

    def detect(self, text: str) -> LanguageDetectionResult:
        clean = self._prepare_text(text)

        if not clean:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                method="empty",
            )

        if self._lingua_detector is not None:
            result = self._detect_with_lingua(clean)
            if result:
                return result

        if _HAS_LANGDETECT:
            result = self._detect_with_langdetect(clean)
            if result:
                return result

        return LanguageDetectionResult(
            language="unknown",
            confidence=0.0,
            method="fallback",
        )

    def _detect_with_lingua(self, text: str) -> LanguageDetectionResult | None:
        try:
            language = self._lingua_detector.detect_language_of(text)
            if language is None:
                return None

            confidence_values = self._lingua_detector.compute_language_confidence_values(text)
            confidence_map = {
                self._map_lingua_lang(cv.language): cv.value
                for cv in confidence_values
            }
            lang_code = self._map_lingua_lang(language)

            return LanguageDetectionResult(
                language=lang_code,
                confidence=float(confidence_map.get(lang_code, 0.0)),
                method="lingua",
            )
        except Exception:
            return None

    def _detect_with_langdetect(self, text: str) -> LanguageDetectionResult | None:
        try:
            lang = langdetect_detect(text)
            if lang not in SUPPORTED_LANGS:
                lang = "unknown"

            return LanguageDetectionResult(
                language=lang,
                confidence=0.55,
                method="langdetect",
            )
        except Exception:
            return None

    def _map_lingua_lang(self, language) -> str:
        mapping = {
            "ROMANIAN": "ro",
            "ITALIAN": "it",
            "ENGLISH": "en",
            "RUSSIAN": "ru",
            "FRENCH": "fr",
            "GERMAN": "de",
            "SPANISH": "es",
        }
        return mapping.get(str(language).split(".")[-1], "unknown")