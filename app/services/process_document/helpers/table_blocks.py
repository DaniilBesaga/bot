import fitz
import numpy as np
import cv2
import pandas as pd

from app.services.process_document.helpers.geometry import Geometry
from app.services.process_document.helpers.ocr import OCR


class TableBlocks:
    @classmethod
    def detect_table_candidates(cls, page: fitz.Page, image_regions: list[dict]) -> list[dict]:
        candidates = []

        # 1. Нативные таблицы PyMuPDF
        for tab in page.find_tables():
            candidates.append({
                "kind": "table_candidate",
                "bbox": tuple(tab.bbox),
                "source_kind": "pymupdf_native",
                "table_obj": tab
            })

        # 2. Визуальные таблицы через render + cv2
        candidates.extend(cls.detect_visual_table_like_regions(page))

        return cls.merge_overlapping_table_candidates(candidates)

    @classmethod
    def detect_visual_table_like_regions(cls, page: fitz.Page) -> list[dict]:
        candidates = []

        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

        if pix.n >= 4:
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        line_length = max(20, int(pix.w / 40))
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (line_length, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, line_length))

        horizontal = cv2.erode(thresh, horizontal_kernel, iterations=1)
        horizontal = cv2.dilate(horizontal, horizontal_kernel, iterations=1)

        vertical = cv2.erode(thresh, vertical_kernel, iterations=1)
        vertical = cv2.dilate(vertical, vertical_kernel, iterations=1)

        mask = cv2.addWeighted(horizontal, 0.5, vertical, 0.5, 0)
        _, mask = cv2.threshold(mask, 50, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            if w > 100 and h > 50:
                candidates.append({
                    "kind": "table_candidate",
                    "bbox": (float(x), float(y), float(x + w), float(y + h)),
                    "source_kind": "cv2_visual"
                })

        return candidates

    @classmethod
    def merge_overlapping_table_candidates(cls, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []

        priority = {
            "pymupdf_native": 2,
            "cv2_visual": 1
        }

        candidates = sorted(
            candidates,
            key=lambda c: (
                priority.get(c.get("source_kind"), 0),
                Geometry.bbox_area(c["bbox"])
            ),
            reverse=True
        )

        result = []
        for cand in candidates:
            duplicate = False

            for existing in result:
                r1 = Geometry.calculate_intersection_ratio(cand["bbox"], existing["bbox"])
                r2 = Geometry.calculate_intersection_ratio(existing["bbox"], cand["bbox"])

                if r1 > 0.8 or r2 > 0.8:
                    duplicate = True
                    break

            if not duplicate:
                result.append(cand)

        return result

    @classmethod
    def extract_table_as_text(cls, block: dict, page: fitz.Page) -> str:
        """
        Простая стратегия:
        1. если есть native table -> пробуем to_pandas()
        2. если dataframe плохой или exception -> OCR
        3. если просто визуальная таблица -> OCR
        """

        if block.get("source_kind") == "pymupdf_native" and block.get("table_obj") is not None:
            try:
                df = block["table_obj"].to_pandas()

                if cls.is_good_dataframe(df):
                    return df.to_markdown(index=False)
            except Exception:
                pass

        return OCR.extract_text_from_image_region(page=page, bbox=block["bbox"])

    @classmethod
    def is_good_dataframe(cls, df: pd.DataFrame) -> bool:
        if df is None or df.empty:
            return False

        rows, cols = df.shape
        if rows < 2 or cols < 2:
            return False

        total_cells = rows * cols
        nan_cells = int(df.isna().sum().sum())
        nan_ratio = nan_cells / total_cells if total_cells else 1.0

        # если слишком много пустых ячеек — считаем мусором
        if nan_ratio > 0.4:
            return False

        non_empty = 0
        short_garbage = 0

        for col in df.columns:
            for val in df[col]:
                if pd.isna(val):
                    continue

                s = str(val).strip()
                if not s:
                    continue

                non_empty += 1

                # очень короткие обрывки часто признак плохой таблицы
                if len(s) <= 1:
                    short_garbage += 1

        if non_empty == 0:
            return False

        if short_garbage / non_empty > 0.35:
            return False

        return True

    @classmethod
    def classify_table_block(cls, block: dict) -> dict:
        if block.get("source_kind") == "pymupdf_native":
            block["role"] = "structured_table"
        else:
            block["role"] = "visual_table"
        return block