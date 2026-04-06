import fitz
import numpy as np
import cv2

from app.services.process_document.helpers.geometry import Geometry


class VisualBlocks:
    def __init__(self, blocks: list[dict], tolerance: float = 5.0):
        self.blocks = blocks
        self.tolerance = tolerance

    @classmethod
    def extract_image_regions(cls, page: fitz.Page) -> list[dict]:
        pdf_images = VisualBlocks.try_extract_pdf_images(page)
        visual_regions = VisualBlocks.detect_visual_regions_from_render(page)

        all_regions = pdf_images + visual_regions
        return VisualBlocks.merge_regions(all_regions)
    
    @classmethod
    def extract_visual_components(cls, page: fitz.Page) -> list[dict]:
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

        if pix.n >= 4:
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
        merged = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(merged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        result = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w < 20 or h < 20:
                continue

            result.append({
                "kind": "visual_component",
                "bbox": (float(x), float(y), float(x + w), float(y + h))
            })

        return result

    @classmethod
    def try_extract_pdf_images(cls, page: fitz.Page) -> list[dict]:
        result = []

        image_objects = page.get_images(full=True)

        for image_info in image_objects:
            xref = image_info[0]
            bbox = VisualBlocks.try_get_image_bbox(page, xref)

            if bbox is None:
                continue

            result.append({
                "kind": "image_region",
                "bbox": tuple(bbox),
                "source_kind": "pdf_image"
            })

        return result

    @classmethod
    def try_get_image_bbox(cls, page: fitz.Page, xref) -> fitz.Rect | None:
        rects = page.get_image_rects(xref)
        return rects[0] if rects else None

    @classmethod
    def detect_visual_regions_from_render(cls, page: fitz.Page) -> list[dict]:
        pix = page.get_pixmap()

        if pix.n >= 4:
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 4)
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        else:
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        result = []

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            if w > 50 and h > 50:
                result.append({
                    "kind": "image_region",
                    "bbox": (float(x), float(y), float(x + w), float(y + h)),
                    "source_kind": "render_detected"
                })

        return result

    @classmethod
    def merge_regions(
        cls,
        regions: list[dict],
        intersection_threshold: float = 0.85,
        near_gap: float = 12.0
    ) -> list[dict]:
        """
        Объединяет:
        1. почти одинаковые регионы;
        2. вложенные регионы;
        3. очень близкие регионы, если они похожи на части одной картинки.
        """
        if not regions:
            return []

        # Нормализуем bbox в tuple
        normalized = []
        for r in regions:
            normalized.append({
                **r,
                "bbox": tuple(r["bbox"])
            })

        # Сначала убираем почти полные дубли / вложенности
        normalized = cls._deduplicate_nested_regions(
            normalized,
            intersection_threshold=intersection_threshold
        )

        # Потом пробуем склеить близкие куски
        normalized = cls._merge_close_regions(
            normalized,
            near_gap=near_gap
        )

        # Финальная сортировка
        normalized.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
        return normalized

    @classmethod
    def _deduplicate_nested_regions(
        cls,
        regions: list[dict],
        intersection_threshold: float = 0.85
    ) -> list[dict]:
        """
        Если один регион почти полностью покрывается другим,
        оставляем более надежный.
        """
        if not regions:
            return []

        priority = {
            "pdf_image": 3,
            "render_detected": 2,
            "unknown": 1
        }

        # Сначала более надежные, потом большие
        regions = sorted(
            regions,
            key=lambda r: (
                priority.get(r.get("source_kind", "unknown"), 0),
                Geometry.bbox_area(r["bbox"])
            ),
            reverse=True
        )

        result = []

        for candidate in regions:
            covered = False

            for existing in result:
                ratio_candidate_in_existing = Geometry.calculate_intersection_ratio(
                    candidate["bbox"],
                    existing["bbox"]
                )
                ratio_existing_in_candidate = Geometry.calculate_intersection_ratio(
                    existing["bbox"],
                    candidate["bbox"]
                )

                # почти одинаковые или вложенные
                if (
                    ratio_candidate_in_existing >= intersection_threshold
                    or ratio_existing_in_candidate >= intersection_threshold
                ):
                    covered = True
                    break

            if not covered:
                result.append(candidate)

        return result

    @classmethod
    def _merge_close_regions(
        cls,
        regions: list[dict],
        near_gap: float = 12.0
    ) -> list[dict]:
        """
        Склеивает регионы, если:
        - они почти соприкасаются
        - и сильно пересекаются по одной оси
        """
        if not regions:
            return []

        changed = True
        current = regions[:]

        while changed:
            changed = False
            new_regions = []
            used = [False] * len(current)

            for i, a in enumerate(current):
                if used[i]:
                    continue

                merged_region = a

                for j in range(i + 1, len(current)):
                    if used[j]:
                        continue

                    b = current[j]

                    if cls._should_merge_two_regions(merged_region, b, near_gap=near_gap):
                        merged_region = {
                            "kind": "image_region",
                            "bbox": Geometry.union_bbox(merged_region["bbox"], b["bbox"]),
                            "source_kind": cls._merge_source_kind(
                                merged_region.get("source_kind"),
                                b.get("source_kind")
                            )
                        }
                        used[j] = True
                        changed = True

                used[i] = True
                new_regions.append(merged_region)

            current = new_regions

        return current

    @classmethod
    def _should_merge_two_regions(
        cls,
        a: dict,
        b: dict,
        near_gap: float = 12.0
    ) -> bool:
        bbox_a = a["bbox"]
        bbox_b = b["bbox"]

        # Если уже сильно пересекаются — склеиваем
        inter_a = Geometry.calculate_intersection_ratio(bbox_a, bbox_b)
        inter_b = Geometry.calculate_intersection_ratio(bbox_b, bbox_a)
        if inter_a > 0.3 or inter_b > 0.3:
            return True

        h_gap = Geometry.horizontal_gap(bbox_a, bbox_b)
        v_gap = Geometry.vertical_gap(bbox_a, bbox_b)

        h_overlap = Geometry.horizontal_overlap_ratio(bbox_a, bbox_b)
        v_overlap = Geometry.vertical_overlap_ratio(bbox_a, bbox_b)

        # рядом по горизонтали, но по вертикали стоят на одной линии
        if h_gap <= near_gap and v_overlap > 0.6:
            return True

        # рядом по вертикали, но по горизонтали хорошо выровнены
        if v_gap <= near_gap and h_overlap > 0.6:
            return True

        return False

    @classmethod
    def _merge_source_kind(cls, a: str | None, b: str | None) -> str:
        """
        Если хотя бы один источник pdf_image — считаем merged регион более надежным.
        """
        kinds = {a, b}
        if "pdf_image" in kinds:
            return "pdf_image"
        if "render_detected" in kinds:
            return "render_detected"
        return "unknown"

    @classmethod
    def classify_visual_block(cls, block: dict, page: fitz.Page, page_layout: dict) -> dict:
        bbox = block.get("bbox")
        page_width = page_layout.get("page_width", 595)
        page_height = page_layout.get("page_height", 842)

        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        if w < 150 and h < 150 and bbox[1] < page_height * 0.2:
            block["role"] = "logo"
        elif w > page_width * 0.8 and h > page_height * 0.7:
            block["role"] = "page_render"
        else:
            block["role"] = "figure"

        return block