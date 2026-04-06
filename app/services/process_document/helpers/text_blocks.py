import fitz
import re

class TextBlocks:
    # Настройки
    LARGE_GAP_THRESHOLD = 8.0
    INDENT_THRESHOLD = 15.0
    Y_TOLERANCE = 3.0

    @classmethod
    def extract_spans(cls, page: fitz.Page) -> list[dict]:
        """
        Извлекает 'спаны' текста. Спан — это кусок текста с одним шрифтом и размером.
        """
        page_dict = page.get_text("dict")
        spans = []

        for block in page_dict.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        spans.append({
                            "bbox": span["bbox"],
                            "text": span["text"],
                            "font_size": round(span["size"], 1),
                            "font_name": span["font"]
                        })
        return spans
    
    @classmethod 
    def extract_words(cls, page: fitz.Page) -> list[dict]:
        return page.get_text("words")

    @classmethod
    def build_lines_from_spans(cls, spans: list[dict]) -> list[dict]:
        """Группирует спаны в строки по координате Y."""
        if not spans: return []
        
        # Сортируем по верху (y0), затем по леву (x0)
        spans = sorted(spans, key=lambda s: (s["bbox"][1], s["bbox"][0]))

        lines = []
        current_line_spans = []

        for s in spans:
            if not current_line_spans:
                current_line_spans.append(s)
                continue

            prev = current_line_spans[-1]
            # Считаем центры по Y
            prev_y_center = (prev["bbox"][1] + prev["bbox"][3]) / 2
            curr_y_center = (s["bbox"][1] + s["bbox"][3]) / 2

            if abs(curr_y_center - prev_y_center) < cls.Y_TOLERANCE:
                current_line_spans.append(s)
            else:
                lines.append(cls.make_line_from_spans(current_line_spans))
                current_line_spans = [s]

        if current_line_spans:
            lines.append(cls.make_line_from_spans(current_line_spans))

        return lines

    @classmethod
    def make_line_from_spans(cls, spans: list[dict]) -> dict:
        """Собирает строку из нескольких спанов и вычисляет её параметры."""
        spans = sorted(spans, key=lambda s: s["bbox"][0])

        parts = []
        prev = None

        for s in spans:
            if prev is not None:
                gap = s["bbox"][0] - prev["bbox"][2]
                if gap > max(1.5, prev["font_size"] * 0.15):
                    parts.append(" ")
            parts.append(s["text"])
            prev = s

        line_text = "".join(parts).strip()
        # Для строки берем максимальный размер шрифта, который в ней встретился
        max_font_size = max(s["font_size"] for s in spans)
        
        x0 = spans[0]["bbox"][0]
        y0 = min(s["bbox"][1] for s in spans)
        x1 = max(s["bbox"][2] for s in spans)
        y1 = max(s["bbox"][3] for s in spans)

        return {
            "bbox": (x0, y0, x1, y1),
            "text": line_text,
            "font_size": max_font_size,
            "kind": "line"
        }

    @classmethod
    def build_blocks_from_lines(cls, lines: list[dict]) -> list[dict]:
        """Группирует строки в смысловые блоки (абзацы)."""
        if not lines: return []
        
        blocks = []
        current_block_lines = []

        for l in lines:
            if not current_block_lines:
                current_block_lines.append(l)
                continue
            
            prev = current_block_lines[-1]

            if cls.should_merge_lines(prev, l):
                current_block_lines.append(l)
            else:
                blocks.append(cls.make_text_block(current_block_lines))
                current_block_lines = [l]

        if current_block_lines:
            blocks.append(cls.make_text_block(current_block_lines))

        return blocks

    @classmethod
    def should_merge_lines(cls, prev: dict, curr: dict) -> bool:
        """Логика склейки строк с учетом размера шрифта."""
        
        # 1. Если размер шрифта изменился значительно — это разные блоки
        if abs(curr["font_size"] - prev["font_size"]) > 1.0:
            return False

        # 2. Проверка на разрыв по вертикали
        line_height = prev["bbox"][3] - prev["bbox"][1]
        vertical_gap = curr["bbox"][1] - prev["bbox"][3]
        if vertical_gap > (line_height + cls.LARGE_GAP_THRESHOLD):
            return False

        # 3. Проверка на заголовки и списки
        if cls.looks_like_heading(curr):
            return False
        
        if cls.is_list_start(curr) and not cls.is_list_start(prev):
            return False

        # 4. Проверка на отступ (красную строку)
        if abs(curr["bbox"][0] - prev["bbox"][0]) > cls.INDENT_THRESHOLD:
            return False

        return True

    @classmethod
    def looks_like_heading(cls, line: dict) -> bool:
        """Заголовок: крупный шрифт или капс."""
        text = line["text"].strip()
        if not text: return False
        
        # Если шрифт больше 12.5 (стандарт обычно 10-12)
        if line["font_size"] > 12.5:
            return True
        
        # Если короткий текст капсом
        if text.isupper() and len(text) < 100 and not text.endswith((".", ":")):
            return True
            
        return False

    @classmethod
    def is_list_start(cls, line: dict) -> bool:
        text = line["text"].strip()
        pattern = r'^(\u2022|\-|\*|\d+\.|\d+\))\s+'
        return bool(re.match(pattern, text))

    @classmethod
    def make_text_block(cls, lines: list[dict]) -> dict:
        """Финальная сборка блока."""
        return {
            "bbox": (
                min(l["bbox"][0] for l in lines),
                min(l["bbox"][1] for l in lines),
                max(l["bbox"][2] for l in lines),
                max(l["bbox"][3] for l in lines)
            ),
            "text": " ".join(l["text"].strip() for l in lines),
            "font_size": lines[0]["font_size"], # Размер шрифта абзаца
            "kind": "text_block"
        }
    
    @classmethod
    def classify_text_block(cls, block: dict) -> dict:
        text = block.get("text", "").strip()
        font_size = block.get("font_size", 10)
        
        # 1. Заголовок (уже есть логика в looks_like_heading, используем её)
        if font_size > 12.5 or (text.isupper() and len(text) < 120):
            block["role"] = "heading"
        # 2. Элемент списка
        elif cls.is_list_start(block):
            block["role"] = "list_item"
        # 3. Мелкий текст (сноски)
        elif font_size < 8.5:
            block["role"] = "footnote"
        # 4. Обычный текст
        else:
            block["role"] = "paragraph"
            
        return block
    
    @classmethod
    def extract_native_text_blocks(cls, page: fitz.Page) -> list[dict]:
        page_dict = page.get_text("dict")
        result = []

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue

            lines = []
            for line in block.get("lines", []):
                line_spans = []
                for span in line.get("spans", []):
                    text = (span.get("text") or "").strip()
                    if not text:
                        continue
                    line_spans.append({
                        "text": text,
                        "bbox": tuple(span["bbox"]),
                        "font_size": round(span["size"], 1),
                        "font_name": span["font"],
                    })

                if line_spans:
                    lines.append(TextBlocks.make_line_from_spans(line_spans))

            if not lines:
                continue

            result.append({
                "kind": "native_text_block",
                "bbox": (
                    min(l["bbox"][0] for l in lines),
                    min(l["bbox"][1] for l in lines),
                    max(l["bbox"][2] for l in lines),
                    max(l["bbox"][3] for l in lines),
                ),
                "lines": lines,
                "text": " ".join(l["text"] for l in lines).strip()
            })

        return result