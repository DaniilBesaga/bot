from app.core.constants import MAX_CHUNK_CHARS, CHUNK_OVERLAP_CHARS


class ParagraphChunker:
    def __init__(self, max_chars: int = MAX_CHUNK_CHARS, overlap_chars: int = CHUNK_OVERLAP_CHARS):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> list[dict]:
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current = ""
        index = 0

        for paragraph in paragraphs:
            candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph

            if len(candidate) <= self.max_chars:
                current = candidate
            else:
                if current:
                    chunks.append({
                        "chunk_index": index,
                        "text": current,
                    })
                    index += 1

                overlap = current[-self.overlap_chars:] if current else ""
                current = f"{overlap}\n\n{paragraph}".strip()

        if current:
            chunks.append({
                "chunk_index": index,
                "text": current,
            })

        return chunks