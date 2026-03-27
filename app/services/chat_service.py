from app.core.config import settings
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.retrieval.vector_search import VectorSearchService
from app.services.retrieval.prompt_builder import build_prompt
from app.services.llm.llm_service import LlmService


class ChatService:
    def __init__(self, db):
        self.llm_service = LlmService()
        self.embedding_service = EmbeddingService()
        self.vector_search = VectorSearchService(db)

    def ask(self, question: str) -> dict:
        question_embedding = self.embedding_service.embed_text(question)
        chunks = self.vector_search.search(question_embedding, limit=settings.CHUNK_LIMIT)

        prompt = build_prompt(question, chunks)

        answer = self.llm_service.generate_answer(prompt)

        return { "answer": answer,
                "sources": [
                    {
                        "file_name": chunk["file_name"],
                        "chunk_index": chunk["chunk_index"],
                        "similarity": float(chunk["similarity"])
                    }
                    for chunk in chunks
                ]    
            }
        