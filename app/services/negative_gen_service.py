import os
from app.services.embeddings.embedding_service import EmbeddingService
from app.db.repositories import DocumentRepository, ChunkRepository
from app.services.retrieval.vector_search import VectorSearchService

class NegativeGenerationService:
    def __init__(self, db):
        self.embedding_service = EmbeddingService()
        self.document_repo = DocumentRepository()
        self.chunk_repo = ChunkRepository()
        self.vector_search = VectorSearchService()

    def generate_negative_chunks(self):

        chunks = self.chunk_repo.get_chunks()

        for chunk in chunks:
            self.generate_negative_chunks(chunk)
            
        try:
            self.db.commit() 
        except Exception as e:
            self.db.rollback()
            print(f"Ошибка при коммите: {e}")
            raise