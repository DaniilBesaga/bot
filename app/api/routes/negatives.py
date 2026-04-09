import os
from fastapi import APIRouter, Depends
from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.services.negative_gen_service import NegativeGenerationService

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close

router = APIRouter()

@router.post("/negatives")
def generate_negatives(db = Depends(get_db)):
    service = NegativeGenerationService(db)
    return service.generate_negative_chunks()