
import fitz
import numpy as np
import cv2

from app.services.process_document.helpers.geometry import Geometry

class TableBlocks:
    def __init__(self, table_candidates: list[dict]):
        self.table_candidates = table_candidates
        self.geometry = Geometry()

    def detect_table_candidates(self, page: fitz.Page, text_blocks: list[dict], image_regions: list[dict]) -> list[dict]:
        candidates = []

        text_tables = self.detect_text_based_tables(page)
        candidates.extend(text_tables)

        visual_tables = self.detect_visual_table_like_regions(page, image_regions)
        candidates.extend(visual_tables)

        return self.merge_overlapping_table_candidates(candidates)
    
    def detect_text_based_tables(self, page: fitz.Page) -> list[dict]:
        candidates = []

        tabs = page.find_tables()

        for tab in tabs:
            bbox = (tab.bbox.x0, tab.bbox.y0, tab.bbox.x1, tab.bbox.y1)

            candidates.append({
                "kind": "table_region",
                "bbox": bbox,
                "source_kind": "pymupdf_native",
                "table_obj": tab
            })

        return candidates
    
    def detect_visual_table_like_regions(self, page: fitz.Page) -> list[dict]:
        candidates = []

        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

        # We need to convert the image to grayscale because the thresholding algorithm expects a single-channel image.
        # The number of channels in the image (pix.n) does not affect the thresholding algorithm itself.
        # However, OpenCV provides different conversion functions for images with different numbers of channels.
        # Therefore, we need to use the correct conversion function based on the number of channels in the image.

        if pix.n >= 4:
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        line_length = int(pix.w / 40)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (line_length, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, line_length))

        horizontal_lines = cv2.erode(thresh, horizontal_kernel, iterations=1)
        horizontal_lines = cv2.dilate(horizontal_lines, horizontal_kernel, iterations=1)

        vertical_lines = cv2.erode(thresh, vertical_kernel, iterations=1)
        vertical_lines = cv2.dilate(vertical_lines, vertical_kernel, iterations=1)

        table_mask = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0)
        _, table_mask = cv2.threshold(table_mask, 50, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            if w > 100 and h > 50:
                region_image = table_mask[y:y + h, x:x + w]
                likelihood = self.estimate_table_likelihood(region_image)

                if likelihood > 0.5:
                    candidates.append({
                        "kind": "table_candidate",
                        "bbox": (float(x), float(y), float(x+w), float(y+h)),
                        "source_kind": "cv2_visual",
                        "likelihood": likelihood
                    })

        return candidates
    
    def estimate_table_likelihood(self, region_image: np.ndarray) -> float:

        """
        Оценивает вероятность, что сетка - это таблица.
        Ищет точки пересечения вертикальных и горизонтальных линий (узлы сетки).
        """
        contours, _ = cv2.findContours(region_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        cells_count = len(contours)

        # Если найдено больше 4 ячеек (минимум 2х2), считаем это таблицей
        if cells_count > 4:
            return min(1.0, cells_count / 10.0)

        return 0

    def merge_overlapping_table_candidates(self, candidates: list[dict]) -> list[dict]:
        """Объединяет кандидатов, чьи bbox сильно пересекаются (IoU)."""
        if not candidates:
            return []
        
        candidates.sort(key=lambda c: (c["bbox"][2] - c["bbox"][0]) * (c["bbox"][3] - c["bbox"][1]), reverse=True)

        merged = []

        for cand in candidates:
            is_overlapping = False

            for m in merged:
                if self.geometry.bbox_iou(cand["bbox"], m["bbox"]) > 0.5:
                    is_overlapping = True
                    break

            if not is_overlapping:
                merged.append(cand)

        return merged
    
    def extract_table_as_text(self, block: dict, page: fitz.Page) -> list[dict]:
        # Если таблицу нашел сам PyMuPDF, у нас есть готовый объект
        if block.get("source") == "pymupdf_native" and "table_obj" in block:
            df = block["table_obj"].to_pandas()
            return df.to_markdown(index=False)
        #Если это визуальный блок, извлекаем текст по координатам (с сохранением разрывов)
        rect = block["bbox"]
        return page.get_text("text", clip=rect)
