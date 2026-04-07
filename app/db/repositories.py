from sqlalchemy import text, select
from sqlalchemy.orm import Session

from app.db.models import RerankerExample

class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def search_similar(self, query_embedding: list[float], limit: int = 5):
        """
        Поиск с использованием pgvector. 
        Обратите внимание: теперь мы джойним таблицу chunk_embeddings.
        """
        # Преобразуем список в строку формата pgvector '[0.1, 0.2, ...]'
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
        
        sql = text("""
            SELECT 
                c.id,
                c.chunk_id,
                c.doc_id,
                c.raw_text,
                c.start_page,
                c.end_page,
                1 - (ce.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM document_chunks c
            JOIN chunk_embeddings ce ON c.chunk_id = ce.chunk_id
            ORDER BY ce.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)

        result = self.db.execute(
            sql,
            {"embedding": embedding_str, "limit": limit}
        )

        return [dict(row._mapping) for row in result]

    def get_chunks(self):
        # Используем новую таблицу document_chunks
        sql = text("SELECT * FROM document_chunks")
        result = self.db.execute(sql)
        return [dict(row._mapping) for row in result]

    def get_questions(self):
        sql = text("SELECT * FROM reranker_examples")
        result = self.db.execute(sql)
        return [dict(row._mapping) for row in result]

    def create_questions(
        self,
        question: str,
        chunk_text_snapshot: str,
        chunk_id: any, # Тип зависит от того, используете вы Integer PK или String chunk_id
        label: bool,
        split: str,
        source: str | None
    ):
        reranker_ex = RerankerExample(
            question=question,
            chunk_id=chunk_id,
            chunk_text_snapshot=chunk_text_snapshot,
            label=label,
            split=split,
            source=source
        )
        try:
            self.db.add(reranker_ex)
            self.db.flush()
            return reranker_ex
        except Exception as e:
            self.db.rollback()
            print(f"Failed to add reranker example to db: {e}")
            raise