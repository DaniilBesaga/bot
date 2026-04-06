import fitz

from app.services.process_document.helpers.text_blocks import TextBlocks
from app.services.process_document.helpers.table_blocks import TableBlocks
from app.services.process_document.helpers.visual_blocks import VisualBlocks

class PrimitivesExtractor:

    @classmethod
    def extract(cls, page: fitz.Page) -> dict:
        page_width = page.rect.width
        page_height = page.rect.height

        spans = TextBlocks.extract_spans(page)
        lines = TextBlocks.build_lines_from_spans(spans)
        native_text_blocks = TextBlocks.extract_native_text_blocks(page)

        words = page.get_text("words")
        drawings = page.get_drawings()

        image_regions = VisualBlocks.extract_image_regions(page)
        table_candidates = TableBlocks.detect_table_candidates(page, image_regions)
        visual_components = VisualBlocks.extract_visual_components(page)

        return {
            "page_width": page_width,
            "page_height": page_height,
            "spans": spans,
            "lines": lines,
            "words": words,
            "native_text_blocks": native_text_blocks,
            "drawings": drawings,
            "image_regions": image_regions,
            "table_candidates": table_candidates,
            "visual_components": visual_components,
        }