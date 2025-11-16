# llm_simple.py
"""
LLM клиент для Perplexity API
"""
import httpx
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """Клиент для Perplexity pplx-api"""

    def __init__(self, api_key: str, model: str = "mistral-7b-instruct"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.perplexity.ai/chat/completions"  # из доков pplx-api

    async def generate(self, system_prompt: str, user_message: str) -> str:
        """Генерировать ответ через Perplexity API"""
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.7,
                "max_tokens": 2000,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json=payload,
                )

            if response.status_code != 200:
                logger.error(f"Perplexity API error: {response.status_code} {response.text}")
                return f"Ошибка LLM: {response.status_code}"

            data = response.json()
            # Схема ответа совместима с OpenAI: choices[0].message.content
            return data["choices"][0]["message"]["content"]

        except Exception as e:
            logger.error(f"Error calling Perplexity API: {e}")
            return f"Ошибка при обращении к LLM: {str(e)}"


_llm_client = None


def get_llm_client(api_key: str, model: str = "mistral-7b-instruct"):
    """Получить глобальный LLM клиент"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(api_key, model)
    return _llm_client
