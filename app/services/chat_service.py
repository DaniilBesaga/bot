import random
from typing import Any
import uuid

from transformers import AutoTokenizer

from app.core.config import settings
from app.db.repositories import ChunkRepository
from app.services.contact.is_contact_query import is_contact_query
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.language.chunk_trans_service import ChunkTranslationService
from app.services.language.deepl import DeepLTranslationService
from app.services.language.translate_pipeline import TranslatePipeline
from app.services.retrieval.json_parser import is_chunk_good_for_qa
from app.services.retrieval.prompt_builder import build_prompt, build_prompt_question, build_prompt_validate
from app.services.retrieval.vector_search import VectorSearchService
from app.services.llm.llm_service import LlmService
from app.services.retrieval.rerank_inference import MyRerankerService
from app.training.train_reranker import SmartCollate


class ChatService:
    def __init__(self, db):
        self.llm_service = LlmService()
        self.translation_service = DeepLTranslationService()
        self.embedding_service = EmbeddingService()
        self.vector_search = VectorSearchService(db)
        # self.reranker = MyRerankerService(model_dir="models/reranker")
        self.chunk_repo = ChunkRepository(db)
        self.db = db
        #self.smart_collate = SmartCollate(tokenizer=AutoTokenizer.from_pretrained("distilbert-base-uncased"))
        self.smart_collate = SmartCollate(db)

    def ask(self, question: str) -> dict:
        question_embedding = self.embedding_service.embed_query(question)

        candidates
        
        if is_contact_query(question):
            candidates = self.vector_search.search_contact_chunks(question_embedding, limit=3)
        else:
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


    def ask_for_questions(self) -> dict[str, Any]:
        chunks = self.chunk_repo.get_chunks_as_dicts()

        if not chunks:
            return {
                "questions": [],
                "groups_created": 0,
                "examples_created": 0,
            }

        groups: list[dict[str, Any]] = []
        seen_negative_pairs: set[tuple[str, uuid.UUID]] = set()

        for chunk in chunks:
            text = ((chunk.get("is_translated_to_ro") and chunk.get("translated_text_ro")) or chunk.get("chunk_text") or "").strip()
            if not is_chunk_good_for_qa(text):
                continue

            # 1. Генерация question + answer
            prompt = build_prompt_question([chunk])
            qa_result = self.llm_service.generate_json(prompt)

            if not qa_result:
                continue

            if qa_result.get("skip") is True:
                continue

            question = str(qa_result.get("question") or "").strip()
            answer = str(qa_result.get("answer") or "").strip()

            if not question or not answer:
                continue

            # 3. LLM validation
            validate_prompt = build_prompt_validate(
                question=question,
                answer=answer,
                chunk_text=text,
            )
            validation_result = self.llm_service.generate_json(validate_prompt)

            if not validation_result:
                continue

            if validation_result.get("valid") is not True:
                continue

            if validation_result.get("grounded") is not True:
                continue

            if validation_result.get("answer_supported") is not True:
                continue

            group_examples: list[dict[str, Any]] = []

            # positive
            group_examples.append({
                "question": question,
                "chunk_id": chunk["id"],
                "chunk_text_snapshot": text,
                "label": True,
                "split": "",
                "source": "generated_positive",
            })

            # 4. negatives строим только после валидного positive
            question_embedding = self.embedding_service.embed_query(question)
            top_chunks = self.vector_search.search(question_embedding, limit=5)

            for found_chunk in top_chunks:
                if found_chunk["id"] == chunk["id"]:
                    continue

                pair_key = (question, found_chunk["id"])
                if pair_key in seen_negative_pairs:
                    continue

                seen_negative_pairs.add(pair_key)

                group_examples.append({
                    "question": question,
                    "chunk_id": found_chunk["id"],
                    "chunk_text_snapshot": found_chunk["chunk_text"],
                    "label": False,
                    "split": "",
                    "source": "generated_negative",
                })

            # группа нужна только если есть хотя бы 1 negative
            if len(group_examples) < 2:
                continue

            groups.append({
                "question": question,
                "answer": answer,
                "source_chunk_id": chunk["id"],
                "examples": group_examples,
            })

        if not groups:
            return {
                "questions": [],
                "groups_created": 0,
                "examples_created": 0,
            }

        random.shuffle(groups)

        total_groups = len(groups)
        train_count = int(total_groups * 0.8)
        val_count = int(total_groups * 0.1)

        train_groups = groups[:train_count]
        val_groups = groups[train_count:train_count + val_count]
        test_groups = groups[train_count + val_count:]

        for group in train_groups:
            for ex in group["examples"]:
                ex["split"] = "train"

        for group in val_groups:
            for ex in group["examples"]:
                ex["split"] = "val"

        for group in test_groups:
            for ex in group["examples"]:
                ex["split"] = "test"

        all_examples: list[dict[str, Any]] = []
        for group in groups:
            all_examples.extend(group["examples"])

        if all_examples:
            self.chunk_repo.create_questions_bulk(all_examples)

        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Ошибка при коммите examples: {e}")
            raise

        return {
            "questions": [group["question"] for group in groups],
            "groups_created": len(groups),
            "examples_created": len(all_examples),
            "train_groups": len(train_groups),
            "val_groups": len(val_groups),
            "test_groups": len(test_groups),
        }
    
    def train_model(self):
        self.smart_collate.train()

    def ask_for_translate(self):
        pipeline = TranslatePipeline(self.db,
                                    chunk_repo=self.chunk_repo,
                                    translation_service=self.translation_service)
        return pipeline.execute()
