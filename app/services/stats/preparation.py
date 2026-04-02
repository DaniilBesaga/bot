from app.services.stats.normalization import normalize_for_fingerprint, normalize_text

class BlocksPreparation:
    @staticmethod
    def prepare_blocks(all_documents: list[dict]) -> list[dict]:
        prepared = []

        for doc in all_documents:
            doc_id = doc.get("doc_id", "unknown_doc")

            for block in doc.get("blocks", []):
                raw_text = ""
                kind = block.get("kind")

                # --- Элегантный сбор текста по типу блока ---
                if kind == "text_block":
                    # У текстового блока текст уже собран в make_text_block
                    raw_text = block.get("text", "")

                elif kind == "image_block":
                    # Если вы делали OCR для картинок, текст будет лежать здесь. 
                    # Если нет - просто вернется пустая строка.
                    raw_text = block.get("text", "")

                elif kind == "table_block":
                    # Таблицу можно превратить в строку (например, склеив ячейки)
                    # Зависит от того, как вы храните table_obj
                    raw_text = block.get("text_content", "") 

                # Очищаем от лишних пробелов по краям
                raw_text = raw_text.strip()

                # --- Обогащение словаря ---
                # Сохраняем все оригинальные метаданные (bbox, kind, role, position_index) 
                # и просто добавляем новые ключи для статистики
                block["doc_id"] = doc_id
                block["raw_text"] = raw_text
                
                if raw_text:
                    block["normalized_text"] = normalize_text(raw_text)
                    block["fingerprint_text"] = normalize_for_fingerprint(raw_text)
                else:
                    block["normalized_text"] = ""
                    block["fingerprint_text"] = ""

                prepared.append(block)

        return prepared