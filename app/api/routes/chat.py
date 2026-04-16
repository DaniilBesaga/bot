from fastapi import APIRouter, Depends
from app.db.repositories import ChunkRepository
from app.schemas.chat import ChatRequest
from app.db.session import SessionLocal
from app.services.chat_service import ChatService
from app.services.language.chunk_trans_service import ChunkTranslationService
from app.services.language.translate_pipeline import TranslatePipeline
from app.services.llm.llm_service import LlmService

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


@router.post("/chat/translate")
def chat_for_translation(db=Depends(get_db)):
    return ChatService(db).ask_for_translate()
    