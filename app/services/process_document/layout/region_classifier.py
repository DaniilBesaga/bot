class RegionClassifier:

    @classmethod
    def classify_regions(cls, regions: list[dict], primitives: dict) -> list[dict]:
        for region in regions:
            region["role"] = cls.classify_region(region, primitives)
        return regions

    @classmethod
    def classify_region(cls, region: dict, primitives: dict) -> str:
        members = region.get("members", [])
        bbox = region["bbox"]

        has_table = any(m.get("kind") == "table_candidate" for m in members)
        has_image = any(m.get("kind") == "image_region" for m in members)
        has_native_text = any(m.get("kind") == "native_text_block" for m in members)

        if cls.is_header_footer_region(bbox, primitives):
            return "header_footer_area"

        if has_table:
            return "table_area"

        if has_image and not has_native_text:
            return "figure_area"

        if has_native_text:
            text = cls.collect_region_text(members)
            if cls.looks_like_heading_region(text, members):
                return "heading_area"
            if cls.looks_like_caption_region(text, bbox, primitives):
                return "caption_area"
            return "paragraph_area"

        if has_image:
            return "figure_area"

        return "marginalia_noise"
    
    @classmethod
    def collect_region_text(cls, members: list[dict]) -> str:
        texts = []
        for m in members:
            t = (m.get("text") or "").strip()
            if t:
                texts.append(t)
        return " ".join(texts).strip()

    @classmethod
    def looks_like_heading_region(cls, text: str, members: list[dict]) -> bool:
        if not text:
            return False

        font_sizes = []
        for m in members:
            for line in m.get("lines", []):
                font_sizes.append(line.get("font_size", 0))

        max_font = max(font_sizes) if font_sizes else 0

        if max_font > 12.5:
            return True

        if len(text) < 120 and text.isupper():
            return True

        return False

    @classmethod
    def looks_like_caption_region(cls, text: str, bbox: tuple, primitives: dict) -> bool:
        text_l = text.lower().strip()
        if not text_l:
            return False

        # caption_prefixes = ("fig.", "figure", "рис.", "рисунок", "table", "табл.", "таблица")
        # if text_l.startswith(caption_prefixes) and len(text) < 250:
        #     return True

        return False

    @classmethod
    def is_header_footer_region(cls, bbox: tuple, primitives: dict) -> bool:
        page_height = primitives["page_height"]
        y0, y1 = bbox[1], bbox[3]

        if y1 < page_height * 0.08:
            return True
        if y0 > page_height * 0.92:
            return True

        return False