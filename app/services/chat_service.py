from transformers import AutoTokenizer

from app.core.config import settings
from app.db.repositories import ChunkRepository
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.retrieval.vector_search import VectorSearchService
from app.services.retrieval.prompt_builder import build_prompt, build_prompt_question
from app.services.llm.llm_service import LlmService
from app.services.retrieval.rerank_inference import MyRerankerService
from app.training.train_reranker import SmartCollate


class ChatService:
    def __init__(self, db):
        self.llm_service = LlmService()
        self.embedding_service = EmbeddingService()
        self.vector_search = VectorSearchService(db)
        self.reranker = MyRerankerService(model_dir="models/reranker")
        self.chunk_repo = ChunkRepository(db)
        self.db = db
        #self.smart_collate = SmartCollate(tokenizer=AutoTokenizer.from_pretrained("distilbert-base-uncased"))
        self.smart_collate = SmartCollate()

    def ask(self, question: str) -> dict:
        question_embedding = self.embedding_service.embed_query(question)
        
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
        chunks = self.chunk_repo.get_chunks_as_dicts()

        responses = []
        generated_examples = []

        # 1. Генерируем positive-вопрос для каждого chunk
        for chunk in chunks:
            prompt = build_prompt_question([chunk])
            question = self.llm_service.generate_answer(prompt)

            responses.append(question)

            self.chunk_repo.create_question(
                question=question,
                chunk_id=chunk["id"],
                label=True,
                chunk_text_snapshot=chunk["chunk_text"],
                split="train",
                source="generated_positive",
            )

            generated_examples.append({
                "question": question,
                "chunk_id": chunk["id"],
                "chunk_text_snapshot": chunk["chunk_text"],
            })

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Ошибка при коммите positive examples: {e}")
            raise

        # 2. Для каждого positive question ищем похожие chunks
        negative_examples = []

        for example in generated_examples:
            question_embedding = self.embedding_service.embed_query(example["question"])

            top_chunks = self.vector_search.search(question_embedding, limit=3)

            for found_chunk in top_chunks:
                # пропускаем исходный positive chunk
                if found_chunk["id"] == example["chunk_id"]:
                    continue

                negative_examples.append({
                    "question": example["question"],
                    "chunk_id": found_chunk["id"],
                    "chunk_text_snapshot": found_chunk["chunk_text"],
                    "label": False,
                    "split": "train",
                    "source": "generated_negative",
                })

        if negative_examples:
            self.chunk_repo.create_questions_bulk(negative_examples)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Ошибка при коммите negative examples: {e}")
            raise

        return {"questions": responses}
    
    def train_model(self):
        self.smart_collate.train()

