from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    ChunkEmbedding,
    DocumentChunk,
    RerankerExample,
)


class ChunkRepository:
    def __init__(self, db: Session):
        self.db = db

    def search_similar(self, query_embedding: list[float], limit: int = 5) -> list[dict[str, Any]]:
        """
        Поиск похожих чанков через pgvector.

        Возвращает данные из текущей схемы:
        - document_chunks.id
        - document_chunks.document_id
        - document_chunks.chunk_index
        - document_chunks.chunk_type
        - document_chunks.chunk_text
        - document_chunks.page_from
        - document_chunks.page_to
        - similarity
        """
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        sql = text("""
            SELECT
                c.id,
                c.document_id,
                c.section_id,
                c.chunk_index,
                c.chunk_type,
                c.chunk_text,
                c.chunk_markdown,
                c.page_from,
                c.page_to,
                c.token_count,
                c.heading_path,
                c.metadata_json,
                1 - (ce.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM document_chunks c
            JOIN chunk_embeddings ce
                ON c.id = ce.chunk_id
            ORDER BY ce.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)

        result = self.db.execute(
            sql,
            {
                "embedding": embedding_str,
                "limit": limit,
            },
        )

        return [dict(row._mapping) for row in result]
    
    def search_similar_contact_chunks(
        self,
        query_embedding: list[float],
        limit: int = 3,
        document_id: uuid.UUID | None = None,
    ) -> list[dict[str, Any]]:
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        if document_id is not None:
            sql = text("""
                SELECT
                    c.id,
                    c.document_id,
                    c.section_id,
                    c.chunk_index,
                    c.chunk_type,
                    c.chunk_text,
                    c.chunk_markdown,
                    c.page_from,
                    c.page_to,
                    c.heading_path,
                    c.metadata_json,
                    1 - (ce.embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM document_chunks c
                JOIN chunk_embeddings ce
                    ON c.id = ce.chunk_id
                WHERE c.chunk_type = 'contact'
                  AND c.document_id = :document_id
                ORDER BY ce.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """)
            params = {
                "embedding": embedding_str,
                "document_id": document_id,
                "limit": limit,
            }
        else:
            sql = text("""
                SELECT
                    c.id,
                    c.document_id,
                    c.section_id,
                    c.chunk_index,
                    c.chunk_type,
                    c.chunk_text,
                    c.chunk_markdown,
                    c.page_from,
                    c.page_to,
                    c.heading_path,
                    c.metadata_json,
                    1 - (ce.embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM document_chunks c
                JOIN chunk_embeddings ce
                    ON c.id = ce.chunk_id
                WHERE c.chunk_type = 'contact'
                ORDER BY ce.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """)
            params = {
                "embedding": embedding_str,
                "limit": limit,
            }

        result = self.db.execute(sql, params)
        return [dict(row._mapping) for row in result]
    
    def get_sections_for_document(self, document_id: uuid.UUID) -> list[dict[str, Any]]:
        sql = text("""
            SELECT
                id,
                document_id,
                section_type,
                title,
                heading_level,
                content_text,
                content_markdown,
                page_number,
                order_index,
                heading_path,
                metadata_json
            FROM document_sections
            WHERE document_id = :document_id
            ORDER BY order_index ASC
        """)

        result = self.db.execute(sql, {"document_id": document_id})
        return [dict(row._mapping) for row in result]


    def get_chunks(self) -> list[DocumentChunk]:
        """
        Возвращает все чанки как ORM-объекты.
        """
        stmt = (
            select(DocumentChunk)
            .options(joinedload(DocumentChunk.embedding))
            .order_by(DocumentChunk.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_chunks_as_dicts(self) -> list[dict[str, Any]]:
        """
        Если нужны именно словари, а не ORM-объекты.
        """
        stmt = select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.section_id,
            DocumentChunk.chunk_index,
            DocumentChunk.chunk_type,
            DocumentChunk.chunk_text,
            DocumentChunk.chunk_markdown,
            DocumentChunk.page_from,
            DocumentChunk.translated_text_ro,
            DocumentChunk.is_translated_to_ro,
            DocumentChunk.page_to,
            DocumentChunk.token_count,
            DocumentChunk.heading_path,
            DocumentChunk.metadata_json,
            DocumentChunk.created_at,
        ).order_by(DocumentChunk.created_at.asc())

        result = self.db.execute(stmt)
        return [dict(row._mapping) for row in result]

    def get_questions(self) -> list[RerankerExample]:
        """
        Возвращает все примеры для реранкера как ORM-объекты.
        """
        stmt = (
            select(RerankerExample)
            .options(joinedload(RerankerExample.chunk))
            .order_by(RerankerExample.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def get_questions_as_dicts(self) -> list[dict[str, Any]]:
        """
        Возвращает все примеры реранкера в виде словарей.
        """
        stmt = select(
            RerankerExample.id,
            RerankerExample.question,
            RerankerExample.chunk_id,
            RerankerExample.chunk_text_snapshot,
            RerankerExample.label,
            RerankerExample.split,
            RerankerExample.source,
            RerankerExample.created_at,
        ).order_by(RerankerExample.created_at.desc())

        result = self.db.execute(stmt)
        return [dict(row._mapping) for row in result]

    def create_question(
        self,
        question: str,
        chunk_text_snapshot: str,
        chunk_id: uuid.UUID | None,
        label: bool,
        split: str,
        source: str | None = None,
    ) -> RerankerExample:
        """
        Создает один пример для обучения реранкера.
        """
        reranker_ex = RerankerExample(
            question=question,
            chunk_id=chunk_id,
            chunk_text_snapshot=chunk_text_snapshot,
            label=label,
            split=split,
            source=source,
        )

        try:
            self.db.add(reranker_ex)
            self.db.flush()
            return reranker_ex
        except Exception:
            self.db.rollback()
            raise

    def create_questions_bulk(
        self,
        examples: list[dict[str, Any]],
    ) -> list[RerankerExample]:
        """
        Массовое создание примеров.

        examples format:
        [
            {
                "question": "...",
                "chunk_text_snapshot": "...",
                "chunk_id": uuid.UUID(...) or None,
                "label": True,
                "split": "train",
                "source": "synthetic",
            }
        ]
        """
        entities: list[RerankerExample] = []

        try:
            for item in examples:
                entity = RerankerExample(
                    question=item["question"],
                    chunk_text_snapshot=item["chunk_text_snapshot"],
                    chunk_id=item.get("chunk_id"),
                    label=item["label"],
                    split=item["split"],
                    source=item.get("source"),
                )
                entities.append(entity)

            self.db.add_all(entities)
            self.db.flush()
            return entities
        except Exception:
            self.db.rollback()
            raise

    def get_chunk_by_id(self, chunk_id: uuid.UUID) -> DocumentChunk | None:
        stmt = (
            select(DocumentChunk)
            .options(joinedload(DocumentChunk.embedding))
            .where(DocumentChunk.id == chunk_id)
        )
        return self.db.scalar(stmt)

    def get_chunks_without_embeddings(self, limit: int | None = None) -> list[DocumentChunk]:
        """
        Получить чанки, для которых еще не сохранен embedding.
        """
        stmt = (
            select(DocumentChunk)
            .outerjoin(ChunkEmbedding, DocumentChunk.id == ChunkEmbedding.chunk_id)
            .where(ChunkEmbedding.chunk_id.is_(None))
            .order_by(DocumentChunk.created_at.asc())
        )

        if limit is not None:
            stmt = stmt.limit(limit)

        return list(self.db.scalars(stmt).all())
    
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
    
    def get_chunks_without_ro_translation(self, limit: int | None = None) -> list[DocumentChunk]:
        query = self.db.query(DocumentChunk).filter(
            (DocumentChunk.translated_text_ro.is_(None)) |
            (DocumentChunk.translation_status.in_(["pending", "failed"]))
        )
        if limit:
            query = query.limit(limit)
        return query.all()

    def update_translation_fields(
        self,
        chunk: DocumentChunk,
        *,
        original_language: str | None,
        translated_text_ro: str | None,
        is_translated_to_ro: bool,
        translation_status: str,
        translation_model: str | None = None,
    ) -> DocumentChunk:
        chunk.original_language = original_language
        chunk.translated_text_ro = translated_text_ro
        chunk.is_translated_to_ro = is_translated_to_ro
        chunk.translation_status = translation_status
        chunk.translation_model = translation_model
        self.db.add(chunk)
        self.db.flush()
        return chunk
    
    def create_question(
        self,
        question: str,
        chunk_id: uuid.UUID,
        chunk_text_snapshot: str,
        label: bool,
        split: str,
        source: str | None = None,
    ):
        entity = RerankerExample(
            question=question,
            chunk_id=chunk_id,
            chunk_text_snapshot=chunk_text_snapshot,
            label=label,
            split=split,
            source=source,
        )
        self.db.add(entity)
        self.db.flush()
        return entity
    
    def update_questions_split(self, example_ids: list[uuid.UUID], split: str) -> None:
        if not example_ids:
            return

        (
            self.db.query(RerankerExample)
            .filter(RerankerExample.id.in_(example_ids))
            .update(
                {"split": split},
                synchronize_session=False,
            )
        )