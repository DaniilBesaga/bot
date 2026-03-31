from fastapi import APIRouter, Depends
from app.schemas.chat import ChatRequest
from app.db.session import SessionLocal
from app.services.chat_service import ChatService

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/chat")
def chat(request: ChatRequest, db = Depends(get_db)):
    return ChatService(db).ask(request.question)

@router.post("/chat/questions")
def chat_for_questions(db = Depends(get_db)):
    return ChatService(db).ask_for_questions()