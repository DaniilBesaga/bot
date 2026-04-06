from app.services.process_document.helpers.geometry import Geometry

class CaptionResolver:

    @classmethod
    def attach_captions(cls, blocks: list[dict]) -> list[dict]:
        captions = [b for b in blocks if b["role"] == "caption"]
        targets = [b for b in blocks if b["kind"] in ("table_block", "image_block")]

        for caption in captions:
            best_target = None
            best_score = None

            for target in targets:
                score = cls.caption_target_score(caption, target)
                if score is None:
                    continue

                if best_score is None or score < best_score:
                    best_score = score
                    best_target = target

            if best_target:
                best_target["caption"] = caption["text"]
                caption["attached_to"] = best_target.get("block_id")

        return blocks

    @classmethod
    def caption_target_score(cls, caption: dict, target: dict) -> float | None:
        cap = caption["bbox"]
        tgt = target["bbox"]

        vertical_dist = min(
            abs(cap[1] - tgt[3]),
            abs(tgt[1] - cap[3])
        )
        horizontal_overlap = Geometry.horizontal_overlap_ratio(cap, tgt)

        if horizontal_overlap < 0.3:
            return None

        if vertical_dist > 60:
            return None

        return vertical_dist