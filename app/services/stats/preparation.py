from app.services.stats.normalization import extract_local_features, normalize_for_fingerprint, normalize_text

class BlocksPreparation:
    @staticmethod
    def prepare_blocks(all_documents: list[dict]) -> list[dict]:
        prepared = []

        for doc in all_documents:

            for block in doc.get("blocks", []):
                if "bbox" in block and not isinstance(block["bbox"], (list, tuple)):
                    block["bbox"] = list(block["bbox"])
                # Теперь всё лежит в одном ключе "text"!
                raw_text = block.get("text", "").strip()

                doc_id_from_parent = doc.get("doc_id")
                if doc_id_from_parent:
                    block["doc_id"] = doc_id_from_parent
                elif not block.get("doc_id"):
                    block["doc_id"] = "unknown_doc"

                block["raw_text"] = raw_text
                block["local_features"] = extract_local_features(block)
                
                if raw_text:
                    block["normalized_text"] = normalize_text(raw_text)
                    block["fingerprint_text"] = normalize_for_fingerprint(raw_text)
                else:
                    block["normalized_text"] = ""
                    block["fingerprint_text"] = ""

                prepared.append(block)

        return prepared