# RAG поисковик для конспектов - Быстрый старт

##  Установка

```bash
# 1. Клонировать или распаковать проект
cd rag-simple

# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

# 3. Установить зависимости
pip install -r requirements-simple.txt

# 4. Создать .env файл
```

## Использование

### Подготовьте PDF конспекты

Положите PDF файлы в папку `data/pdfs/`:

```
data/
└── pdfs/
    ├── lecture_01.pdf
    ├── lecture_02.pdf
    └── ...
```

### Индексируйте конспекты

```bash
python index_lectures_simple.py
```

Вывод:
```
Loading model: BAAI/bge-m3
Model loaded!
Found 3 PDF files
Parsed lecture_01.pdf: 12 chunks from 5 pages
...
Success! Total chunks in database: 47
```

### Запустите API сервер

```bash
python main_simple.py
```

Вывод:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Opening browser at http://localhost:8000
```

Автоматически откроется браузер на `http://localhost:8000` 

## Примеры запросов

### Через браузер
Просто откройте http://localhost:8000 и напишите вопрос в текстовое поле

### Через curl

```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Что такое линейная регрессия?"
  }'
```

**Ответ:**
```json
{
  "answer": "Линейная регрессия - это метод машинного обучения... [Источник: lecture_02.pdf, стр. 5]",
  "source": "lectures",
  "citations": [
    {
      "file": "lecture_02.pdf",
      "page": 5,
      "text": "Линейная регрессия - это..."
    }
  ]
}
```

### Через Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/ask",
    json={"question": "Что такое машинное обучение?"}
)

print(response.json())
```

## 📊 Статистика

```bash
curl http://localhost:8000/api/stats
```

Ответ:
```json
{
  "total_chunks": 47,
  "chunk_size": 512,
  "retrieval_top_k": 5
}
```

## Возможные проблемы и их решение

###  "ModuleNotFoundError: No module named 'chromadb'"

```bash
pip install chromadb
```

### "OpenAI API key not found"

Убедитесь что `.env` в той же папке и содержит:
```
LLM_API_KEY=sk-xxxxxxxxxx
```

### "No PDF files found"

```bash
mkdir -p data/pdfs
# Положите PDF файлы в эту папку
python index_lectures_simple.py
```

### "Cannot find embeddings"

Модель будет загружена автоматически при первом запуске (может быть медленно ~30 сек)

### Ошибка при подключении к LLM

- Проверьте ключ в `.env`
- Проверьте интернет соединение
- Убедитесь что API доступен

## Структура проекта

```
rag-simple/
├── main_simple.py              #  Запуск сервера
├── index_lectures_simple.py    #  Индексирование PDF
├── config_simple.py            #  Конфигурация
├── chroma_db_simple.py         #  БД (ChromaDB)
├── embeddings_simple.py        #  Эмбеддинги (BAAI/bge-m3)
├── llm_simple.py              #  LLM клиент (OpenAI)
├── pdf_parser_simple.py       #  Парсинг PDF
├── test_simple.py             #  Тесты
├── requirements-simple.txt    #  Зависимости
├── .env.example               #  Пример конфига
└── data/
    ├── pdfs/                  #  Ваши PDF файлы
    └── chroma_db/             #  БД (создаётся автоматически)
```

