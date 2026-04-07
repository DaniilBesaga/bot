from llama_cloud import AsyncLlamaCloud

from app.services.embeddings.embedding_service import EmbeddingService
from app.services.ingestion.llama_chunking import ChunkingService
from app.services.ingestion.llama_ingestion import DocumentIngestionService
from app.services.ingestion.llama_parse_client_service import LlamaParseClientService
from app.services.ingestion.llama_parse_normalizer import LlamaParseNormalizer

client = AsyncLlamaCloud(api_key="llx-9ZVEP7IdVyjJ6KmCmcvWLi0xUWnhhy1fnSLDBTNabiYu6E0v")


class ProcessDocumentService:
    def __init__(self, db):
        self.db = db
        self.document_ingestion_service = DocumentIngestionService(
            db=db,
            llama_parse_client_service=LlamaParseClientService(client=client),
            llama_parse_normalizer=LlamaParseNormalizer(),
            chunking_service=ChunkingService(max_chars=1800),
            embedding_service=EmbeddingService(model_name="all-MiniLM-L6-v2"),
    )

    async def process_document(self, file_path: str) -> dict:
        return await self.document_ingestion_service.ingest_file(file_path=file_path)
  