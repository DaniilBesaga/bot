
from app.db.models import Block
from app.services.chunking.rules import should_include_in_clean_text


class ChunkTextBuilder:
    @staticmethod
    def safe_join_text(parts: list[str]) -> str:
        parts = [p.strip() for p in parts if p and p.strip()]
        return "\n\n".join(parts)

    @classmethod
    def build_raw_text(cls, blocks: list[Block]) -> str:
        parts = []
        for block in blocks:
            text = (block.raw_text or "").strip()
            if text:
                parts.append(text)
        return cls.safe_join_text(parts)

    @classmethod
    def build_clean_text(cls, blocks: list[Block]) -> str:
        parts = []
        for block in blocks:
            if should_include_in_clean_text(block):
                text = (block.normalized_text or "").strip()
                if text:
                    parts.append(text)
        return cls.safe_join_text(parts)