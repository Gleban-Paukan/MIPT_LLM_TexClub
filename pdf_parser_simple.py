"""
Парсинг PDF и индексирование с корректными номерами страниц
"""
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import pdfplumber

from embeddings_simple import get_embedding_model

logger = logging.getLogger(__name__)


def split_text_into_chunks(text: str, chunk_size: int = 512, overlap: int = 100) -> List[str]:
    """Разбить текст на куски с перекрытием"""
    chunks: List[str] = []
    step = max(chunk_size - overlap, 1)

    if not text:
        return chunks

    for i in range(0, len(text), step):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk)

    return chunks


def _detect_printed_page_number_from_lines(lines: List[str]) -> Optional[int]:
    """
    Попытаться найти логический номер страницы по строкам текста.

    Стратегия:
    - рассматриваем последние несколько непустых строк (обычно номер страницы внизу);
    - ищем строку, которая состоит только из числа (например "13").

    Если ничего не нашли, возвращаем None.
    """
    # Берём только непустые строки
    non_empty = [ln.strip() for ln in lines if ln.strip()]
    # Смотрим снизу, последние 5 строк
    tail = non_empty[-5:] if len(non_empty) > 5 else non_empty

    for ln in reversed(tail):
        # Чисто число 1–4 знака (10, 23, 101 и т.п.)
        m = re.fullmatch(r"\d{1,4}", ln)
        if m:
            try:
                return int(m.group(0))
            except ValueError:
                continue

    return None


def parse_pdf(pdf_path: str, chunk_size: int = 512, chunk_overlap: int = 100) -> List[Dict[str, Any]]:
    """
    Прочитать PDF и создать чанки.

    Возвращает список словарей вида:
    {
        "id": "file_pageIndex_chunkIndex",
        "text": "содержание",
        "file": "name.pdf",
        "page": logical_page_number,  # напечатанный номер или индекс страницы
        "pdf_page_index": физический_индекс_страницы_в_PDF
    }
    """
    chunks_list: List[Dict[str, Any]] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            file_name = Path(pdf_path).name

            for page_index, page in enumerate(pdf.pages, start=1):
                # Берём текст с сохранённой разметкой, чтобы номера страниц были отдельной строкой
                text_layout = page.extract_text(layout=True) or ""
                if not text_layout.strip():
                    continue

                lines = text_layout.split("\n")

                # Пытаемся найти напечатанный номер страницы
                logical_page = _detect_printed_page_number_from_lines(lines)
                if logical_page is None:
                    logical_page = page_index  # fallback: физический индекс страницы

                # Убираем последнюю строку, если это номер страницы, чтобы он не попадал в чанки
                if lines and lines[-1].strip().isdigit():
                    lines = lines[:-1]

                cleaned_text = "\n".join(lines)
                if not cleaned_text.strip():
                    continue

                # Разбиваем текст страницы на чанки
                page_chunks = split_text_into_chunks(cleaned_text, chunk_size, chunk_overlap)

                for chunk_idx, chunk_text in enumerate(page_chunks):
                    chunks_list.append(
                        {
                            "id": f"{file_name}_page{page_index}_chunk{chunk_idx}",
                            "text": chunk_text,
                            "file": file_name,
                            # логический номер страницы для отображения в цитатах
                            "page": logical_page,
                            # физический индекс страницы в PDF (для отладки)
                            "pdf_page_index": page_index,
                        }
                    )

        logger.info(f"Parsed {pdf_path}: {len(chunks_list)} chunks from {len(pdf.pages)} pages")
        return chunks_list

    except Exception as e:
        logger.error(f"Error parsing {pdf_path}: {e}")
        return []


def index_pdf_files(pdf_dir: str, db, chunk_size: int = 512, chunk_overlap: int = 100):
    """
    Индексировать все PDF в папке.

    db - экземпляр ChromaDB (ожидает, что в чанках есть поле 'embedding').
    """
    pdf_dir_path = Path(pdf_dir)

    if not pdf_dir_path.exists():
        logger.warning(f"PDF directory not found: {pdf_dir_path}")
        return 0

    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {pdf_dir_path}")
        return 0

    logger.info(f"Found {len(pdf_files)} PDF files")

    all_chunks: List[Dict[str, Any]] = []
    for pdf_file in pdf_files:
        chunks = parse_pdf(str(pdf_file), chunk_size, chunk_overlap)
        all_chunks.extend(chunks)

    if not all_chunks:
        logger.warning("No chunks created")
        return 0

    logger.info(f"Total chunks: {len(all_chunks)}")

    # Получить эмбеддинги
    logger.info("Computing embeddings...")
    embedding_model = get_embedding_model()
    texts = [chunk["text"] for chunk in all_chunks]
    embeddings = embedding_model.embed(texts)

    # Добавить эмбеддинги к чанкам
    for chunk, embedding in zip(all_chunks, embeddings):
        chunk["embedding"] = embedding

    # Добавить в БД
    logger.info("Adding chunks to database...")
    db.add_chunks(all_chunks)

    logger.info(f"Indexed {len(all_chunks)} chunks successfully!")
    return len(all_chunks)
