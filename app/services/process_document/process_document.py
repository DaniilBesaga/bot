
from app.services.extraction.factory import ExtractorFactory


class ProcessDocumentService:
    def __init__(self, db):
        self.extractor = ExtractorFactory()
        self.db = db

    def process_document(self, file_path: str, doc_id: str):
        