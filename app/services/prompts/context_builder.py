from db.models import Chunk


class ContextBuilder:
    @staticmethod
    def build_context(candidates: list[dict], max_chunks: int = 5) -> str:
        parts: list[str] = []

        for i, item in enumerate(candidates[:max_chunks], start=1):
            chunk: Chunk = item["chunk"]

            heading = chunk.heading_text.strip() if chunk.heading_text else ""
            raw_text = chunk.raw_text.strip() if chunk.raw_text else ""

            section_parts = [f"[Chunk {i}]"]

            if heading:
                section_parts.append(f"Title: {heading}")

            if chunk.doc_id:
                section_parts.append(f"Document: {chunk.doc_id}")

            if raw_text:
                section_parts.append(raw_text)

            parts.append("\n".join(section_parts))

        return "\n\n".join(parts).strip()