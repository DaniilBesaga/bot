from sentence_transformers import SentenceTransformer

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Модель загружается один раз при инициализации
        self.model = SentenceTransformer(model_name)
        self.model_name = model_name

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """
        Превращает список строк в список эмбеддингов.
        Библиотека сама эффективно делит данные на батчи.
        """
        if not texts:
            return []

        # convert_to_numpy=False вернет тензоры или списки (зависит от настроек), 
        # .tolist() гарантирует стандартный формат Python list
        embeddings = self.model.encode(
            texts, 
            batch_size=batch_size, 
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Эмбеддинг для одной строки."""
        # Можно передать строку напрямую, encode её обработает
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()