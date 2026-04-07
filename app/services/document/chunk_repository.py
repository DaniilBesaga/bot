from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import DocumentChunk

class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
        if not chunks:
            return []

        self.db.add_all(chunks)
        self.db.commit()

        for chunk in chunks:
            self.db.refresh(chunk)

        return chunks

    def get_document_chunks(self, document_id):
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        return list(self.db.scalars(stmt))