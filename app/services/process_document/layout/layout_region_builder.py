from app.services.process_document.helpers.geometry import Geometry

class LayoutRegionBuilder:

    @classmethod
    def build_regions(cls, primitives: dict) -> list[dict]:
        candidates = []

        for b in primitives["native_text_blocks"]:
            candidates.append({
                "kind": "region_candidate",
                "bbox": b["bbox"],
                "source_kind": "native_text_block",
                "members": [b],
            })

        for b in primitives["image_regions"]:
            candidates.append({
                "kind": "region_candidate",
                "bbox": tuple(b["bbox"]),
                "source_kind": "image_region",
                "members": [b],
            })

        for b in primitives["table_candidates"]:
            candidates.append({
                "kind": "region_candidate",
                "bbox": tuple(b["bbox"]),
                "source_kind": "table_candidate",
                "members": [b],
            })

        for b in primitives["visual_components"]:
            candidates.append({
                "kind": "region_candidate",
                "bbox": tuple(b["bbox"]),
                "source_kind": "visual_component",
                "members": [b],
            })

        candidates = cls.merge_nested_candidates(candidates)
        candidates = cls.merge_close_candidates(candidates)
        candidates = cls.apply_whitespace_segmentation(candidates, primitives)

        return candidates
    
    @classmethod
    def merge_nested_candidates(cls, candidates: list[dict]) -> list[dict]:
        result = []

        candidates = sorted(
            candidates,
            key=lambda c: Geometry.bbox_area(c["bbox"]),
            reverse=True
        )

        for candidate in candidates:
            merged_into_existing = False

            for existing in result:
                ratio = Geometry.calculate_intersection_ratio(candidate["bbox"], existing["bbox"])
                if ratio > 0.85:
                    existing["members"].extend(candidate["members"])
                    merged_into_existing = True
                    break

            if not merged_into_existing:
                result.append(candidate)

        return result
    
    @classmethod
    def merge_close_candidates(cls, candidates: list[dict]) -> list[dict]:
        changed = True

        while changed:
            changed = False
            new_candidates = []
            used = [False] * len(candidates)

            for i, a in enumerate(candidates):
                if used[i]:
                    continue

                current = a

                for j in range(i + 1, len(candidates)):
                    if used[j]:
                        continue

                    b = candidates[j]
                    if cls.should_merge_regions(current, b):
                        current = {
                            "kind": "region_candidate",
                            "bbox": Geometry.union_bbox(current["bbox"], b["bbox"]),
                            "source_kind": "merged",
                            "members": current["members"] + b["members"],
                        }
                        used[j] = True
                        changed = True

                used[i] = True
                new_candidates.append(current)

            candidates = new_candidates

        return candidates

    @classmethod
    def should_merge_regions(cls, a: dict, b: dict) -> bool:
        horiz_gap = Geometry.horizontal_gap(a["bbox"], b["bbox"])
        vert_gap = Geometry.vertical_gap(a["bbox"], b["bbox"])
        overlap_y = Geometry.vertical_overlap_ratio(a["bbox"], b["bbox"])
        overlap_x = Geometry.horizontal_overlap_ratio(a["bbox"], b["bbox"])

        # соседние по горизонтали блоки в одной строке
        if horiz_gap < 20 and overlap_y > 0.5:
            return True

        # соседние по вертикали куски одного текста/региона
        if vert_gap < 20 and overlap_x > 0.5:
            return True

        return False
    
    @classmethod
    def apply_whitespace_segmentation(cls, candidates: list[dict], primitives: dict) -> list[dict]:
        # На первом этапе можно просто вернуть как есть,
        # а потом усложнить.
        return candidates