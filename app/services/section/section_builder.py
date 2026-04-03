from app.db.models import Block
from app.services.chunking.rules import is_heading_block, is_strong_boilerplate


class SectionBuilder:
    @staticmethod
    def build_sections(blocks: list[Block]) -> list[dict]:
        sections = []
        current_section = None

        for block in blocks:
            if is_strong_boilerplate(block):
                continue

            if is_heading_block(block):
                if current_section and current_section["blocks"]:
                    sections.append(current_section)

                current_section = {
                    "heading": block,
                    "blocks": [block],
                }
                continue

            if current_section is None:
                current_section = {
                    "heading": None,
                    "blocks": [block],
                }
            else:
                current_section["blocks"].append(block)

        if current_section and current_section["blocks"]:
            sections.append(current_section)

        return sections