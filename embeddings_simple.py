# embeddings_simple.py

from sentence_transformers import SentenceTransformer
from typing import List
import logging
import numpy as np  # можно, но не обязательно

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Модель для создания эмбеддингов"""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        logger.info(f"Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        logger.info("Model loaded!")

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Создать эмбеддинги для текстов"""
        # ВАЖНО: вернуть список списков float
        emb = self.model.encode(
            texts,
            convert_to_numpy=True,   # ← ключевой момент
            normalize_embeddings=True  # опционально, но полезно для косинусной близости
        )
        # emb: np.ndarray [N, D] → переводим в list[list[float]]
        return emb.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Создать эмбеддинг для запроса"""
        emb = self.model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True
        )[0]
        return emb.tolist()


_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model
