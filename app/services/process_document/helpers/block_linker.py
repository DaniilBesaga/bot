class DocumentStructurizer:
    @staticmethod
    def attach_visual_blocks_to_context(all_blocks: list[dict]) -> list[dict]:
        """
        Проходит по всем блокам и добавляет изображениям/таблицам 
        информацию о ближайшем заголовке и соседнем тексте.
        """
        # 1. Важно: блоки должны быть отсортированы в порядке чтения!
        sorted_blocks = sorted(all_blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
        
        for i, block in enumerate(sorted_blocks):
            if block["kind"] in ["image_region", "table_candidate"]:
                # Ищем заголовок
                heading = DocumentStructurizer.find_nearest_heading_above(i, sorted_blocks)
                block["parent_heading"] = heading["text"] if heading else None
                
                # Ищем подпись (текст сразу сверху или снизу)
                block["context_above"] = DocumentStructurizer.find_nearest_text_above(i, sorted_blocks)
                block["context_below"] = DocumentStructurizer.find_nearest_text_below(i, sorted_blocks)
                
        return sorted_blocks

    @staticmethod
    def find_nearest_heading_above(current_idx: int, blocks: list[dict]) -> dict | None:
        """Идем вверх по списку от текущего блока в поиске ближайшего заголовка."""
        for i in range(current_idx - 1, -1, -1):
            if blocks[i].get("is_heading"): # Флаг, который мы поставили ранее
                return blocks[i]
        return None

    @staticmethod
    def find_nearest_text_above(current_idx: int, blocks: list[dict], max_distance: float = 30.0) -> str | None:
        """Ищем текст непосредственно над блоком (возможная подпись 'Рис. 1')."""
        if current_idx == 0: return None
        
        prev_block = blocks[current_idx - 1]
        if prev_block["kind"] == "text_block":
            # Проверяем расстояние между низом текста и верхом нашего блока
            dist = blocks[current_idx]["bbox"][1] - prev_block["bbox"][3]
            if dist < max_distance:
                return prev_block["text"]
        return None

    @staticmethod
    def find_nearest_text_below(current_idx: int, blocks: list[dict], max_distance: float = 30.0) -> str | None:
        """Ищем текст непосредственно под блоком (возможная подпись к таблице)."""
        if current_idx >= len(blocks) - 1: return None
        
        next_block = blocks[current_idx + 1]
        if next_block["kind"] == "text_block":
            dist = next_block["bbox"][1] - blocks[current_idx]["bbox"][3]
            if dist < max_distance:
                return next_block["text"]
        return None