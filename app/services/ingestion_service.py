import os
from app.services.process_document import process_document


class IngestionService:
    def __init__(self, db):
        self.db = db
        self.process_document_service = process_document.ProcessDocumentService(db)

    async def ingest_file(self, file_path: str):
        result = await self.process_document_service.process_document(file_path=file_path)
        return {
            "file_path": file_path,
            "result": result
        }