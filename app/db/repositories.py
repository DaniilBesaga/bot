from sqlalchemy import text, select
from sqlalchemy.orm import Session
from app.db.models import Chunk, ChunkEmbedding, RerankerExample, Document

class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        raw_text: str,
        clean_text: str | None = None,
        start_page: int | None = None,
        end_page: int | None = None,
        embedding_vector: list[float] | None = None,
        embedding_model: str = "default-model",
    ) -> Chunk:
        # 1. Создаем основной объект чанка
        chunk = Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            raw_text=raw_text,
            clean_text=clean_text,
            start_page=start_page,
            end_page=end_page,
            # Добавьте остальные поля (scores, block_ids), если они приходят из парсера
        )
        
        self.db.add(chunk)
        self.db.flush()  # Получаем доступ к chunk.id, если нужно

        # 2. Если передан вектор, создаем запись в таблицу эмбеддингов
        if embedding_vector:
            embedding_obj = ChunkEmbedding(
                chunk_id=chunk_id,  # Используем строковый chunk_id как в модели
                doc_id=doc_id,
                embedding_model=embedding_model,
                embedding_dim=len(embedding_vector),
                embedding=embedding_vector
            )
            self.db.add(embedding_obj)
        
        return chunk

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