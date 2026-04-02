import re
import unicodedata

from app.dataclasses.block import Block

EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
URL_RE = re.compile(r'(https?://\S+|www\.\S+)')
PHONE_RE = re.compile(r'(\+?\d[\d\s\-\.\(\)]{6,}\d)')

def normalize_whitespace(text: str) -> str:
    text = text.replace('\xa0', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def strip_control_chars(text: str) -> str:
    return ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C' or ch in '\n\t')

def normalize_text(text: str) -> str:
    text = strip_control_chars(text)
    text = unicodedata.normalize("NFKC", text)
    text = normalize_whitespace(text)
    return text

def normalize_for_fingerprint(text: str) -> str:
    text = normalize_text(text).lower()

    text = EMAIL_RE.sub('[email]', text)
    text = URL_RE.sub('[url]', text)
    text = PHONE_RE.sub('[phone]', text)

    text = re.sub(r'\d+', '[num]', text)
    text = re.sub(r'[^\w\s\[\]]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


CONTACT_TERMS = {
    "tel", "telefon", "fax", "email", "e-mail", "contact", "office", "www", "webpage", "phone"
}

def count_words(text: str) -> int:
    return len(text.split()) if text else 0

def calc_digit_ratio(text: str) -> float:
    if not text:
        return 0.0
    digits = sum(ch.isdigit() for ch in text)
    return digits / len(text)

def calc_uppercase_ratio(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return 0.0
    upper = sum(ch.isupper() for ch in letters)
    return upper / len(letters)

def contains_email(text: str) -> bool:
    return bool(EMAIL_RE.search(text or ""))

def contains_url(text: str) -> bool:
    return bool(URL_RE.search(text or ""))

def contains_phone_like(text: str) -> bool:
    return bool(PHONE_RE.search(text or ""))

def count_contact_terms(text: str) -> int:
    tokens = re.findall(r'\w+', text.lower())
    return sum(1 for t in tokens if t in CONTACT_TERMS)

def calc_line_count(text: str) -> int:
    if not text:
        return 0
    return len([line for line in text.splitlines() if line.strip()])

def get_relative_top(block: dict, page_height: float | None = None) -> float:
    if not page_height:
        return 0.0
    y0 = block["bbox"][1]
    return y0 / page_height

def get_relative_bottom(block: dict, page_height: float | None = None) -> float:
    if not page_height:
        return 0.0
    y1 = block["bbox"][3]
    return y1 / page_height

def extract_local_features(block: dict) -> dict:
    raw_text = block.get("raw_text", "") or ""
    normalized_text = block.get("normalized_text", "") or ""

    page_height = block.get("page_height")

    return {
        "char_count": len(normalized_text),
        "word_count": count_words(normalized_text),
        "digit_ratio": calc_digit_ratio(normalized_text),
        "has_email": contains_email(raw_text),
        "has_url": contains_url(raw_text),
        "has_phone_like": contains_phone_like(raw_text),
        "contact_term_count": count_contact_terms(normalized_text),
        "is_short": count_words(normalized_text) <= 12,
        "is_empty": count_words(normalized_text) == 0,
        "relative_top": get_relative_top(block, page_height),
        "relative_bottom": get_relative_bottom(block, page_height),
        "position_index": block.get("position_index", 0),
        "block_type": block.get("block_type", "unknown"),
    }