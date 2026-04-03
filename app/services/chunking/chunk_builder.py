from app.services.chunking.rules import avg, estimate_word_count, safe_join_text
from db.models import Block


class ChunkBuilder:
    @staticmethod
    def is_strong_boilerplate(block: Block) -> bool:
        return block.boilerplate_score >= 0.8 and block.content_score < 0.3

    @staticmethod
    def is_strong_contact(block: Block) -> bool:
        return block.contact_score >= 0.8 and block.content_score < 0.3

    @staticmethod
    def split_section_into_chunk_groups(section: dict, max_words: int = 220) -> list[list[Block]]:
        groups: list[list[Block]] = []
        current_group: list[Block] = []
        current_words = 0

        for block in section["blocks"]:
            block_text = (block.normalized_text or "").strip()
            if not block_text:
                continue

            block_words = estimate_word_count(block_text)

            if current_group and current_words + block_words > max_words:
                groups.append(current_group)
                current_group = [block]
                current_words = block_words
            else:
                current_group.append(block)
                current_words += block_words

        if current_group:
            groups.append(current_group)

        return groups

    @staticmethod
    def ensure_heading_in_group(section_heading: Block | None, group: list[Block]) -> list[Block]:
        if section_heading is None or not group:
            return group

        if group[0].block_id == section_heading.block_id:
            return group

        return [section_heading] + group

    @staticmethod
    def detect_chunk_type(blocks: list[Block]) -> str:
        roles = {(b.role or "").lower() for b in blocks}
        kinds = {(b.kind or "").lower() for b in blocks}

        if any("table_block" in k for k in kinds) or "table_text" in roles:
            return "table_chunk"

        meaningful = [b for b in blocks if (b.raw_text or "").strip()]
        if meaningful and all((b.contact_score >= 0.8 and b.content_score < 0.3) for b in meaningful):
            return "contact_chunk"

        if "heading" in roles:
            return "product_section"

        return "mixed"

    @classmethod
    def build_chunk_from_blocks(
        cls,
        doc_id: str,
        chunk_index: int,
        blocks: list[Block],
        heading: Block | None = None,
    ) -> dict:
        raw_parts: list[str] = []
        clean_parts: list[str] = []

        for block in blocks:
            raw_text = (block.raw_text or "").strip()
            norm_text = (block.normalized_text or "").strip()

            if raw_text:
                raw_parts.append(raw_text)

            include_in_clean = True
            if cls.is_strong_boilerplate(block):
                include_in_clean = False
            if cls.is_strong_contact(block):
                include_in_clean = False

            if include_in_clean and norm_text:
                clean_parts.append(norm_text)

        block_ids = [b.block_id for b in blocks]
        pages = [b.page_number for b in blocks if b.page_number is not None]
        positions = [b.position_index for b in blocks if b.position_index is not None]

        contact_scores = [b.contact_score for b in blocks]
        boilerplate_scores = [b.boilerplate_score for b in blocks]
        content_scores = [b.content_score for b in blocks]

        return {
            "chunk_id": f"{doc_id}_chunk_{chunk_index}",
            "doc_id": doc_id,
            "start_page": min(pages) if pages else None,
            "end_page": max(pages) if pages else None,
            "start_position_index": min(positions) if positions else None,
            "end_position_index": max(positions) if positions else None,
            "block_ids": block_ids,
            "chunk_type": cls.detect_chunk_type(blocks),
            "raw_text": safe_join_text(raw_parts),
            "clean_text": safe_join_text(clean_parts),
            "heading_text": heading.raw_text if heading else None,
            "heading_fingerprint": heading.fingerprint_text if heading else None,
            "avg_contact_score": avg(contact_scores),
            "max_contact_score": max(contact_scores) if contact_scores else 0.0,
            "avg_boilerplate_score": avg(boilerplate_scores),
            "max_boilerplate_score": max(boilerplate_scores) if boilerplate_scores else 0.0,
            "avg_content_score": avg(content_scores),
            "max_content_score": max(content_scores) if content_scores else 0.0,
        }