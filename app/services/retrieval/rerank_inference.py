from pathlib import Path

import torch

from app.services.retrieval.my_reranker import MyReranker


class MyRerankerService:
    def __init__(self, model_dir : str="models/reranker", device: str | None = None):
        self.model_dir = Path(model_dir)

        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)

        self.model = MyReranker(model_name="distilbert-base-uncased").to(self.device)
        self.model.load_state_dict(torch.load(self.model_dir / "model.pt", map_location=self.device))
        self.model.to(self.device)
        self.model.eval()

    def score_pairs(self, question: str, chunks: list[dict], batch_size: int = 8) -> list[dict]:
        if not chunks:
            return []
        
        scored = []

        with torch.no_grad():
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]

                questions = [question] * len(batch_chunks)
                texts = [chunk["text"] for chunk in batch_chunks]

                encoded = self.model.tokenize_pairs(questions, texts, max_length=256)
                encoded = {k: v.to(self.device) for k, v in encoded.items()}

                logits = self.model(
                    input_ids=encoded["input_ids"],
                    attention_mask=encoded["attention_mask"]
                )

                probs = torch.sigmoid(logits).cpu().tolist()

                for chunk, score in zip(batch_chunks, probs):
                    item = dict(chunk)
                    item["rerank_score"] = float(score)
                    scored.append(item)

        scored.sort(key=lambda x: x["rerank_score"], reverse=True)

        return scored
    
    def rerank(self, question: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
        scored = self.score_pairs(question, chunks)
        return scored[:top_n]

