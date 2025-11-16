"""
CLI скрипт для индексирования PDF
"""
import sys
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from config_simple import get_settings
from chroma_db_simple import ChromaDB
from pdf_parser_simple import index_pdf_files


def main():
    parser = argparse.ArgumentParser(description="Индексировать PDF конспекты")
    parser.add_argument("--pdf-dir", type=str, default="data/pdfs", help="Папка с PDF")
    parser.add_argument("--clear", action="store_true", help="Очистить индекс")
    
    args = parser.parse_args()
    
    # Загрузить конфиг
    settings = get_settings()
    
    # Инициализировать ChromaDB
    db = ChromaDB(
        db_path=settings.CHROMA_DB_PATH,
        collection_name=settings.COLLECTION_NAME
    )
    
    # Очистить если нужно
    if args.clear:
        print("Clearing index...")
        db.clear()
        print("Done!")
        return
    
    # Индексировать PDF
    print(f"Indexing PDFs from {args.pdf_dir}...")
    chunks_count = index_pdf_files(
        args.pdf_dir,
        db,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )
    
    count = db.get_count()
    print(f"\n✅ Success! Total chunks in database: {count}")


if __name__ == "__main__":
    main()
