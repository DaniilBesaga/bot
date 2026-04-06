from app.services.embeddings.embedding_builder import EmbeddingBuilder
from app.services.embeddings.embedding_service import EmbeddingService
from db.session import SessionLocal

# пример: sentence-transformers
from sentence_transformers import SentenceTransformer


def main():
    model = SentenceTransformer("intfloat/multilingual-e5-base")
    embedding_service = EmbeddingService(model)

    with SessionLocal() as session:
        EmbeddingBuilder.generate_embeddings_for_all_chunks(
            session=session,
            embedding_service=embedding_service,
            model_name="intfloat/multilingual-e5-base",
            batch_size=32,
        )

    print("Embeddings indexed")


if __name__ == "__main__":
    main()