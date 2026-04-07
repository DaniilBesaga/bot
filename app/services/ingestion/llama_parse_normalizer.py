

from app.dataclasses.classes import NormalizedBlock, NormalizedDocument


class LlamaParseNormalizer:
    def normalize(self, file_name: str, parse_result: dict) -> NormalizedDocument:
        blocks: list[NormalizedBlock] = []
        order_index = 0
        heading_stack: list[str] = []

        items_root = parse_result.get("items") or {}
        pages = items_root.get("pages", [])

        for page_idx, page in enumerate(pages, start=1):
            page_number = page.get("page_number") or page.get("page") or page_idx

            for item in page.get("items", []):
                item_type = item.get("type") or "unknown"
                value = item.get("value")
                md = item.get("md")

                if item_type == "heading":
                    level = item.get("level", 1)

                    while len(heading_stack) >= level:
                        heading_stack.pop()

                    heading_text = (value or md or "").strip()
                    if heading_text:
                        heading_stack.append(heading_text)

                    blocks.append(
                        NormalizedBlock(
                            block_type="heading",
                            text=heading_text or None,
                            markdown=md,
                            page_number=page_number,
                            order_index=order_index,
                            heading_level=level,
                            heading_path=heading_stack.copy(),
                            metadata={},
                        )
                    )
                    order_index += 1
                    continue

                if item_type in {"text", "paragraph"}:
                    blocks.append(
                        NormalizedBlock(
                            block_type="paragraph",
                            text=(value or md or "").strip() or None,
                            markdown=md,
                            page_number=page_number,
                            order_index=order_index,
                            heading_path=heading_stack.copy(),
                            metadata={},
                        )
                    )
                    order_index += 1
                    continue

                if item_type == "list":
                    list_text = self._flatten_list_item(item)
                    blocks.append(
                        NormalizedBlock(
                            block_type="list",
                            text=list_text or None,
                            markdown=md,
                            page_number=page_number,
                            order_index=order_index,
                            heading_path=heading_stack.copy(),
                            metadata={},
                        )
                    )
                    order_index += 1
                    continue

                if item_type == "table":
                    table_text = self._table_to_text(item)
                    blocks.append(
                        NormalizedBlock(
                            block_type="table",
                            text=table_text or None,
                            markdown=md,
                            page_number=page_number,
                            order_index=order_index,
                            heading_path=heading_stack.copy(),
                            metadata={"raw_table": item},
                        )
                    )
                    order_index += 1
                    continue

                blocks.append(
                    NormalizedBlock(
                        block_type=item_type,
                        text=(value or md or "").strip() or None,
                        markdown=md,
                        page_number=page_number,
                        order_index=order_index,
                        heading_path=heading_stack.copy(),
                        metadata={"raw_item": item},
                    )
                )
                order_index += 1

        return NormalizedDocument(
            file_name=file_name,
            markdown_full=parse_result.get("markdown_full"),
            text_full=parse_result.get("text_full"),
            blocks=blocks,
            raw_items=parse_result.get("items"),
        )

    def _flatten_list_item(self, item: dict) -> str:
        parts: list[str] = []

        for sub in item.get("items", []):
            val = (sub.get("value") or sub.get("md") or "").strip()
            if val:
                parts.append(f"- {val}")

        if parts:
            return "\n".join(parts)

        fallback = (item.get("value") or item.get("md") or "").strip()
        return fallback

    def _table_to_text(self, item: dict) -> str:
        if item.get("md"):
            return item["md"]

        rows = item.get("rows")
        if isinstance(rows, list):
            lines = []
            for row in rows:
                if isinstance(row, list):
                    line = " | ".join(str(cell) for cell in row)
                    lines.append(line)
            if lines:
                return "\n".join(lines)

        return (item.get("value") or "").strip()