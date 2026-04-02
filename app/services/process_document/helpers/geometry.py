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
    
    @classmethod
    def remove_heavy_overlaps(blocks: list[dict], iou_threshold: float = 0.7) -> list[dict]:
        """
        Удаляет дубликаты и блоки, которые 'съедены' более важными объектами.
        """
        # Сортируем блоки по приоритету: сначала таблицы, потом картинки, потом текст
        priority = {"table_candidate": 3, "image_region": 2, "text_block": 1}
        sorted_blocks = sorted(blocks, key=lambda b: priority.get(b["kind"], 0), reverse=True)
        
        final_blocks = []
        
        for current_block in sorted_blocks:
            is_covered = False
            for master in final_blocks:
                # Если текущий блок почти полностью внутри уже добавленного (более приоритетного)
                if Geometry.calculate_intersection_ratio(current_block["bbox"], master["bbox"]) > iou_threshold:
                    is_covered = True
                    break
            
            if not is_covered:
                final_blocks.append(current_block)
                
        # Возвращаем блоки в порядке их расположения на странице (сверху вниз)
        return sorted(final_blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))

    @classmethod
    def calculate_intersection_ratio(bbox_small, bbox_large):
        """Какую часть маленького блока занимает пересечение с большим."""
        x0 = max(bbox_small[0], bbox_large[0])
        y0 = max(bbox_small[1], bbox_large[1])
        x1 = min(bbox_small[2], bbox_large[2])
        y1 = min(bbox_small[3], bbox_large[3])
        
        if x1 <= x0 or y1 <= y0: return 0.0
        
        intersection_area = (x1 - x0) * (y1 - y0)
        small_area = (bbox_small[2] - bbox_small[0]) * (bbox_small[3] - bbox_small[1])
        
        return intersection_area / small_area if small_area > 0 else 0