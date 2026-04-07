from fastapi import FastAPI
from app.api.routes.chat import router as chat_router
from app.api.routes.ingest import router as ingest_router
import os

# Your specific path to the site-packages
dll_dir = r"C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\Lib\site-packages\docling_parse"

if os.path.exists(dll_dir):
    os.add_dll_directory(dll_dir)
    print(f"Successfully added DLL directory: {dll_dir}")
else:
    print("Warning: The docling_parse directory was not found at the specified path.")
    
app = FastAPI(title="Custom RAG Bot")

app.include_router(chat_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")