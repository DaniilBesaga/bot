from app.core.config import settings
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.retrieval.vector_search import VectorSearchService
from app.services.retrieval.prompt_builder import build_prompt, build_prompt_question
from app.services.llm.llm_service import LlmService
from app.services.retrieval.rerank_inference import MyRerankerService


class ChatService:
    def __init__(self, db):
        self.llm_service = LlmService()
        self.embedding_service = EmbeddingService()
        self.vector_search = VectorSearchService(db)
        self.reranker = MyRerankerService(model_dir="models/reranker")

    def ask(self, question: str) -> dict:
        question_embedding = self.embedding_service.embed_text(question)
        
        candidates = self.vector_search.search(question_embedding, limit=30)

        best_chunks = self.reranker.rerank(question, candidates, top_n=settings.TOP_K)

        prompt = build_prompt(question, best_chunks)

        answer = self.llm_service.generate_answer(prompt)

        return { "answer": answer,
                "sources": [
                    {
                        "file_name": chunk["file_name"],
                        "chunk_index": chunk["chunk_index"],
                        "vector_similarity": float(chunk.get("similarity", 0)),
                        "rerank_score": float(chunk.get("rerank_score", 0))
                    }
                    for chunk in best_chunks
                ]    
            }
        
    def ask_for_questions(self) -> dict:
        chunks = self.vector_search.get_chunks()

        prompt = build_prompt_question(chunks)

        answer = [self.llm_service.generate_answer(prompt) for chunk in chunks]

        return {
            "question": answer,
            "sources": [
                {
                    "file_name": chunk["file_name"],
                    "chunk_index": chunk["chunk_index"],
                    "vector_similarity": float(chunk.get("similarity", 0)),
                    "rerank_score": float(chunk.get("rerank_score", 0))
                }
                for chunk in chunks
            ]
        }