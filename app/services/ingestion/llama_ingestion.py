import os

from app.db.models import ChunkEmbedding, DocumentChunk, DocumentSection
from app.services.document.chunk_repository import ChunkRepository
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

            self.section_repository.bulk_create(section_entities)

            chunks_data = self.chunking_service.build_chunks(normalized)

            chunk_entities = []
            for ch in chunks_data:
                chunk_entities.append(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=ch["chunk_index"],
                        chunk_type=ch["chunk_type"],
                        chunk_text=ch["chunk_text"],
                        chunk_markdown=ch["chunk_markdown"],
                        page_from=ch["page_from"],
                        page_to=ch["page_to"],
                        heading_path=ch["heading_path"],
                        metadata_json=ch["metadata_json"],
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
            }

        except Exception as e:
            self.document_repository.update(
                document,
                status="failed",
                error_message=str(e),
            )
            return {
                "document_id": str(document.id),
                "file_name": file_name,
                "status": "failed",
                "error": str(e),
            }