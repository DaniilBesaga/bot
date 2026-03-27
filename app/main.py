from fastapi import FastAPI
from app.api.routes.chat import router as chat_router
from app.api.routes.ingest import router as ingest_router

app = FastAPI(title="Custom RAG Bot")

app.include_router(chat_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")