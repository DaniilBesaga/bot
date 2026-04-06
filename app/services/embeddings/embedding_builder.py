from sqlalchemy.orm import Session
from app.db.models import Chunk
from app.services.embeddings.embedding_repository import EmbeddingRepository
from app.services.embeddings.embedding_service import EmbeddingService


class EmbeddingBuilder:
    @staticmethod
    def build_embedding_input(chunk: Chunk) -> str:
        parts: list[str] = []

        if chunk.heading_text and chunk.heading_text.strip():
            parts.append(f"Title: {chunk.heading_text.strip()}")

        if chunk.clean_text and chunk.clean_text.strip():
            parts.append(f"Content:\n{chunk.clean_text.strip()}")

        return "\n\n".join(parts).strip()

    @staticmethod
    def should_embed_chunk(chunk: Chunk) -> bool:
        if not chunk.clean_text or not chunk.clean_text.strip():
            return False

        if chunk.avg_content_score < 0.15 and chunk.avg_boilerplate_score > 0.8:
            return False

        return True

    @classmethod
    def generate_embeddings_for_all_chunks(
        cls,
        session: Session,
        embedding_service: EmbeddingService,
        model_name: str,
        batch_size: int = 32,
    ) -> None:
        chunks = session.query(Chunk).all()
        to_embed = [ch for ch in chunks if cls.should_embed_chunk(ch)]

        for i in range(0, len(to_embed), batch_size):
            batch = to_embed[i:i + batch_size]
            texts = [cls.build_embedding_input(ch) for ch in batch]

            embeddings = embedding_service.embed_texts(texts)

            for chunk, vector in zip(batch, embeddings):
                EmbeddingRepository.upsert_chunk_embedding(
                    session=session,
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    embedding_model=model_name,
                    embedding=vector,
                )

            EmbeddingRepository.commit(session)