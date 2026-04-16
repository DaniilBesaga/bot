# from __future__ import annotations

# import re
# import time
# from typing import Any

# from app.core.config import settings


# class TranslatePipeline:
#     def __init__(
#         self,
#         db,
#         chunk_repo,
#         translation_service,
#     ) -> None:
#         self.db = db
#         self.chunk_repo = chunk_repo
#         self.translation_service = translation_service

#     def _extract_retry_after(self, error: Exception) -> float | None:
#         """
#         Пытается достать recommended wait time из текста ошибки Groq:
#         'Please try again in 1.51s'
#         """
#         text = str(error)
#         match = re.search(r"try again in\s+([0-9]+(?:\.[0-9]+)?)s", text, re.IGNORECASE)
#         if match:
#             return float(match.group(1))
#         return None

#     def _is_rate_limit_error(self, error: Exception) -> bool:
#         text = str(error).lower()
#         return (
#             "rate_limit_exceeded" in text
#             or "rate limit" in text
#             or "429" in text
#         )

#     def execute(self, limit: int | None = None) -> dict[str, Any]:
#         chunks = self.chunk_repo.get_chunks_without_ro_translation(limit=limit)

#         if not chunks:
#             return {
#                 "processed": 0,
#                 "done": 0,
#                 "skipped": 0,
#                 "failed": 0,
#             }

#         processed = 0
#         done = 0
#         skipped = 0
#         failed = 0

#         max_retries = 5

#         for chunk in chunks:
#             processed += 1

#             for attempt in range(max_retries + 1):
#                 try:
#                     result = self.translation_service.process_chunk(chunk.chunk_text)

#                     self.chunk_repo.update_translation_fields(
#                         chunk,
#                         original_language=result.original_language,
#                         translated_text_ro=result.translated_text_ro,
#                         is_translated_to_ro=result.is_translated,
#                         translation_status=result.status,
#                         translation_model=settings.CHAT_MODEL if result.status == "done" else None,
#                     )

#                     self.db.commit()

#                     if result.status == "done":
#                         done += 1
#                     elif result.status == "skipped":
#                         skipped += 1
#                     else:
#                         failed += 1

#                     break

#                 except Exception as e:
#                     self.db.rollback()

#                     if self._is_rate_limit_error(e):
#                         if attempt >= max_retries:
#                             failed += 1
#                             break

#                         retry_after = self._extract_retry_after(e)

#                         if retry_after is not None:
#                             sleep_seconds = retry_after + 0.5
#                         else:
#                             sleep_seconds = min(2 ** attempt, 10)

#                         time.sleep(sleep_seconds)
#                         continue

#                     failed += 1
#                     break

#         return {
#             "processed": processed,
#             "done": done,
#             "skipped": skipped,
#             "failed": failed,
#         }


from __future__ import annotations

import time
from typing import Any

import deepl

from app.core.config import settings


class TranslatePipeline:
    def __init__(
        self,
        db,
        chunk_repo,
        translation_service,
    ) -> None:
        self.db = db
        self.chunk_repo = chunk_repo
        self.translation_service = translation_service

    def _is_retryable_error(self, error: Exception) -> bool:
        return isinstance(
            error,
            (
                deepl.TooManyRequestsException,
                deepl.ConnectionException,
            ),
        )

    def execute(self, limit: int | None = None) -> dict[str, Any]:
        chunks = self.chunk_repo.get_chunks_without_ro_translation(limit=limit)

        if not chunks:
            return {
                "processed": 0,
                "done": 0,
                "skipped": 0,
                "failed": 0,
            }

        processed = 0
        done = 0
        skipped = 0
        failed = 0

        max_retries = 5

        for chunk in chunks:
            processed += 1

            for attempt in range(max_retries + 1):
                try:
                    result = self.translation_service.process_chunk(chunk.chunk_text)

                    self.chunk_repo.update_translation_fields(
                        chunk,
                        original_language=result.original_language,
                        translated_text_ro=result.translated_text_ro,
                        is_translated_to_ro=result.is_translated,
                        translation_status=result.status,
                        translation_model="deepl" if result.status == "done" else None,
                    )

                    self.db.commit()

                    if result.status == "done":
                        done += 1
                    elif result.status == "skipped":
                        skipped += 1
                    else:
                        failed += 1

                    break

                except deepl.QuotaExceededException:
                    self.db.rollback()
                    # месячная квота закончилась — дальше крутить цикл бессмысленно
                    failed += 1
                    return {
                        "processed": processed,
                        "done": done,
                        "skipped": skipped,
                        "failed": failed,
                        "error": "DeepL quota exceeded",
                    }

                except Exception as e:
                    self.db.rollback()

                    if self._is_retryable_error(e):
                        if attempt >= max_retries:
                            failed += 1
                            break

                        # у DeepL не всегда будет красивое 'try again in Xs',
                        # поэтому обычный exponential backoff
                        sleep_seconds = min(2 ** attempt, 20)
                        time.sleep(sleep_seconds)
                        continue

                    failed += 1
                    break

        return {
            "processed": processed,
            "done": done,
            "skipped": skipped,
            "failed": failed,
        }