

from app.db.models import Block


def is_heading_block(block: Block) -> bool:
    return (block.role or "").lower() == "heading"


def is_strong_boilerplate(block: Block) -> bool:
    return block.boilerplate_score >= 0.8 and block.content_score < 0.3


def is_strong_contact(block: Block) -> bool:
    return block.contact_score >= 0.8 and block.content_score < 0.3


def is_content_like_block(block: Block) -> bool:
    role = (block.role or "").lower()
    kind = (block.kind or "").lower()

    if role in {"heading", "paragraph", "list", "table_text"}:
        return True

    if "table" in kind:
        return True

    return False


def should_include_in_clean_text(block: Block) -> bool:
    if is_strong_boilerplate(block):
        return False

    if is_strong_contact(block):
        return False

    if not (block.normalized_text or "").strip():
        return False

    return True


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def safe_join_text(parts: list[str]) -> str:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    return "\n\n".join(cleaned)


def estimate_word_count(text: str) -> int:
    return len(text.split()) if text else 0


def is_text_present(text: str | None) -> bool:
    return bool(text and text.strip())