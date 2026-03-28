from sqlalchemy import text
import uuid
from app.db.models import Document, DocumentChunk

class DocumentRepository:
    def __init__(self, db):
        self.db = db
    
    def create_document(self, file_name: str, doc_type: str, title: str | None, language: str | None) -> Document:
        document = Document(file_name=file_name, doc_type=doc_type, title=title, language=language)
        self.db.add(document)
        self.db.flush()
        return document
    
class ChunkRepository:
    def __init__(self, db):
        self.db = db
    def create_chunk(
        self,
        document_id: uuid.UUID,
        chunk_index: int,
        text_value: str,
        token_count: int | None = None,
        page_from: int | None = None,
        page_to: int | None = None,
        embedding: list[float] | None = None,
    ):
        chunk = DocumentChunk(
            document_id=document_id,
            chunk_index=chunk_index,
            text=text_value,
            token_count=token_count,
            page_from=page_from,
            page_to=page_to,
            embedding=embedding,
        )
        self.db.add(chunk)
        return chunk
    
    def search_similar(self, query_embedding: list[float], limit: int = 5):
        sql = text("""
            SELECT 
                   dc.id,
                   dc.document_id,
                   dc.chunk_index,
                   dc.text,
                   dc.page_from,
                   dc.page_to,
                   d.file_name,
                   1 - (dc.embedding <=> CAST(:embedding AS vector)) AS similarity
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            ORDER BY dc.embedding <=> CAST(:embedding AS vector)
            LIMIT :limit
        """)

        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        result = self.db.execute(
            sql,
            {"embedding": embedding_str, "limit": limit}
        )

        return [dict(row._mapping) for row in result]