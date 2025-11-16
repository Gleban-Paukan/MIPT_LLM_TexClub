# streamlit_app.py
import os
import re
import requests
import streamlit as st
from streamlit_markdown import st_markdown

def render_answer_with_latex(text: str):
    """
    Рендерит ответ: обычный текст через st.markdown,
    строки вида [ ... ] — как формулы через st.latex.
    """
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        # 1) Строка целиком в формате [ ... ] → считаем это формулой
        m = re.fullmatch(r"\[\s*(.+?)\s*\]", line)
        if m:
            latex_body = m.group(1)
            st.latex(latex_body)
        else:
            st.markdown(raw_line)

# URL до твоего FastAPI бэкенда
API_URL = os.getenv("RAG_API_URL", "http://localhost:8000/api/ask")

st.set_page_config(page_title="RAG по конспектам", page_icon="🎓")

st.title("🎓 Вопросы по конспектам лекций")
st.caption("RAG + LLM по PDF конспектам с цитированием страниц")

# Инициализация истории диалога
if "messages" not in st.session_state:
    st.session_state.messages = []  # список dict: {"role": "user"/"assistant", "content": "..."}

# Отрисовка истории (как в chat templates)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Поле ввода снизу экрана
if prompt := st.chat_input("Задайте вопрос по конспектам (на русском или английском)"):
    # Сохраняем сообщение пользователя в истории
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Рисуем пузырь пользователя
    with st.chat_message("user"):
        st.markdown(prompt)

    # Ответ ассистента
    with st.chat_message("assistant"):
        with st.spinner("Ищу ответ в конспектах и вызываю LLM..."):
            try:
                resp = requests.post(
                    API_URL,
                    json={"question": prompt},
                    timeout=60,
                )
                if resp.status_code != 200:
                    answer = f"Ошибка сервера ({resp.status_code}): {resp.text}"
                    st.error(answer)
                else:
                    data = resp.json()
                    # Поддерживаем как твой простой ответ, так и вариант из первой версии
                    answer_text = data.get("answer", "")
                    citations = data.get("citations", [])
                    mode = data.get("source") or data.get("mode", "lectures")

                    # Формируем подпись об источнике
                    if mode == "lectures":
                        footer = "Ответ основан на конспектах лекций."
                    elif mode == "internet":
                        footer = "Ответ основан на интернет-материалах (поисковый модуль)."
                    else:
                        footer = ""

                    # Формируем список цитат
                    citation_lines = []
                    for c in citations:
                        file = (
                            c.get("file")
                            or c.get("document_title")
                            or c.get("course_name")
                            or "документ"
                        )
                        page = (
                            c.get("page")
                            or c.get("page_start")
                            or "?"
                        )
                        page_end = c.get("page_end")
                        if page_end and page_end != page:
                            page_str = f"стр. {page}–{page_end}"
                        else:
                            page_str = f"стр. {page}"
                        citation_lines.append(f"- {file}, {page_str}")

                    citations_md = ""
                    if citation_lines:
                        citations_md = "\n\n**Источники:**\n" + "\n".join(citation_lines)

                    full_answer = answer_text
                    if footer:
                        full_answer += "\n\n" + footer
                    full_answer += citations_md

                    st_markdown(full_answer)
                    answer = full_answer
            except Exception as e:
                answer = f"Ошибка при запросе к backend API: {e}"
                st.error(answer)

    # Сохраняем ответ ассистента в истории
    st.session_state.messages.append({"role": "assistant", "content": answer})
