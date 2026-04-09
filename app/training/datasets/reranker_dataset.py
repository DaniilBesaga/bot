import json
from pathlib import Path
from sqlalchemy.orm import Session
from torch.utils.data import Dataset

class RerankerDataset(Dataset):
    def __init__(self, sql: str, db: Session):
        self.items = []

        try:
            result = db.execute(sql)
            if result is not None:
                self.items = [{
                    "question": row.question,
                    "chunk": row.chunk_text,  # Теперь это поле доступно благодаря JOIN
                    "label": row.label
                } for row in result]
        except Exception as e:
            print(f"Error: {e}")
            raise

    def __len__(self) -> int:
        return len(self.items)
    
    def __getitem__(self, index) -> dict:
        item = self.items[index]
        return {
            "question": item["question"],
            "chunk": item["chunk"],
            "label": float(item["label"])
        }
