from app.services.process_document.helpers.geometry import Geometry


class Cleanup:

    @classmethod
    def run(cls, blocks: list[dict]) -> list[dict]:
        blocks = cls.remove_empty(blocks)
        blocks = cls.remove_tiny_noise(blocks)
        blocks = cls.deduplicate_overlaps(blocks)
        blocks = cls.merge_split_paragraphs(blocks)
        return blocks

    @classmethod
    def remove_empty(cls, blocks: list[dict]) -> list[dict]:
        result = []

        for b in blocks:
            text = (b.get("text") or "").strip()
            kind = b.get("kind")

            if kind in ("text_block", "table_block") and not text:
                continue

            result.append(b)

        return result

    @classmethod
    def remove_tiny_noise(cls, blocks: list[dict]) -> list[dict]:
        result = []

        for b in blocks:
            x0, y0, x1, y1 = b["bbox"]
            w = x1 - x0
            h = y1 - y0

            if w < 8 or h < 8:
                continue

            result.append(b)

        return result
    
    @classmethod
    def deduplicate_overlaps(cls, blocks: list[dict]) -> list[dict]:
        priority = {
            "heading": 5,
            "caption": 4,
            "structured_table": 4,
            "visual_table": 3,
            "figure": 3,
            "paragraph": 2,
            "header_footer": 1,
        }

        sorted_blocks = sorted(
            blocks,
            key=lambda b: priority.get(b.get("role"), 0),
            reverse=True
        )

        result = []
        for block in sorted_blocks:
            covered = False
            for existing in result:
                ratio = Geometry.calculate_intersection_ratio(block["bbox"], existing["bbox"])
                if ratio > 0.85:
                    covered = True
                    break
            if not covered:
                result.append(block)

        return result
    
    @classmethod
    def merge_split_paragraphs(cls, blocks: list[dict]) -> list[dict]:
        if not blocks:
            return []

        blocks = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
        result = []
        current = blocks[0]

        for nxt in blocks[1:]:
            if cls.should_merge_paragraphs(current, nxt):
                current = {
                    **current,
                    "bbox": Geometry.union_bbox(current["bbox"], nxt["bbox"]),
                    "text": f'{current["text"].rstrip()} {nxt["text"].lstrip()}'.strip()
                }
            else:
                result.append(current)
                current = nxt

        result.append(current)
        return result

    @classmethod
    def should_merge_paragraphs(cls, a: dict, b: dict) -> bool:
        if a.get("role") != "paragraph" or b.get("role") != "paragraph":
            return False

        gap = Geometry.vertical_gap(a["bbox"], b["bbox"])
        overlap = Geometry.horizontal_overlap_ratio(a["bbox"], b["bbox"])

        if gap < 12 and overlap > 0.6:
            return True

        return False