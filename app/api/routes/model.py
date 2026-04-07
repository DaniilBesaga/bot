from fastapi import APIRouter, Depends
from app.db.session import SessionLocal
from app.training.train_reranker import SmartCollate

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/model/train")
async def model_train(db=Depends(get_db)):
    return SmartCollate().train() 