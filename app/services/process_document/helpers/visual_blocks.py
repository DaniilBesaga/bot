import fitz
import numpy as np
import cv2

class VisualBlocks:
    def __init__(self, blocks: list[dict], tolerance: float = 5.0):
        self.blocks = blocks
        self.tolerance = tolerance

    def extract_image_regions(self, page: fitz.Page) -> list[dict]:
        image_regions = []

        pdf_images = self.try_extract_pdf_images(page)

        image_regions.extend(pdf_images)

        if not image_regions:
            visual_regions = self.detect_visual_regions_from_render(page)
            image_regions.extend(visual_regions)

        return image_regions

        

    def try_extract_pdf_images(self, page: fitz.Page) -> list[dict]:
        result = []

        image_objects = page.get_images(full=True)

        for image_info in image_objects:
            xref = image_info[0]

            bbox = self.try_get_image_bbox(page, xref)

            if bbox is None:
                continue
            
            result.append({
                "kind": "image_region",
                "bbox": bbox,
                "source_kind": "pdf_image"
            })

        return result
    
    def try_get_image_bbox(self, page: fitz.Page, xref) -> fitz.Rect | None:
        return page.get_image_rects(xref)
    
    def detect_visual_regions_from_render(self, page: fitz.Page) -> list[dict]:
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