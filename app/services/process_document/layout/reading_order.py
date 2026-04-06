class ReadingOrderResolver:

    @classmethod
    def sort_blocks(cls, blocks: list[dict], page_width: float) -> list[dict]:
        columns = cls.detect_columns(blocks, page_width)

        if len(columns) <= 1:
            return sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))

        ordered = []
        for col in columns:
            col_blocks = [
                b for b in blocks
                if cls.block_in_column(b, col)
            ]
            col_blocks = sorted(col_blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
            ordered.extend(col_blocks)

        return ordered
    
    @classmethod
    def detect_columns(cls, blocks: list[dict], page_width: float) -> list[tuple[float, float]]:
        text_blocks = [b for b in blocks if b.get("role") in ("paragraph", "heading", "caption")]

        if len(text_blocks) < 3:
            return [(0, page_width)]

        centers = sorted(
            ((b["bbox"][0] + b["bbox"][2]) / 2, b) for b in text_blocks
        )

        xs = [c for c, _ in centers]
        gaps = []

        for i in range(1, len(xs)):
            gaps.append((xs[i] - xs[i - 1], xs[i - 1], xs[i]))

        if not gaps:
            return [(0, page_width)]

        biggest_gap, left_x, right_x = max(gaps, key=lambda t: t[0])

        if biggest_gap > page_width * 0.15:
            split_x = (left_x + right_x) / 2
            return [(0, split_x), (split_x, page_width)]

        return [(0, page_width)]

    @classmethod
    def block_in_column(cls, block: dict, column: tuple[float, float]) -> bool:
        x0, x1 = column
        cx = (block["bbox"][0] + block["bbox"][2]) / 2
        return x0 <= cx <= x1