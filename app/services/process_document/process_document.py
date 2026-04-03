
from app.dataclasses.block import Block
from app.services.process_document.helpers.pdf_loader import PdfLoader
from app.services.process_document.pipeline import Pipeline
from app.services.stats.pipeline import build_block_statistics_and_scores

import os
import uuid
class ProcessDocumentService:
    def __init__(self, db):
        self.db = db
        self.pdf_loader = PdfLoader()

    def _insert_blocks_to_db(self, blocks: list[dict]):
        """Efficiently maps block dictionaries to DB models and bulk inserts."""
        if not blocks:
            return

        db_blocks = []
        for b in blocks:
            db_blocks.append(
                Block(
                    block_id=b.get("block_id"),
                    doc_id=b.get("doc_id"),
                    page_number=b.get("page_number"),
                    position_index=b.get("position_index"),
                    kind=b.get("kind"),
                    role=b.get("role"),
                    bbox=b.get("bbox"),
                    raw_text=b.get("raw_text", ""),
                    normalized_text=b.get("normalized_text", ""),
                    fingerprint_text=b.get("fingerprint_text", "")
                )
            )
        
        # Bulk save for better performance on large documents
        self.db.bulk_save_objects(db_blocks)
        self.db.commit()


    def process_document(self, file_path: str) -> dict:
        # --- Generate the unique doc_id ---
        filename = os.path.basename(file_path)
        name_only = os.path.splitext(filename)[0].replace(".", "_").replace(" ", "_")
        generated_doc_id = f"{name_only}_{uuid.uuid4().hex[:8]}"

        file = self.pdf_loader.open_pdf(file_path)
        all_blocks = []

        # Use the generated_doc_id here instead of the full file_path
        for i, page in self.pdf_loader.iter_pages(file):
            page_blocks = Pipeline.process_page(page, i, generated_doc_id)
            all_blocks.extend(page_blocks)

        # Grouping blocks by doc_id
        documents_data = {}
        for block in all_blocks:
            doc_id = block["doc_id"]
            if doc_id not in documents_data:
                documents_data[doc_id] = {
                    "file_path": file_path,
                    "doc_id": doc_id,
                    "total_pages": getattr(file, 'page_count', 0), 
                    "blocks": []            
                }
            documents_data[doc_id]["blocks"].append(block)

        # 1. build_block_statistics_and_scores expects a list[dict]
        docs_list = list(documents_data.values())
        
        # 2. Capture the returned enriched list of blocks
        enriched_blocks = build_block_statistics_and_scores(docs_list)

        # 3. Insert into DB
        self._insert_blocks_to_db(enriched_blocks)

        return documents_data


