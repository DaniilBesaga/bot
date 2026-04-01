import os
from fastapi import APIRouter, Depends
from app.db.session import SessionLocal
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
def ingest(db=Depends(get_db)):
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
                result = service.ingest_file(file_path)
                if result:
                    results.append(result)

    return {"message": "Ingestion completed", "results": results}

@router.get("/pdf")
def process_pdf(file_path: str, doc_id: str, db=Depends(get_db)):
    service = ProcessDocumentService(db)
    return service.process_document(file_path, doc_id)