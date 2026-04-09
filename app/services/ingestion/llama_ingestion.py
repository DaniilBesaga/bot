import os

from app.db.models import ChunkEmbedding, DocumentChunk, DocumentSection
from app.db.repositories import ChunkRepository
from app.services.contact.contact_extractor import ContactChunkExtractor
from app.services.contact.cosine_sim import _cosine_similarity
from app.services.document.document_repository import DocumentRepository
from app.services.document.embedding_repository import EmbeddingRepository
from app.services.document.section_repository import SectionRepository
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.ingestion.llama_chunking import ChunkingService


class DocumentIngestionService:
    def __init__(
        self,
        db,
        llama_parse_client_service,
        llama_parse_normalizer,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
    ):
        self.db = db
        self.document_repository = DocumentRepository(db)
        self.section_repository = SectionRepository(db)
        self.chunk_repository = ChunkRepository(db)
        self.embedding_repository = EmbeddingRepository(db)

        self.llama_parse_client_service = llama_parse_client_service
        self.llama_parse_normalizer = llama_parse_normalizer
        self.chunking_service = chunking_service
        self.embedding_service = embedding_service

    async def ingest_file(self, file_path: str) -> dict:
        file_name = os.path.basename(file_path)

        existing = self.document_repository.get_by_file_path(file_path=file_path)
        if existing:
            return {
                "document_id": str(existing.id),
                "file_name": existing.file_name,
                "status": "already_exists",
            }

        document = self.document_repository.create(
            file_name=file_name,
            file_path=file_path,
            source_type="local_file",
            status="processing",
            parser_name="llamaparse",
        )

        try:
            parse_result = await self.llama_parse_client_service.parse_file(file_path)

            document = self.document_repository.update(
                document,
                parser_job_id=parse_result.get("job_id"),
                markdown_full=parse_result.get("markdown_full"),
                text_full=parse_result.get("text_full"),
                raw_items=parse_result.get("items"),
                page_count=len((parse_result.get("items") or {}).get("pages", [])),
                status="parsed",
            )

            normalized = self.llama_parse_normalizer.normalize(
                file_name=file_name,
                parse_result=parse_result,
            )

            section_entities = []
            for block in normalized.blocks:
                section_entities.append(
                    DocumentSection(
                        document_id=document.id,
                        section_type=block.block_type,
                        title=block.text[:300] if block.block_type == "heading" and block.text else None,
                        heading_level=block.heading_level,
                        content_text=block.text,
                        content_markdown=block.markdown,
                        page_number=block.page_number,
                        order_index=block.order_index,
                        heading_path=block.heading_path,
                        metadata_json=block.metadata,
                    )
                )

            section_entities = self.section_repository.bulk_create(section_entities)

            # 1. Обычные чанки
            chunks_data = self.chunking_service.build_chunks(normalized)

            # 2. Контактные чанки
            contact_chunks_data = self._build_contact_chunks(
                document_id=document.id,
                sections=section_entities,
                start_chunk_index=len(chunks_data),
                similarity_threshold=0.95,
                search_globally=True,
            )

            # 3. Объединяем обычные и контактные чанки
            all_chunks_data = chunks_data + contact_chunks_data
            print(contact_chunks_data)

            chunk_entities = []
            for ch in all_chunks_data:
                chunk_entities.append(
                    DocumentChunk(
                        document_id=document.id,
                        section_id=ch.get("section_id"),
                        chunk_index=ch["chunk_index"],
                        chunk_type=ch["chunk_type"],
                        chunk_text=ch["chunk_text"],
                        chunk_markdown=ch.get("chunk_markdown"),
                        page_from=ch.get("page_from"),
                        page_to=ch.get("page_to"),
                        heading_path=ch.get("heading_path"),
                        metadata_json=ch.get("metadata_json"),
                    )
                )

            chunk_entities = self.chunk_repository.bulk_create(chunk_entities)

            vectors = self.embedding_service.embed_batch(
                [chunk.chunk_text for chunk in chunk_entities]
            )

            embedding_entities = []
            for chunk, vector in zip(chunk_entities, vectors):
                embedding_entities.append(
                    ChunkEmbedding(
                        chunk_id=chunk.id,
                        model_name=self.embedding_service.model_name,
                        embedding=vector,
                    )
                )

            self.embedding_repository.bulk_create(embedding_entities)

            self.document_repository.update(document, status="indexed")

            return {
                "document_id": str(document.id),
                "file_name": file_name,
                "status": "indexed",
                "sections_count": len(section_entities),
                "chunks_count": len(chunk_entities),
                "regular_chunks_count": len(chunks_data),
                "contact_chunks_count": len(contact_chunks_data),
            }

        except Exception as e:
            self.db.rollback()
            self.document_repository.update(
                document,
                status="failed",
                error_message=str(e),
            )
            raise
        

    def _build_contact_chunks(
        self,
        document_id,
        sections: list[DocumentSection],
        start_chunk_index: int,
        similarity_threshold: float = 0.95,
        search_globally: bool = True,
    ) -> list[dict]:
        contact_chunks_data = []
        next_chunk_index = start_chunk_index

        # чтобы в рамках одного документа не плодить почти одинаковые contact blocks
        local_contact_embeddings: list[tuple[str, list[float]]] = []

        for section in sections:
            source_text = (
                section.content_text
                or section.content_markdown
                or ""
            ).strip()

            if not source_text:
                continue

            contact_blocks = ContactChunkExtractor.extract_blocks(source_text)
            if not contact_blocks:
                continue

            for block in contact_blocks:
                candidate_text = block.normalized_text

                if not candidate_text.strip():
                    continue

                candidate_embedding = self.embedding_service.embed_query(candidate_text)

                # 1. сначала локальная проверка среди уже найденных contact chunks этого же документа
                local_duplicate = False
                for _, existing_embedding in local_contact_embeddings:
                    similarity = _cosine_similarity(candidate_embedding, existing_embedding)
                    if similarity >= similarity_threshold:
                        local_duplicate = True
                        break

                if local_duplicate:
                    continue

                # 2. проверка в БД среди уже существующих contact chunks
                existing_matches = self.chunk_repository.search_similar_contact_chunks(
                    query_embedding=candidate_embedding,
                    limit=3,
                    document_id=None if search_globally else document_id,
                )

                best_match = existing_matches[0] if existing_matches else None
                best_similarity = float(best_match["similarity"]) if best_match else 0.0

                if best_match and best_similarity >= similarity_threshold:
                    continue

                contact_chunks_data.append({
                    "section_id": section.id,
                    "chunk_index": next_chunk_index,
                    "chunk_type": "contact",
                    "chunk_text": candidate_text,
                    "chunk_markdown": candidate_text,
                    "page_from": section.page_number,
                    "page_to": section.page_number,
                    "heading_path": section.heading_path,
                    "metadata_json": {
                        "source": "contact_extractor",
                        "contact_score": block.score,
                        "origin_section_id": str(section.id),
                        "origin_section_type": section.section_type,
                    },
                })

                local_contact_embeddings.append((candidate_text, candidate_embedding))
                next_chunk_index += 1

        return contact_chunks_data