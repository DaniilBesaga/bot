import fitz

class Geometry:
    def bbox_width(bbox: fitz.Rect) -> float:
        return bbox[2] - bbox[0]
    def bbox_height(bbox: fitz.Rect) -> float:
        return bbox[3] - bbox[1]
    def bbox_area(bbox: fitz.Rect) -> float:
        return Geometry.bbox_width(bbox) * Geometry.bbox_height(bbox)
    def bbox_center(bbox: fitz.Rect) -> tuple[float,float]:
        return (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    def vertical_gap(bbox1: fitz.Rect, bbox2: fitz.Rect) -> float:
        return max(0, bbox2[1] - bbox1[3], bbox1[1] - bbox2[3])
    def horizontal_gap(bbox1: fitz.Rect, bbox2: fitz.Rect) -> float:
        return max(0, bbox2[0] - bbox1[2], bbox1[0] - bbox2[2])
    
    def bbox_intersection_area(bbox1: fitz.Rect, bbox2: fitz.Rect) -> float:
        dx = min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0])
        dy = min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1])
        return dx * dy if (dx > 0 and dy > 0) else 0.0
    def bbox_iou(bbox1: fitz.Rect, bbox2: fitz.Rect) -> float:
        return Geometry.bbox_intersection_area(bbox1, bbox2) / Geometry.bbox_area(bbox1)
    def is_above(bbox1, bbox2) -> bool:
        # bbox1 выше чем bbox2, если его нижняя граница выше (меньше) верхней границы bbox2
        return bbox1[3] <= bbox2[1]

    def is_below(bbox1, bbox2) -> bool:
        return bbox1[1] >= bbox2[3]
    
    def sort_by_reading_order(blocks: list[dict], tolerance: float = 5.0) -> list[dict]:
        """
        Сортировка: сначала сверху вниз, потом слева направо.
        tolerance помогает группировать блоки в одну 'строку', если их Y немного пляшут.
        """
        return sorted(
            blocks, 
            key=lambda b: (round(b["bbox"][1] / tolerance), b["bbox"][0])
        )