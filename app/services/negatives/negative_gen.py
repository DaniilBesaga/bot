import os
from app.services.embeddings.embedding_service import EmbeddingService
from app.db.repositories import DocumentRepository, ChunkRepository
from app.services.retrieval.vector_search import VectorSearchService

class NegativeGeneration:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.document_repo = DocumentRepository()
        self.chunk_repo = ChunkRepository()
        self.vector_search = VectorSearchService()

    def generate_negative_chunks(self, chunk, top_n=3):
        question_embedding = self.embedding_service.embed_text(chunk["question"])

        best_chunks = self.vector_search.search(question_embedding, top_n)

        negatives = best_chunks[1:]

        for negative in negatives:
            self.chunk_repo.create_questions(question=negative["text"], 
                                             chunk_id=negative["id"], 
                                             label=False, 
                                             chunk_text_snapshot=negative["text"],
                                             split='train', 
                                             source="generated_negative")
        try:
            self.db.commit() 
        except Exception as e:
            self.db.rollback()
            print(f"Ошибка при коммите: {e}")
            raise