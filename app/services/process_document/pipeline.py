# import fitz

# from app.services.process_document.helpers.geometry import Geometry
# from app.services.process_document.helpers.ocr import OCR
# from app.services.process_document.helpers.table_blocks import TableBlocks
# from app.services.process_document.helpers.text_blocks import TextBlocks
# from app.services.process_document.helpers.visual_blocks import VisualBlocks


# class Pipeline:
    
#     @classmethod
#     def extract_page_layout(cls, page, page_number: int, doc_id: str) -> dict:
#         page_width = page.rect.width
#         page_height = page.rect.height
        
#         # 1. Достаем спаны — это наш фундамент
#         spans = TextBlocks.extract_spans(page)
        
#         # 2. Строим линии именно ИЗ СПАНОВ (сохраняем шрифты!)
#         lines = TextBlocks.build_lines_from_spans(spans)
        
#         # 3. Достаем слова просто "чтобы были" (для поиска или метаданных)
#         words = page.get_text("words") 

#         # 4. Все остальное как обычно
#         image_regions = VisualBlocks.extract_image_regions(page)
#         table_candidates = TableBlocks.detect_table_candidates(page, image_regions)

#         return {
#             "doc_id": doc_id,
#             "page_number": page_number,
#             "page_width": page_width,
#             "page_height": page_height,
#             "lines": lines,         # Самый важный элемент
#             "words": words,         # Вспомогательный
#             "image_regions": image_regions,
#             "table_candidates": table_candidates,
#         }
        
#     @classmethod
#     def build_primitive_blocks(cls, page_layout: dict) -> list[dict]:
#         primitive_blocks = []

#         # --- 1. ТЕКСТ ---
#         # Собираем линии в абзацы
#         text_based_blocks = TextBlocks.build_blocks_from_lines(page_layout["lines"])
#         for b in text_based_blocks:
#             b["kind"] = "text_block"
#             primitive_blocks.append(b)

#         # --- 2. КАРТИНКИ ---
#         for img in page_layout["image_regions"]:
#             primitive_blocks.append({
#                 "kind": "image_block",
#                 "bbox": img["bbox"],
#                 "image_data": img.get("image"), # Байты картинки для OCR
#                 "source": img.get("source_kind", "pdf_native")
#             })

#         # --- 3. ТАБЛИЦЫ ---
#         for tbl in page_layout["table_candidates"]:
#             primitive_blocks.append({
#                 "kind": "table_block",
#                 "bbox": tbl["bbox"],
#                 "table_obj": tbl.get("table_obj"),
#                 "source": tbl.get("source_kind", "unknown")
#             })

#         # --- 4. ОРКЕСТРАЦИЯ (Удаление наложений) ---
#         # Если bbox текста находится внутри bbox таблицы — текст удалится из списка, 
#         # чтобы не было дублей.
#         clean_blocks = Geometry.remove_heavy_overlaps(primitive_blocks)

#         return clean_blocks

#     @classmethod
#     def classify_primitive_blocks(cls, blocks: list[dict], page_layout: dict, page: fitz.Page) -> list[dict]:
#         for b in blocks:
#             kind = b.get("kind")
#             if kind == "text_block":
#                 TextBlocks.classify_text_block(b)
#             elif kind == "image_block":
#                 # Safer way to call in Pipeline
#                 VisualBlocks.classify_visual_block(block=b, page=page, page_layout=page_layout)
#             elif kind == "table_block":
#                 TableBlocks.classify_table_block(b)
#         return blocks

#     @classmethod
#     def index_blocks(cls, blocks: list[dict], doc_id: str, page_number: int) -> list[dict]:
#         # Обязательно сортируем! Это гарантирует правильный порядок чтения, 
#         # даже если блоки "перемешались" при удалении наложений.
#         blocks.sort(key=lambda b: (b["bbox"][1], b["bbox"][0]))
        
#         for idx, block in enumerate(blocks):
#             block["doc_id"] = doc_id          # <--- ADD THIS
#             block["page_number"] = page_number # <--- ADD THIS (Good for metadata)
#             block["position_index"] = idx
#             # Формат: IDдокумента_pНомерСтраницы_blockНомерБлока
#             block["block_id"] = f"{doc_id}_p{page_number}_block_{idx}"
            
#         return blocks
    
