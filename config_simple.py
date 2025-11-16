"""
Конфигурация (упрощённая версия)
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Настройки"""
    
    # LLM
    LLM_API_KEY: str
    LLM_PROVIDER: str = "openai"  # openai или anthropic
    LLM_MODEL: str = "gpt-4-turbo-preview"
    
    # Поиск в интернете
    SEARCH_ENABLED: bool = False
    SEARCH_API_KEY: Optional[str] = None
    
    # RAG параметры
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 100
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_THRESHOLD: float = 0.3
    
    # ChromaDB
    CHROMA_DB_PATH: str = "data/chroma_db"
    COLLECTION_NAME: str = "lectures"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    return Settings()
