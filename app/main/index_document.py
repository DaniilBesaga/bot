from app.services.chunking.chunk_pipeline import ChunkPipeline
from db.session import SessionLocal

def main(doc_id: str):
    with SessionLocal() as session:
        chunks = ChunkPipeline.build_and_save_chunks_for_document(session, doc_id=doc_id, max_words=220)
        print(f"Saved {len(chunks)} chunks for doc_id={doc_id}")


if __name__ == "__main__":
    main("doc_1")