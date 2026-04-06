import os
from app.services.extraction.factory import ExtractorFactory
from app.services.chunking.cleaners import clean_text
from app.services.chunking.chunking import ParagraphChunker
from app.services.embeddings.embedding_service import EmbeddingService
from app.db.repositories import ChunkRepository, ChunkRepository
from app.services.process_document import process_document


class IngestionService:
    def __init__(self, db):
        self.db = db
        self.chunker = ParagraphChunker()
        self.embedding_service = EmbeddingService()
        self.document_repo = ChunkRepository(db)
        self.chunk_repo = ChunkRepository(db)
        self.process_document_service = process_document.ProcessDocumentService(db)

    def ingest_file(self, file_path: str):
        # extractor = ExtractorFactory.get_extractor(file_path)
        # extracted = extractor.extract(file_path)

        # raw_text = extracted["text"]
        # cleaned_text = clean_text(raw_text)

        # if not cleaned_text:
        #     return None
        
        # doc_type = os.path.splitext(file_path)[1].replace(".", "").lower()
        # document = self.document_repo.create_document(
        #     file_name=os.path.basename(file_path),
        #     doc_type=doc_type,
        #     title=os.path.basename(file_path),
        #     language=None
        # )

        # chunks = self.chunker.chunk(cleaned_text)

        # for chunk in chunks:
        #     embedding = self.embedding_service.embed_text(chunk["text"])

        #     self.chunk_repo.create_chunk(
        #         document_id=document.id,
        #         chunk_index=chunk["chunk_index"],
        #         text_value=chunk["text"],
        #         embedding=embedding,
        #         token_count=None
        #     )

        # self.db.commit()
            
        # return {
        #     "document_id": str(document.id),
        #     "file_name": document.file_name,
        #     "chunks": len(chunks),
        # }
        self.process_document_service.process_document(file_path=file_path)
        return {"status": "ok"}