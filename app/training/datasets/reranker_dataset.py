import json
from pathlib import Path
from torch.utils.data import Dataset

class RerankerDataset(Dataset):
    def __init__(self, sql: str, db):
        self.db = db
        self.items = []

        try:
            training_data = self.db.engine.execute(sql)
            if training_data is not None:
                self.items = [{
                    "question": training_data.question,
                    "chunk": training_data.chunk.text,
                    "label": training_data.label
                } for training_data in training_data]
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