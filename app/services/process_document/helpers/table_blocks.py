import fitz
import cv2
import numpy as np
import pandas as pd

from app.services.process_document.helpers.geometry import Geometry
from app.services.process_document.helpers.ocr import OCR


class TableBlocks:
    @classmethod
    def detect_table_candidates(cls, page: fitz.Page, image_regions: list[dict]) -> list[dict]:
        candidates: list[dict] = []

        # 1. Нативные таблицы PyMuPDF
        try:
            tables = page.find_tables()
            for tab in tables:
                candidates.append({
                    "kind": "table_candidate",
                    "bbox": tuple(tab.bbox),
                    "source_kind": "pymupdf_native",
                    "table_obj": tab
                })
        except Exception:
            pass

        # 2. Визуальные таблицы через render + cv2
        candidates.extend(cls.detect_visual_table_like_regions(page))

        print("PAGE:", page.number)

        tables = page.find_tables()
        print("native tables:", len(tables.tables if hasattr(tables, "tables") else tables))

        visual = cls.detect_visual_table_like_regions(page)
        print("visual table candidates:", len(visual))

        # 3. Убираем дубли
        return cls.merge_overlapping_table_candidates(candidates)

    @classmethod
    def detect_visual_table_like_regions(cls, page: fitz.Page) -> list[dict]:
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

        if pix.n >= 4:
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        # Чуть мягче порог
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)

        line_length = max(20, pix.w // 40)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (line_length, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, line_length))

        horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel)
        vertical = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel)

        mask = cv2.bitwise_or(horizontal, vertical)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        scale_x = page.rect.width / pix.w
        scale_y = page.rect.height / pix.h

        candidates: list[dict] = []

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            # слишком мелкие игнорим
            if w < 80 or h < 40:
                continue

            pdf_bbox = (
                float(x * scale_x),
                float(y * scale_y),
                float((x + w) * scale_x),
                float((y + h) * scale_y),
            )

            candidates.append({
                "kind": "table_candidate",
                "bbox": pdf_bbox,
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

        result: list[dict] = []

        for cand in candidates:
            is_duplicate = False

            for existing in result:
                r1 = Geometry.calculate_intersection_ratio(cand["bbox"], existing["bbox"])
                r2 = Geometry.calculate_intersection_ratio(existing["bbox"], cand["bbox"])

                if r1 > 0.8 or r2 > 0.8:
                    is_duplicate = True
                    break

            if not is_duplicate:
                result.append(cand)

        return result

    @classmethod
    def extract_table_as_text(cls, block: dict, page: fitz.Page) -> str:
        # 1. Сначала пробуем нативную таблицу
        if block.get("source_kind") == "pymupdf_native" and block.get("table_obj") is not None:
            try:
                df = block["table_obj"].to_pandas()

                if cls.is_good_dataframe(df):
                    return df.fillna("").to_markdown(index=False)
            except Exception:
                pass

        # 2. Иначе OCR
        return OCR.extract_text_from_image_region(
            page=page,
            bbox=block["bbox"]
        )

    @classmethod
    def is_good_dataframe(cls, df: pd.DataFrame) -> bool:
        if df is None or df.empty:
            return False

        rows, cols = df.shape
        if rows < 1 or cols < 2:
            return False

        total_cells = rows * cols
        if total_cells == 0:
            return False

        nan_cells = int(df.isna().sum().sum())
        nan_ratio = nan_cells / total_cells

        # Не слишком жёстко
        if nan_ratio > 0.75:
            return False

        non_empty = 0
        for col in df.columns:
            for val in df[col]:
                if pd.isna(val):
                    continue
                if str(val).strip():
                    non_empty += 1

        return non_empty > 0

    @classmethod
    def classify_table_block(cls, block: dict) -> dict:
        block["role"] = (
            "structured_table"
            if block.get("source_kind") == "pymupdf_native"
            else "visual_table"
        )
        return block