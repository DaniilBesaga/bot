
from app.services.process_document.helpers.pdf_loader import PdfLoader
from app.services.process_document.pipeline import Pipeline
from app.services.stats.pipeline import build_block_statistics_and_scores

class ProcessDocumentService:
    def __init__(self, db):
        self.db = db
        self.pdf_loader = PdfLoader()

    def process_document(self, file_path: str) -> dict:
        # Предположим, pdf_loader.open_pdf возвращает объект с document_id
        file = self.pdf_loader.open_pdf(file_path)

        all_blocks = []

        for i, page in self.pdf_loader.iter_pages(file):
            # Pipeline возвращает список блоков для конкретной страницы
            page_blocks = Pipeline.process_page(page, i, file_path)
            all_blocks.extend(page_blocks)

        # Формируем структуру документов
        documents_data = {}
        for block in all_blocks:
            doc_id = block["doc_id"]
            if doc_id not in documents_data:
                documents_data[doc_id] = {
                    "file_path": file_path,
                    "total_pages": file.page_count, # если loader это отдает
                    "blocks": []            # ВОТ ОНО — поле blocks
            }
            documents_data[doc_id]["blocks"].append(block)

        ##################################

        build_block_statistics_and_scores(documents_data)


