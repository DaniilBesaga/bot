import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None

    text = text.strip()

    # сначала пробуем как есть
    try:
        return json.loads(text)
    except Exception:
        pass

    # если модель обернула в ```json ... ```
    fence_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except Exception:
            pass

    # ищем первый JSON-объект
    obj_match = re.search(r"\{.*\}", text, re.DOTALL)
    if obj_match:
        try:
            return json.loads(obj_match.group(0))
        except Exception:
            return None

    return None

def is_chunk_good_for_qa(text: str) -> bool:
        text = (text or "").strip()

        if len(text) < 120:
            return False

        if len(text.split()) < 20:
            return False

        return True