import fitz
import numpy as np
import cv2

class VisualBlocks:
    def __init__(self, blocks: list[dict], tolerance: float = 5.0):
        self.blocks = blocks
        self.tolerance = tolerance

    @classmethod
    def extract_image_regions(cls, page: fitz.Page) -> list[dict]:
        image_regions = []

        pdf_images = VisualBlocks.try_extract_pdf_images(page)

        image_regions.extend(pdf_images)

        if not image_regions:
            visual_regions = VisualBlocks.detect_visual_regions_from_render(page)
            image_regions.extend(visual_regions)

        return image_regions

        
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
                "bbox": bbox,
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
    def classify_visual_block(cls, block: dict, page: fitz.Page, page_layout: dict) -> dict:
        bbox = block.get("bbox")
        page_width = page_layout.get("page_width", 595)
        page_height = page_layout.get("page_height", 842)
        
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        # Логотип: маленький, в верхней части страницы
        if w < 150 and h < 150 and bbox[1] < page_height * 0.2:
            block["role"] = "logo"
        # Полностраничное изображение/скан
        elif w > page_width * 0.8 and h > page_height * 0.7:
            block["role"] = "page_render"
        else:
            block["role"] = "figure"
            
        return block