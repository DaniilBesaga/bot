import os
from fastapi import APIRouter, Depends
import pandas as pd
from app.db.session import SessionLocal
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.ingestion_service import IngestionService
from app.services.process_document.process_document import ProcessDocumentService

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/ingest")
async def ingest(db=Depends(get_db)):
    service = IngestionService(db)
    results = []

    folders = [
        "data/raw/pdf",
        "data/raw/docx",
        "data/raw/txt"
    ]

    for folder in folders:
        if not os.path.exists(folder):
            continue
        
        for file_name in os.listdir(folder):
            file_path = os.path.join(folder, file_name)
            if os.path.isfile(file_path):
                result = await service.ingest_file(file_path)
                if result:
                    results.append(result)

    return {"message": "Ingestion completed", "results": results}

@router.get("/tojson")
def to_json(db=Depends(get_db)):
    query = """
        SELECT e.question, c.chunk_text, e.label, e.split 
        FROM reranker_examples e
        JOIN document_chunks c ON e.chunk_id = c.id
    """
    # Если ты используешь SQLAlchemy:
    df = pd.read_sql(query, "postgresql+psycopg://postgres:root@localhost:5434/bot")
    
    # Разделяем на train и val (или используй колонку e.split, если она есть)
    df_train = df[df['split'] == 'train']
    df_val = df[df['split'] == 'val']
    
    # Сохраняем в JSONL
    train_path = "dataset_train.jsonl"
    val_path = "dataset_val.jsonl"
    df_train.to_json(train_path, orient="records", lines=True, force_ascii=False)
    df_val.to_json(val_path, orient="records", lines=True, force_ascii=False)
    print(f"Готово! Выгружено {len(df_train)} строк в {train_path} и {len(df_val)} строк в {val_path}")

@router.get("/pdf")
def process_pdf(file_path: str, doc_id: str, db=Depends(get_db)):
    service = ProcessDocumentService(db)
    return service.process_document(file_path, doc_id)

# @router.post("/chunks")
# def process_chunks(db=Depends(get_db)):
#     service = ChunkPipeline(db)
#     docs = db.execute("SELECT id FROM document_blocks").fetchall()

#     chunks = []

#     for doc in docs:
#         service.build_and_save_chunks_for_document(session=db, doc_id=doc.id)

#     return {"message": "Chunking completed"}


# @router.post("/embeddings")
# def process_embeddings(db=Depends(get_db)):
#     service = EmbeddingService()
#     chunks = db.execute("SELECT id FROM document_chunks").fetchall()
#     docs = EmbeddingBuilder.generate_embeddings_for_all_chunks(session=db, embedding_service=service, model_name="intfloat/multilingual-e5-base", batch_size=32)
    
#     return {"message": "Embeddings completed"}
