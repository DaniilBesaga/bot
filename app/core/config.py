from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DATABASE_URL: str
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    CHAT_MODEL: str = "gpt-4"
    TOP_K: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()