import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer

class MyReranker(nn.Module):
    def __init__(self, model_name: str = "distilbert-base-uncased", 
                 dropout: float = 0.1):
        super().__init__()

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.encoder = AutoModel.from_pretrained(model_name)

        hidden_size = self.encoder.config.hidden_size

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_size, 1)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        outputs = self.encoder(input_ids, attention_mask=attention_mask)

        cls_embedding = outputs.last_hidden_state[:, 0, :]

        cls_embedding = self.dropout(cls_embedding)
        logits = self.classifier(cls_embedding).squeeze(-1)

        return logits
    
    def tokenize_pairs(
            self,
            questions: list[str],
            chunks: list[str],
            max_length: int = 384
    ) -> dict:
        return self.tokenizer(
            questions,
            chunks,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_length
        )