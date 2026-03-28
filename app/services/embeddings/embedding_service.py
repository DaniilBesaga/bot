from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self):
        # Модель скачается один раз при первом запуске (около 80 Мб)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def embed_text(self, text: str) -> list[float]:
        # Просто превращаем текст в список чисел
        embedding = self.model.encode(text)
        return embedding.tolist()