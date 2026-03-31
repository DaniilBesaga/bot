from openai import OpenAI
from app.core.config import settings

class LlmService:
    def __init__(self):
        # Берем настройки из вашего .env
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=getattr(settings, "OPENAI_API_BASE", None)
        )

    def generate_answer (self, prompt: str) -> str:
        # В библиотеке OpenAI нет метода .responses.create
        # Используем стандартный .chat.completions.create
        response = self.client.chat.completions.create(
            model=settings.CHAT_MODEL, 
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content