#     @classmethod
#     def populate_blocks_text(cls, blocks: list[dict], page: fitz.Page) -> list[dict]:
#         """Проходится по всем блокам и извлекает для них текст, пока доступен объект page."""
#         for block in blocks:
#             kind = block.get("kind")
#             role = block.get("role")

#             if kind == "text_block":
#                 # Текст уже собран в TextBlocks.make_line_from_spans, ничего не делаем
#                 pass

#             elif kind == "table_block":
#                 # Используем ваш отличный метод из TableBlocks
#                 block["text"] = TableBlocks.extract_table_as_text(block, page)

#             elif kind == "image_block":
#                 # Фильтруем мусор. Если это логотип — текст нам не нужен.
#                 if role == "logo":
#                     block["text"] = ""
#                 # Если это скан страницы или важный график, отправляем в OCR
#                 else:
#                     block["text"] = OCR.extract_text_from_image_region(page, block["bbox"])
                    
#         return blocks
    
#     @classmethod
#     def filter_noise_blocks(cls, blocks: list[dict]) -> list[dict]:
#         result = []

#         for b in blocks:
#             text = (b.get("text") or "").strip()
#             kind = b.get("kind")
#             bbox = b.get("bbox", (0, 0, 0, 0))
#             w = bbox[2] - bbox[0]
#             h = bbox[3] - bbox[1]

#             # очень маленькие блоки отбрасываем
#             if w < 8 or h < 8:
#                 continue

#             # пустой текстовый блок не нужен
#             if kind == "text_block" and not text:
#                 continue

#             # пустая таблица тоже не нужна
#             if kind == "table_block" and len(text) < 3:
#                 continue

#             # картинку без роли и без OCR можно отфильтровать отдельно по логике
#             result.append(b)

#         return result

#     @classmethod
#     def process_page(cls, page, page_number: int, doc_id: str) -> list[dict]:
#         """Оркестратор для обработки одной страницы целиком."""
        
#         # 1. Извлекаем сырые данные страницы
#         page_layout = cls.extract_page_layout(page, page_number, doc_id)
        
#         # 2. Собираем примитивные блоки и чистим наложения
#         primitive_blocks = cls.build_primitive_blocks(page_layout)
        
#         # 3. Классифицируем блоки (назначаем роли: заголовок, параграф, логотип и т.д.)
#         classified_blocks = cls.classify_primitive_blocks(primitive_blocks, page_layout, page)
        
#         # 4. НАПОЛНЯЕМ ТЕКСТОМ (Новый шаг!)
#         text_filled_blocks = cls.populate_blocks_text(classified_blocks, page)

#         filter_noise_blocks = cls.filter_noise_blocks(text_filled_blocks)
        
#         # 5. Индексируем и раздаем ID
#         final_blocks = cls.index_blocks(filter_noise_blocks, doc_id, page_number)
        
#         return final_blocks

import fitz

from app.services.process_document.layout.primitives_extractor import PrimitivesExtractor
from app.services.process_document.layout.layout_region_builder import LayoutRegionBuilder
from app.services.process_document.layout.reading_order import ReadingOrderResolver
from app.services.process_document.layout.region_classifier import RegionClassifier
from app.services.process_document.layout.region_content_extractor import RegionContentExtractor
from app.services.process_document.layout.caption_resolver import CaptionResolver
from app.services.process_document.layout.cleanup import Cleanup

class Pipeline:

    @classmethod
    def process_page(cls, page: fitz.Page, page_number: int, doc_id: str) -> list[dict]:
        primitives = PrimitivesExtractor.extract(page)

        regions = LayoutRegionBuilder.build_regions(primitives)
        regions = RegionClassifier.classify_regions(regions, primitives)

        blocks = RegionContentExtractor.extract_blocks(page, regions)
        blocks = Cleanup.run(blocks)
        blocks = ReadingOrderResolver.sort_blocks(blocks, primitives["page_width"])
        blocks = cls.index_blocks(blocks, doc_id, page_number)
        blocks = CaptionResolver.attach_captions(blocks)

        return blocks

    @classmethod
    def index_blocks(cls, blocks: list[dict], doc_id: str, page_number: int) -> list[dict]:
        for idx, block in enumerate(blocks):
            block["doc_id"] = doc_id
            block["page_number"] = page_number
            block["position_index"] = idx
            block["block_id"] = f"{doc_id}_p{page_number}_block_{idx}"
        return blocks