from __future__ import annotations

import re


def is_noise_chunk(text: str) -> bool:
    text = (text or "").strip().lower()
    if not text:
        return True

    noise_markers = [
        "tel.:",
        "tel:",
        "fax:",
        "e-mail:",
        "email:",
        "webpage:",
        "website:",
        "www.",
        "http://",
        "https://",
        "office@",
        "contact",
        "contacts",
    ]

    if any(marker in text for marker in noise_markers):
        return True

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return True

    contact_like = 0
    for line in lines:
        if (
            re.search(r"\+?\d[\d\-\.\(\) ]{5,}", line)
            or "@" in line
            or "www." in line
            or line.lower().startswith(("str.", "tel", "fax", "email", "e-mail"))
        ):
            contact_like += 1

    if len(lines) >= 2 and contact_like / len(lines) >= 0.4:
        return True

    return False


def is_chunk_good_for_translation(text: str) -> bool:
    text = (text or "").strip()

    if len(text) < 60:
        return False

    if len(text.split()) < 10:
        return False

    if is_noise_chunk(text):
        return False

    return True