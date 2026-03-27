from openai import OpenAI
from app.core.config import settings

class LlmService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPEN_API_KEY)

    def generate_answer(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=settings.CHAT_MODEL, 
            input=prompt
        )
        return response.output_text