import os
from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService

folders = [
    "data/raw/pdf",
    "data/raw/docx",
    "data/raw/txt"
]

db = SessionLocal()
service = IngestionService(db)

try:
    for folder in folders:
        if not os.path.exists(folder):
            continue

        for file_name in os.listdir(folder):
            file_path = os.path.join(folder, file_name)
            if os.path.isfile(file_path):
                result = service.ingest_file(file_path)
                print(result)
finally:
    db.close()