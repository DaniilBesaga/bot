
# from app.db.models import Block
# from app.services.process_document.helpers.pdf_loader import PdfLoader
# from app.services.process_document.pipeline import Pipeline
# from app.services.stats.pipeline import build_block_statistics_and_scores

# import os
# import uuid
# class ProcessDocumentService:
#     def __init__(self, db):
#         self.db = db
#         self.pdf_loader = PdfLoader()

#     def _insert_blocks_to_db(self, blocks: list[dict]):
#         """Efficiently maps block dictionaries to DB models and bulk inserts."""
#         if not blocks:
#             return

#         db_blocks = []
#         for b in blocks:
#             db_blocks.append(
#                 Block(
#                     block_id=b.get("block_id"),
#                     doc_id=b.get("doc_id"),
#                     page_number=b.get("page_number"),
#                     position_index=b.get("position_index"),
#                     kind=b.get("kind"),
#                     role=b.get("role"),
#                     bbox=b.get("bbox"),
#                     raw_text=b.get("raw_text", ""),
#                     normalized_text=b.get("normalized_text", ""),
#                     fingerprint_text=b.get("fingerprint_text", ""),
#                     content_score=b.get("content_score", 0.0),
#                     contact_score=b.get("contact_score", 0.0),
#                     boilerplate_score=b.get("boilerplate_score", 0.0)
#                 )
#             )
        
#         # Bulk save for better performance on large documents
#         self.db.bulk_save_objects(db_blocks)
#         self.db.commit()


#     def process_document(self, file_path: str) -> dict:
#         # --- Generate the unique doc_id ---
#         filename = os.path.basename(file_path)
#         name_only = os.path.splitext(filename)[0].replace(".", "_").replace(" ", "_")
#         generated_doc_id = f"{name_only}_{uuid.uuid4().hex[:8]}"

#         file = self.pdf_loader.open_pdf(file_path)
#         all_blocks = []

#         # Use the generated_doc_id here instead of the full file_path
#         for i, page in self.pdf_loader.iter_pages(file):
#             page_blocks = Pipeline.process_page(page, i, generated_doc_id)
#             all_blocks.extend(page_blocks)

#         # Grouping blocks by doc_id
#         documents_data = {}
#         for block in all_blocks:
#             doc_id = block["doc_id"]
#             if doc_id not in documents_data:
#                 documents_data[doc_id] = {
#                     "file_path": file_path,
#                     "doc_id": doc_id,
#                     "total_pages": getattr(file, 'page_count', 0), 
#                     "blocks": []            
#                 }
#             documents_data[doc_id]["blocks"].append(block)

#         # 1. build_block_statistics_and_scores expects a list[dict]
#         docs_list = list(documents_data.values())
        
#         # 2. Capture the returned enriched list of blocks
#         enriched_blocks = build_block_statistics_and_scores(docs_list)

#         flat_blocks = []
#         for doc in enriched_blocks:
#             flat_blocks.extend(doc.get("blocks", []))

#         self._insert_blocks_to_db(flat_blocks)

#         # 3. Insert into DB
#         self._insert_blocks_to_db(enriched_blocks)

#         return documents_data


# import os
# from docling.datamodel.base_models import InputFormat
# from docling.document_converter import DocumentConverter, PdfPipelineOptions
# from docling.datamodel.pipeline_options import TesseractOcrOptions
# from docling.datamodel.base_models import PictureItem, TableItem

# from app.db.models import Block

# class ProcessDocumentService:
#     def __init__(self, db):
#         self.db = db
        
#         # --- НАСТРОЙКА OCR ---
#         # В Docker мы используем Tesseract, так как ты его установил в Dockerfile
#         pipeline_options = PdfPipelineOptions()
#         pipeline_options.do_ocr = True  # Включаем распознавание текста на картинках
#         pipeline_options.ocr_options = TesseractOcrOptions() 
        
#         # Инициализируем конвертер один раз при создании сервиса
#         self.converter = DocumentConverter(pipeline_options=pipeline_options)

#     def process_document(self, file_path: str) -> dict:
#         # Конвертируем документ
#         result = self.converter.convert(file_path)
#         doc = result.document
        
#         for item, level in doc.iterate_items():
#             # 1. Пропускаем элементы без координат (метаданные и т.д.)
#             if not item.prov:
#                 continue
                
#             location = item.prov[0]
            
#             # 2. Извлекаем текст
#             # Если это картинка, Docling попробует вытащить текст через OCR
#             try:
#                 # Используем список [item], чтобы избежать TypeError: unhashable type
#                 content = doc.export_to_markdown(item_set=[item])
#             except Exception as e:
#                 print(f"Ошибка экспорта блока {item.self_ref}: {e}")
#                 content = ""

#             # 3. Создаем объект модели
#             new_block = Block(
#                 block_id=str(item.self_ref),
#                 doc_id="your_doc_id",
#                 page_number=location.page_no,
#                 # Исправлено: используем model_dump() для Pydantic v2
#                 bbox=location.bbox.model_dump(), 
#                 role=getattr(item, 'label', 'unknown'),
#                 raw_text=content
#             )
            
#             # Логируем результат
#             if content.strip():
#                 print(f"--- Block {new_block.block_id} ({new_block.role}) ---")
#                 print(new_block.raw_text)
            
#             # 4. Сохранение в базу
#             # self.db.add(new_block)
        
#         # self.db.commit()
#         return doc

from llama_cloud import AsyncLlamaCloud

client = AsyncLlamaCloud(api_key="llx-9ZVEP7IdVyjJ6KmCmcvWLi0xUWnhhy1fnSLDBTNabiYu6E0v")
class ProcessDocumentService:
    def __init__(self, db):
        self.db = db

    async def process_document(self, file_path: str) -> dict:
        import asyncio

        print(f"\n>>> [START] Processing: {file_path}", flush=True)

        try:
            with open(file_path, "rb") as f:
                print("Sending to LlamaParse...", flush=True)
                file_obj = await client.files.create(file=f, purpose="parse")
                print(f"File uploaded. ID: {file_obj.id}", flush=True)

            print("Starting job...", flush=True)
            parse_result = await client.parsing.parse(
                file_id=file_obj.id,
                tier="agentic",
                version="latest",
                expand=["markdown_full", "text_full"],
            )

            job_id = parse_result.job.id
            print(f"Job ID: {job_id}. Waiting for completion...", flush=True)

            while True:
                result = await client.parsing.get(
                    job_id=job_id,
                    expand=["markdown_full", "text_full"],
                )

                if getattr(result, "markdown_full", None):
                    print(">>> [SUCCESS] Data received!", flush=True)
                    return {
                        "status": "ok",
                        "markdown": result.markdown_full,
                        "text": getattr(result, "text_full", None),
                    }

                if getattr(result.job, "status", "") in {"FAILED", "ERROR"}:
                    print(">>> [ERROR] Parsing failed on server", flush=True)
                    return {"status": "error", "message": "Parsing failed"}

                print("Still parsing... waiting 5 seconds", flush=True)
                await asyncio.sleep(5)

        except Exception as e:
            print(f">>> [CRITICAL ERROR]: {str(e)}", flush=True)
            return {"status": "error", "message": str(e)}
  