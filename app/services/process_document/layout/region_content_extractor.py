import fitz

from app.services.process_document.helpers.text_blocks import TextBlocks
from app.services.process_document.helpers.table_blocks import TableBlocks
from app.services.process_document.helpers.ocr import OCR
from app.services.process_document.layout.region_classifier import RegionClassifier

class RegionContentExtractor:

    @classmethod
    def extract_blocks(cls, page: fitz.Page, regions: list[dict]) -> list[dict]:
        blocks = []

        for region in regions:
            role = region["role"]

            if role == "paragraph_area":
                blocks.extend(cls.extract_paragraph_blocks(region))

            elif role == "heading_area":
                blocks.extend(cls.extract_heading_blocks(region))

            elif role == "table_area":
                blocks.append(cls.extract_table_block(region, page))

            elif role == "figure_area":
                blocks.append(cls.extract_figure_block(region, page))

            elif role == "caption_area":
                blocks.append(cls.extract_caption_block(region))

            elif role == "header_footer_area":
                blocks.append(cls.extract_header_footer_block(region))

        return blocks
    
    @classmethod
    def extract_paragraph_blocks(cls, region: dict) -> list[dict]:
        text_members = [m for m in region["members"] if m.get("kind") == "native_text_block"]
        lines = []

        for member in text_members:
            lines.extend(member.get("lines", []))

        lines = sorted(lines, key=lambda l: (l["bbox"][1], l["bbox"][0]))
        paragraphs = TextBlocks.build_blocks_from_lines(lines)

        for p in paragraphs:
            p["kind"] = "text_block"
            p["role"] = "paragraph"

        return paragraphs

    @classmethod
    def extract_heading_blocks(cls, region: dict) -> list[dict]:
        text = RegionClassifier.collect_region_text(region["members"])
        return [{
            "kind": "text_block",
            "role": "heading",
            "bbox": region["bbox"],
            "text": text
        }]
    
    @classmethod
    def extract_table_block(cls, region: dict, page: fitz.Page) -> dict:
        table_members = [m for m in region["members"] if m.get("kind") == "table_candidate"]

        best_table = None
        for m in table_members:
            if m.get("source_kind") == "pymupdf_native":
                best_table = m
                break

        block = {
            "kind": "table_block",
            "role": "structured_table" if best_table and best_table.get("source_kind") == "pymupdf_native" else "visual_table",
            "bbox": region["bbox"],
            "text": ""
        }

        if best_table:
            block["text"] = TableBlocks.extract_table_as_text(best_table, page)
        else:
            rect = fitz.Rect(region["bbox"])
            text = page.get_text("text", clip=rect).strip()
            block["text"] = text if text else OCR.extract_text_from_image_region(page, region["bbox"])

        return block
    
    @classmethod
    def extract_figure_block(cls, region: dict, page: fitz.Page) -> dict:
        need_ocr = cls.figure_needs_ocr(region, page)

        text = ""
        if need_ocr:
            text = OCR.extract_text_from_image_region(page, region["bbox"])

        return {
            "kind": "image_block",
            "role": "figure",
            "bbox": region["bbox"],
            "text": text
        }

    @classmethod
    def figure_needs_ocr(cls, region: dict, page: fitz.Page) -> bool:
        bbox = region["bbox"]
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        page_w = page.rect.width
        page_h = page.rect.height

        # полностраничный скан
        if w > page_w * 0.8 and h > page_h * 0.7:
            return True

        # потом можно добавить more advanced text density heuristic
        return False
    
    @classmethod
    def extract_caption_block(cls, region: dict) -> dict:
        text = RegionClassifier.collect_region_text(region["members"])
        return {
            "kind": "text_block",
            "role": "caption",
            "bbox": region["bbox"],
            "text": text
        }
    
    @classmethod
    def extract_header_footer_block(cls, region: dict) -> dict:
        text = RegionClassifier.collect_region_text(region["members"])
        return {
            "kind": "text_block",
            "role": "header_footer",
            "bbox": region["bbox"],
            "text": text
        }