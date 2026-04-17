from __future__ import annotations

import random
import re
import time
import uuid
from typing import Any

import openai

def _extract_retry_after_seconds(error: Exception) -> float | None:
    """
    Пытается достать recommended wait time из текста ошибки:
    'Please try again in 10ms'
    'Please try again in 5.08s'
    """
    text = str(error)

    ms_match = re.search(r"try again in\s+(\d+(?:\.\d+)?)ms", text, re.IGNORECASE)
    if ms_match:
        return float(ms_match.group(1)) / 1000.0

    s_match = re.search(r"try again in\s+(\d+(?:\.\d+)?)s", text, re.IGNORECASE)
    if s_match:
        return float(s_match.group(1))

    return None



def _with_rate_limit_retry(func, *args, max_retries: int = 6, **kwargs):
    """
    Retry wrapper для вызовов LLM / embedding.
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)

        except openai.RateLimitError as e:
            last_error = e

            retry_after = _extract_retry_after_seconds(e)
            if retry_after is None:
                # fallback exponential backoff
                retry_after = min(2 ** attempt, 30)

            # небольшой jitter
            retry_after += random.uniform(0.05, 0.3)

            print(
                f"Rate limit hit on attempt {attempt + 1}/{max_retries}. "
                f"Sleeping {retry_after:.2f}s..."
            )
            time.sleep(retry_after)

    raise last_error