from app.db.repositories import ChunkRepository

class VectorSearchService:
    def __init__(self, db):
        self.chunk_repo = ChunkRepository(db)

    def search(self, query_embedding: list[float], limit: int = 5):
        return self.chunk_repo.search_similar(query_embedding, limit)
    
    def get_chunks(self):
        return self.chunk_repo.get_chunks()