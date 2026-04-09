from openai import OpenAI
from app.core.config import settings
from app.services.retrieval.json_parser import extract_json_object

class LlmService:
    def __init__(self):
        # Берем настройки из вашего .env
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=getattr(settings, "OPENAI_API_BASE", None)
        )

    def generate_answer(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=settings.CHAT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content or ""

    def generate_json(self, prompt: str) -> dict | None:
        raw = self.generate_answer(prompt)
        return extract_json_object(raw)