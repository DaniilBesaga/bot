from sqlalchemy.orm import Session

from app.db.models import ChunkEmbedding


class EmbeddingRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, embeddings: list[ChunkEmbedding]) -> list[ChunkEmbedding]:
        if not embeddings:
            return []

        self.db.add_all(embeddings)
        self.db.commit()
        return embeddings