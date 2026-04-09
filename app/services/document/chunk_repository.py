from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import DocumentChunk

class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    