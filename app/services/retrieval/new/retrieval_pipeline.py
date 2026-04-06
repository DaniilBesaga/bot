from sqlalchemy.orm import Session

from app.services.embeddings.embedding_service import EmbeddingService
from app.services.retrieval.new.query_processing import QueryProcessing
from app.services.retrieval.new.rerank_prep import RerankPrep
from app.services.retrieval.vector_search import VectorSearchService


class RetrievalPipeline:
    def __init__(self, db):
        self.vector_search = VectorSearchService(db)
        self.query_processing = QueryProcessing()

    @classmethod
    def retrieve(
        cls,
        session: Session,
        embedding_service: EmbeddingService,
        query: str,
        top_k: int = 8,
    ) -> list[dict]:
        normalized_query = cls.query_processing.normalize_query(query)
        query_contact_intent = cls.query_processing.estimate_contact_intent(normalized_query)

        query_vector = embedding_service.embed_texts([normalized_query])[0]

        candidates = cls.vector_search.search(
            session=session,
            query_vector=query_vector,
            top_k=top_k * 3,
        )

        reranked = RerankPrep.rerank_candidates(
            candidates=candidates,
            query_contact_intent=query_contact_intent,
        )

        return reranked[:top_k]
