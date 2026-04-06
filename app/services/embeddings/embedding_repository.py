from sqlalchemy.orm import Session

from app.db.models import ChunkEmbedding



class EmbeddingRepository:
    @staticmethod
    def upsert_chunk_embedding(
        session: Session,
        chunk_id: str,
        doc_id: str,
        embedding_model: str,
        embedding: list[float],
    ) -> None:
        row = ChunkEmbedding(
            chunk_id=chunk_id,
            doc_id=doc_id,
            embedding_model=embedding_model,
            embedding_dim=len(embedding),
            embedding=embedding,
        )
        session.merge(row)

    @staticmethod
    def commit(session: Session) -> None:
        session.commit()