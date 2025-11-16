# chroma_db_simple.py

import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any
import logging

from embeddings_simple import get_embedding_model  # уже обсуждали

logger = logging.getLogger(__name__)


class ChromaDB:
    """Простой клиент для ChromaDB"""

    def __init__(self, db_path: str = "data/chroma_db", collection_name: str = "lectures"):
        self.db_path = db_path
        self.collection_name = collection_name

        # НОВЫЙ способ инициализации клиента
        self.client = chromadb.PersistentClient(
            path=db_path
            # Если хочешь, можно добавить tenant/database, но по умолчанию не нужно
        )

        self.collection = None
        self._init_collection()

    def _init_collection(self):
        """Получить или создать коллекцию"""
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(f"Created new collection: {self.collection_name}")

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        ids, documents, metadatas, embeddings = [], [], [], []

        for chunk in chunks:
            ids.append(chunk["id"])
            documents.append(chunk["text"])
            metadatas.append(
                {
                    "file": chunk.get("file", ""),
                    "page": chunk.get("page", 0),
                }
            )
            if "embedding" in chunk:
                embeddings.append(chunk["embedding"])

        if embeddings:
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,  # тут уже должны быть list[list[float]]
                metadatas=metadatas,
            )
        else:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

        logger.info(f"Added {len(chunks)} chunks to collection")

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Поиск по тем же эмбеддингам, что и при индексации."""
        try:
            embedding_model = get_embedding_model()
            query_emb = embedding_model.embed_query(query)

            results = self.collection.query(
                query_embeddings=[query_emb],
                n_results=top_k,
            )

            output: List[Dict[str, Any]] = []
            if results["ids"] and len(results["ids"]) > 0:
                for i, id_val in enumerate(results["ids"][0]):
                    output.append(
                        {
                            "id": id_val,
                            "text": results["documents"][0][i],
                            "distance": results["distances"][0][i],
                            "file": results["metadatas"][0][i].get("file", ""),
                            "page": results["metadatas"][0][i].get("page", 0),
                        }
                    )
            return output
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

    def clear(self):
        """Очистить коллекцию (проще — удалить и пересоздать)"""
        try:
            self.client.delete_collection(name=self.collection_name)
            self._init_collection()
            logger.info("Collection cleared")
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")

    def get_count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0
