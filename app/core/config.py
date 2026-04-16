from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    DATABASE_URL: str
    EMBEDDING_MODEL: str
    CHAT_MODEL: str
    TOP_K: int = 5
    OPENAI_API_BASE: str
    DEEPL_API_KEY: str | None = None
    DEEPL_TARGET_LANG: str = "RO"
    DEEPL_GLOSSARY_ID: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()