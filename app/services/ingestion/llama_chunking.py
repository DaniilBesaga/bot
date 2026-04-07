from app.dataclasses.classes import NormalizedBlock, NormalizedDocument


class ChunkingService:
    def __init__(self, max_chars: int = 1800):
        self.max_chars = max_chars

    def build_chunks(self, normalized: NormalizedDocument) -> list[dict]:
        chunks: list[dict] = []
        buffer_blocks: list[NormalizedBlock] = []
        chunk_index = 0

        def flush_buffer():
            nonlocal chunk_index, buffer_blocks

            if not buffer_blocks:
                return

            text_parts = [b.text for b in buffer_blocks if b.text]
            md_parts = [b.markdown for b in buffer_blocks if b.markdown]

            chunk_text = "\n\n".join(text_parts).strip()
            chunk_md = "\n\n".join(md_parts).strip()

            if not chunk_text:
                buffer_blocks = []
                return

            heading_path = buffer_blocks[-1].heading_path if buffer_blocks else []
            heading_prefix = " > ".join(heading_path).strip()

            final_text = chunk_text
            if heading_prefix:
                final_text = f"Section: {heading_prefix}\n\n{chunk_text}"

            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "chunk_type": "text",
                    "chunk_text": final_text,
                    "chunk_markdown": chunk_md or None,
                    "page_from": buffer_blocks[0].page_number,
                    "page_to": buffer_blocks[-1].page_number,
                    "heading_path": heading_path,
                    "metadata_json": {
                        "source_block_types": [b.block_type for b in buffer_blocks]
                    },
                }
            )

            chunk_index += 1
            buffer_blocks = []

        for block in normalized.blocks:
            if block.block_type == "heading":
                continue

            if block.block_type == "table":
                flush_buffer()

                heading_prefix = " > ".join(block.heading_path).strip()
                table_text = block.text or ""
                if heading_prefix:
                    table_text = f"Table under section: {heading_prefix}\n\n{table_text}"

                chunks.append(
                    {
                        "chunk_index": chunk_index,
                        "chunk_type": "table",
                        "chunk_text": table_text,
                        "chunk_markdown": block.markdown,
                        "page_from": block.page_number,
                        "page_to": block.page_number,
                        "heading_path": block.heading_path,
                        "metadata_json": block.metadata,
                    }
                )
                chunk_index += 1
                continue

            candidate_blocks = buffer_blocks + [block]
            candidate_text = "\n\n".join(b.text for b in candidate_blocks if b.text)

            if len(candidate_text) > self.max_chars and buffer_blocks:
                flush_buffer()

            buffer_blocks.append(block)

        flush_buffer()
        return chunks