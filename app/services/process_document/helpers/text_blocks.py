import fitz

class TextBlocks:
    def extract_text_blocks(page: fitz.Page) -> list[dict]:
        return page.get_text("blocks")

    def extract_words(page: fitz.Page) -> str:
        raw_words = page.get_text("words")

        words = []

        for w in raw_words:
            x0, y0, x1, y1, text = w[:4]
            words.append({
                "bbox": (x0, y0, x1, y1),
                "text": text
            })

        return words
    
    def build_lines_from_words(words: list[dict], y_threshold: float = 3.0) -> list[dict]:
        words = sorted(words, key=lambda w: (w["bbox"][1], w["bbox"][0]))

        lines = []
        current_line = []

        for w in words:
            if not current_line:
                current_line.append(w)
                continue

            prev = current_line[-1]

            prev_y = prev["bbox"][1]
            current_y = w["bbox"][1]

            if(abs(current_y - prev_y) < y_threshold):
                current_line.append(w)
            else:
                lines.append(TextBlocks.make_line(current_line))
                current_line = [w]

        if current_line:
            lines.append(TextBlocks.make_line(current_line))

        return lines
    
    def make_line(words_in_line: list[dict]):
        words_in_line = sorted(words_in_line, key=lambda w: w["bbox"][0])

        line_text = " ".join(w["text"] for w in words_in_line)

        x0 = words_in_line[0]["bbox"][0]
        y0 = words_in_line[0]["bbox"][1]
        x1 = words_in_line[-1]["bbox"][2]
        y1 = words_in_line[-1]["bbox"][3]

        return {
            "bbox": (x0, y0, x1, y1),
            "text": line_text,
            "kind": "line",
            "words": words_in_line
        }