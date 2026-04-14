import os
from pathlib import Path

from sqlalchemy import text
import torch
from torch.utils.data import DataLoader
from torch.optim import AdamW
from transformers import AutoTokenizer

from app.training.datasets.reranker_dataset import RerankerDataset
from app.services.retrieval.my_reranker import MyReranker

class SmartCollate:
    def __init__(self, db, max_length=256):
        self.max_length = max_length
        self.db = db
        self.tokenizer = AutoTokenizer.from_pretrained("distilbert-base-uncased")

    def __call__(self, batch):
        questions = [item["question"] for item in batch]
        chunks = [item["chunk"] for item in batch]
        labels = torch.tensor([item["label"] for item in batch], dtype=torch.float32)

        encoded = self.tokenizer(
            questions,
            chunks,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt"
        )
        encoded["labels"] = torch.tensor(labels, dtype=torch.float)

        return encoded
        

# def collate_fn(batch, model: MyReranker):
#     questions = [item["question"] for item in batch]
#     chunks = [item["chunk"] for item in batch]
#     labels = torch.tensor([item["label"] for item in batch], dtype=torch.float32)

#     encoded = model.tokenize_pairs(questions, chunks, max_length=384)
#     encoded["labels"] = labels

#     return encoded

    def evaluate(self, model, dataloader, device):
        model.eval()
        total_loss = 0.0
        total_count = 0

        loss_fn = torch.nn.BCEWithLogitsLoss()

        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)

                logits = model(input_ids, attention_mask)
                loss = loss_fn(logits, labels)

                batch_size = labels.size(0)
                total_loss += loss.item() * batch_size
                total_count += batch_size

        return total_loss / max(total_count, 1)

    def train(self):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        model = MyReranker(model_name="distilbert-base-uncased").to(device)

        train_sql = train_sql = text("""
                SELECT e.question, c.chunk_text, e.label 
                FROM reranker_examples e
                JOIN document_chunks c ON e.chunk_id = c.id
                WHERE e.split = 'train' 
                
            """)
        train_dataset = RerankerDataset(train_sql, self.db)

        val_sql = text("""
                SELECT e.question, c.chunk_text, e.label 
                FROM reranker_examples e
                JOIN document_chunks c ON e.chunk_id = c.id
                WHERE e.split = 'val' 
                
            """)
        val_dataset = RerankerDataset(val_sql, self.db)

        my_collate = SmartCollate(model.tokenizer)

        train_loader = DataLoader(
            train_dataset,
            batch_size=8,
            shuffle=True,
            collate_fn=self,
            num_workers=0,
            pin_memory=True
        )

        val_loader = DataLoader(
            val_dataset,
            batch_size=8,
            shuffle=False,
            collate_fn=self,
            num_workers=0,
            pin_memory=True
        )

        optimizer = AdamW(model.parameters(), lr=2e-5)
        loss_fn = torch.nn.BCEWithLogitsLoss()

        epochs = 10
        best_val_loss = float("inf")

        save_dir = Path("models/reranker")
        save_dir.mkdir(parents=True, exist_ok=True)

        for epoch in range(epochs):
            model.train()
            running_loss = 0.0
            total_count = 0

            for batch in train_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)

                optimizer.zero_grad()

                logits = model(input_ids, attention_mask)
                loss = loss_fn(logits, labels)
                
                loss.backward()
                optimizer.step()

                batch_size = labels.size(0)
                running_loss += loss.item() * batch_size
                total_count += batch_size
            
            train_loss = running_loss / max(total_count, 1)
            val_loss = self.evaluate(model, val_loader, device)

            print(f"Epoch {epoch + 1}/{epochs}, Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                torch.save(model.state_dict(), os.path.join(save_dir, "best_model.pt"))

                model.encoder.config.save_pretrained(save_dir)
                model.tokenizer.save_pretrained(save_dir)

                with open(save_dir / "meta.txt", "w", encoding="utf-8") as f:
                    f.write("base_model=distilbert-base-uncased\n")
                    f.write("max_length=256\n")

                print("Saved best reranker.")