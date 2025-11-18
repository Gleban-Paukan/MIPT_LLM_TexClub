"""
FastAPI сервер (основной)
"""
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import webbrowser
import threading

from config_simple import get_settings
from chroma_db_simple import ChromaDB
from llm_simple import get_llm_client
from embeddings_simple import get_embedding_model

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализировать сервисы
settings = get_settings()
db = ChromaDB(settings.CHROMA_DB_PATH, settings.COLLECTION_NAME)
llm_client = get_llm_client(settings.LLM_API_KEY, settings.LLM_MODEL)
embedding_model = get_embedding_model()

# FastAPI приложение
app = FastAPI(
    title="RAG Lectures API",
    description="Простой RAG для конспектов",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


class Citation(BaseModel):
    file: str
    page: int
    text: str


class AskResponse(BaseModel):
    answer: str
    source: str 
    citations: List[Citation] = []



@app.post("/api/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """Задать вопрос"""
    try:
        question = request.question.strip()
        print(question)
        
        if not question:
            raise HTTPException(status_code=400, detail="Question is empty")
        
        #релевантные чанки
        logger.info(f"Question: {question}")
        search_results = db.search(question, top_k=settings.RETRIEVAL_TOP_K)
        
        if not search_results:
            logger.info("No results found")
            return AskResponse(
                answer="К сожалению, я не нашёл релевантной информации в конспектах.",
                source="error",
                citations=[]
            )
        
        # Проверить похожесть
        max_distance = search_results[0]['distance']
        # ChromaDB использует distance, а не similarity
        if max_distance > 0.7:
            logger.info(f"Max distance {max_distance} exceeds threshold")
            return AskResponse(
                answer="Информация по этому вопросу не найдена.",
                source="error",
                citations=[]
            )
        
        # Создать контекст из чанков
        context_parts = []
        citations = []
        
        for result in search_results[:3]:
            context_parts.append(result['text'])
            citations.append(Citation(
                file=result['file'],
                page=result['page'],
                text=result['text'][:80] + "..."
            ))
        
        context = "\n\n".join(context_parts)
        
        system_prompt = """Ты - помощник, который отвечает на вопросы по конспектам лекций.
Правила:
1. Опирайся ТОЛЬКО на предоставленные конспекты
2. Используй простой и понятный язык
3. Если в конспектах нет ответа - скажи об этом
4. Цитируй источники (файл и страница)
5. Оформи ответ в Markdown:
           - Делай структурированные абзацы и списки.
           - Встроенные формулы записывай в формате $ ... $.
           - Формулы на отдельной строке записывай в формате:
             $$ ... $$
           - НЕ используй квадратные скобки вокруг формул вида [ Y = f(X) ] и НЕ дублируй формулы текстом.
"""

        user_message = f"""Контекст из конспектов:
{context}

Вопрос: {question}

Ответь на вопрос на основе контекста выше."""

        logger.info("Generating answer...")
        answer = await llm_client.generate(system_prompt, user_message)
        
        return AskResponse(
            answer=answer,
            source="lectures",
            citations=citations
        )
    
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Получить статистику"""
    return {
        "total_chunks": db.get_count(),
        "chunk_size": settings.CHUNK_SIZE,
        "retrieval_top_k": settings.RETRIEVAL_TOP_K
    }


@app.get("/health")
async def health():
    """Проверка здоровья"""
    return {
        "status": "ok",
        "database": "ready"
    }



@app.get("/")
async def root():
    """Простой UI"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RAG Lectures</title>
        <style>
            body { font-family: Arial; max-width: 800px; margin: 50px auto; }
            input { width: 100%; padding: 10px; font-size: 16px; }
            button { padding: 10px 20px; font-size: 16px; cursor: pointer; }
            #answer { margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 5px; }
            .citation { margin: 10px 0; padding: 10px; background: #e8e8e8; border-left: 3px solid #333; }
        </style>
    </head>
    <body>
        <h1>🎓 RAG для конспектов</h1>
        <p>Задайте вопрос по конспектам лекций:</p>
        
        <div>
            <input type="text" id="question" placeholder="Например: Что такое машинное обучение?" />
            <button onclick="askQuestion()">Спросить</button>
        </div>
        
        <div id="answer"></div>
        
        <script>
            async function askQuestion() {
                const question = document.getElementById('question').value;
                if (!question) return;
                
                document.getElementById('answer').innerHTML = ' Ищу ответ...';
                
                try {
                    const response = await fetch('/api/ask', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question})
                    });
                    
                    const data = await response.json();
                    
                    let html = `<h3>Ответ:</h3><p>${data.answer}</p>`;
                    
                    if (data.citations.length > 0) {
                        html += '<h4>Источники:</h4>';
                        data.citations.forEach(c => {
                            html += `<div class="citation"><strong>${c.file}</strong> стр. ${c.page}</div>`;
                        });
                    }
                    
                    document.getElementById('answer').innerHTML = html;
                } catch (e) {
                    document.getElementById('answer').innerHTML = `Ошибка: ${e.message}`;
                }
            }
            
            // Enter для отправки
            document.getElementById('question').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') askQuestion();
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

if __name__ == "__main__":
    import uvicorn
    
    # Открыть браузер
    def open_browser():
        import time
        time.sleep(1)
        webbrowser.open('http://localhost:8000')
    
    thread = threading.Thread(target=open_browser, daemon=True)
    thread.start()
    
    # Запустить сервер
    uvicorn.run(app, host="0.0.0.0", port=8000)
