import fitz
import cv2
import numpy as np

from app.services.process_document.helpers.geometry import Geometry


class VisualBlocks:
    @classmethod
    def extract_image_regions(cls, page: fitz.Page) -> list[dict]:
        pdf_images = cls.try_extract_pdf_images(page)
        visual_regions = cls.detect_visual_regions_from_render(page)

        all_regions = pdf_images + visual_regions
        return cls.merge_regions(all_regions)

    @classmethod
    def try_extract_pdf_images(cls, page: fitz.Page) -> list[dict]:
        result: list[dict] = []

        try:
            image_objects = page.get_images(full=True)
        except Exception:
            return result

        for image_info in image_objects:
            xref = image_info[0]
            bbox = cls.try_get_image_bbox(page, xref)

            if bbox is None:
                continue

            result.append({
                "kind": "image_region",
                "bbox": tuple(bbox),
                "source_kind": "pdf_image"
            })

        return result
    
    @classmethod
    def try_get_image_bbox(cls, page: fitz.Page, xref: int) -> fitz.Rect | None:
        rects = page.get_image_rects(xref)
        return rects[0] if rects else None

    @classmethod
    def detect_visual_regions_from_render(cls, page: fitz.Page) -> list[dict]:
        pix = page.get_pixmap()
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)

        if pix.n >= 4:
            gray = cv2.cvtColor(img, cv2.COLOR_RGBA2GRAY)
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

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

        candidates = []

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)

            if w < 120 or h < 60:
                continue

            roi_h = horizontal[y:y+h, x:x+w]
            roi_v = vertical[y:y+h, x:x+w]
            roi_inter = cv2.bitwise_and(roi_h, roi_v)

            # количество контуров горизонтальных линий
            h_cnts, _ = cv2.findContours(roi_h, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            v_cnts, _ = cv2.findContours(roi_v, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            i_cnts, _ = cv2.findContours(roi_inter, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            h_lines = sum(1 for c in h_cnts if cv2.boundingRect(c)[2] > w * 0.3)
            v_lines = sum(1 for c in v_cnts if cv2.boundingRect(c)[3] > h * 0.3)
            intersections = len(i_cnts)

            # жёстче фильтруем
            if h_lines < 2:
                continue
            if v_lines < 2:
                continue
            if intersections < 4:
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
    def merge_regions(
        cls,
        regions: list[dict],
        intersection_threshold: float = 0.85
    ) -> list[dict]:
        if not regions:
            return []

        priority = {
            "pdf_image": 2,
            "render_detected": 1
        }

        regions = sorted(
            regions,
            key=lambda r: (
                priority.get(r.get("source_kind", ""), 0),
                Geometry.bbox_area(r["bbox"])
            ),
            reverse=True
        )

        result: list[dict] = []

        for candidate in regions:
            duplicate = False

            for existing in result:
                r1 = Geometry.calculate_intersection_ratio(candidate["bbox"], existing["bbox"])
                r2 = Geometry.calculate_intersection_ratio(existing["bbox"], candidate["bbox"])

                if r1 >= intersection_threshold or r2 >= intersection_threshold:
                    duplicate = True
                    break

            if not duplicate:
                result.append(candidate)

        result.sort(key=lambda r: (r["bbox"][1], r["bbox"][0]))
        return result

    @classmethod
    def classify_visual_block(cls, block: dict, page: fitz.Page, page_layout: dict) -> dict:
        bbox = block["bbox"]
        page_width = page_layout.get("page_width", page.rect.width)
        page_height = page_layout.get("page_height", page.rect.height)

        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]

        if w < 150 and h < 150 and bbox[1] < page_height * 0.2:
            block["role"] = "logo"
        elif w > page_width * 0.8 and h > page_height * 0.7:
            block["role"] = "page_render"
        else:
            block["role"] = "figure"

        return block