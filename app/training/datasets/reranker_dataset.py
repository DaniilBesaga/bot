import json
from pathlib import Path
from torch.utils.data import Dataset

class RerankerDataset(Dataset):
    def __init__(self, file_path:str):
        self.items = []

        path = Path(file_path)
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                self.items.append(json.loads(line))

    def __len__(self) -> int:
        return len(self.items)
    
    def __getitem__(self, index) -> dict:
        item = self.items[index]
        return {
            "question": item["question"],
            "chunk": item["chunk"],
            "label": float(item["label"])
        }